import asyncio
import json
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims
from app.dependencies.db import get_db
from app.runtime.memory_context import build_memory_context
from app.runtime.model_gateway import ModelGateway
from app.services.knowledge_retrieval import KnowledgeRetrievalService
from app.services.memory_service import MemoryService
from app.services.observability_service import ObservabilityService
from app.services.session_service import SessionService

router = APIRouter()


class ChatRequest(BaseModel):
    agent_id: UUID
    input: str = Field(min_length=1)
    session_id: UUID | None = None
    memory_limit: int = Field(default=20, ge=1, le=50)


def gateway():
    """Build the configured model gateway."""
    return ModelGateway()


def build_knowledge_context(results: list[dict]) -> str:
    if not results:
        return ""
    sections = [
        "以下内容来自当前 AgentVersion 配置的知识库检索结果。仅使用这些内容回答相关问题，并保留引用标记："
    ]
    for item in results:
        sections.append(f"[{item['citation']}] {item['content']}")
    return "\n\n".join(sections)


@router.post("/stream")
async def stream(
    p: ChatRequest,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    request_id, trace_id = ObservabilityService.new_ids()
    user_id = UUID(claims["sub"])
    is_admin = "admin" in claims.get("roles", [])
    service = SessionService(db)
    memory_service = MemoryService(db)
    observability = ObservabilityService(db)
    retrieval = KnowledgeRetrievalService(db)
    agent, version = await service.load_runtime(p.agent_id)

    if not is_admin and agent.owner_id != user_id:
        raise HTTPException(403, "无权访问该 Agent")

    session = await service.get_or_create(p.session_id, user_id, agent.id)
    history = await service.history(session.id, user_id)
    memories = await memory_service.list_for_context(
        user_id=user_id,
        agent_id=agent.id,
        session_id=session.id,
        limit=p.memory_limit,
    )
    memory_context = build_memory_context(memories)

    await service.add_message(session.id, "user", p.input)
    execution = await observability.start_execution(
        request_id=request_id,
        trace_id=trace_id,
        session_id=session.id,
        agent_id=agent.id,
        agent_version=version.version,
        model_id=version.model_id,
    )
    await db.commit()

    knowledge_config = version.knowledge_config or {}
    knowledge_base_ids = [UUID(str(item)) for item in knowledge_config.get("knowledge_base_ids", [])]
    top_k = int(knowledge_config.get("top_k", 5))
    retrieval_results: list[dict] = []
    if knowledge_base_ids:
        retrieval_started = observability.now()
        try:
            for knowledge_base_id in knowledge_base_ids:
                retrieval_results.extend(
                    await retrieval.retrieve(
                        query=p.input,
                        top_k=top_k,
                        owner_id=user_id,
                        is_admin=is_admin,
                        knowledge_base_id=knowledge_base_id,
                    )
                )
            retrieval_results.sort(
                key=lambda item: (-item["relevance_score"], str(item["document_id"]), item["chunk_index"])
            )
            retrieval_results = retrieval_results[:top_k]
            await observability.record_event(
                execution,
                span_type="retrieval",
                started_at=retrieval_started,
            )
        except Exception as exc:
            await observability.record_event(
                execution,
                span_type="retrieval",
                started_at=retrieval_started,
                status="failed",
                error_code=type(exc).__name__,
                error_message="Knowledge retrieval failed",
            )
            await observability.finish_execution(
                execution,
                status="failed",
                error_code=type(exc).__name__,
                error_message="Knowledge retrieval failed",
            )
            await db.commit()
            raise HTTPException(502, "知识检索失败") from exc

    knowledge_context = build_knowledge_context(retrieval_results)
    messages = [{"role": "system", "content": version.system_prompt}]
    if knowledge_context:
        messages.append({"role": "system", "content": knowledge_context})
    if memory_context:
        messages.append({"role": "system", "content": memory_context})
    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": p.input})

    model_started = observability.now()
    try:
        result = await gateway().generate(version.model_id, messages, session.id)
        usage = result.usage
        await observability.record_event(
            execution,
            span_type="model",
            started_at=model_started,
            model_id=version.model_id,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
        )
        await observability.finish_execution(execution)
        await db.commit()
    except Exception as exc:
        await observability.record_event(
            execution,
            span_type="model",
            started_at=model_started,
            status="failed",
            model_id=version.model_id,
            error_code=type(exc).__name__,
            error_message="Model execution failed",
        )
        await observability.finish_execution(
            execution,
            status="failed",
            error_code=type(exc).__name__,
            error_message="Model execution failed",
        )
        await db.commit()
        raise HTTPException(502, "模型执行失败") from exc

    citations = [item["citation"] for item in retrieval_results]

    async def events():
        yield f"data: {json.dumps({'type': 'start', 'request_id': request_id, 'trace_id': trace_id, 'session_id': str(session.id), 'agent_id': str(agent.id), 'agent_version': version.version, 'model_id': version.model_id, 'memory_count': len(memories), 'knowledge_count': len(retrieval_results), 'citations': citations}, ensure_ascii=False)}\n\n"
        for i in range(0, len(result.content), 24):
            yield f"data: {json.dumps({'type': 'delta', 'content': result.content[i:i + 24]}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
        await service.add_message(session.id, "assistant", result.content)
        await db.commit()
        yield f"data: {json.dumps({'type': 'done', 'execution_id': str(execution.id), 'latency_ms': execution.duration_ms, 'citations': citations}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Request-ID": request_id,
            "X-Trace-ID": trace_id,
        },
    )


@router.get("/sessions/{session_id}/messages")
async def messages(
    session_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    items = await SessionService(db).history(session_id, UUID(claims["sub"]))
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in items
    ]
