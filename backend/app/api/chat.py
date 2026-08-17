import asyncio, json, time, uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth import current_claims
from app.dependencies.db import get_db
from app.models.core import Agent, AgentVersion
from app.runtime.model_gateway import ModelGateway, MockProvider
from app.services.session_service import SessionService

router = APIRouter()
class ChatRequest(BaseModel):
    agent_id: UUID
    input: str = Field(min_length=1)
    session_id: UUID | None = None

def gateway(): return ModelGateway(MockProvider())

@router.post("/stream")
async def stream(p: ChatRequest, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    request_id, trace_id = uuid.uuid4(), uuid.uuid4()
    user_id = UUID(claims["sub"])
    service = SessionService(db)
    agent, version = await service.load_runtime(p.agent_id)
    if "admin" not in claims.get("roles", []) and agent.owner_id != user_id: raise HTTPException(403, "无权访问该 Agent")
    session = await service.get_or_create(p.session_id, user_id, agent.id)
    history = await service.history(session.id, user_id)
    await service.add_message(session.id, "user", p.input); await db.commit()
    messages = [{"role":"system","content":version.system_prompt}] + [{"role":m.role,"content":m.content} for m in history] + [{"role":"user","content":p.input}]
    started = time.perf_counter(); answer = await gateway().generate(version.model_id, messages)
    async def events():
        yield f"data: {json.dumps({'type':'start','request_id':str(request_id),'trace_id':str(trace_id),'session_id':str(session.id),'agent_id':str(agent.id),'agent_version':version.version,'model_id':version.model_id}, ensure_ascii=False)}\n\n"
        for i in range(0, len(answer), 24):
            yield f"data: {json.dumps({'type':'delta','content':answer[i:i+24]}, ensure_ascii=False)}\n\n"; await asyncio.sleep(0)
        await service.add_message(session.id, "assistant", answer); await db.commit()
        yield f"data: {json.dumps({'type':'done','execution_id':str(uuid.uuid4()),'latency_ms':int((time.perf_counter()-started)*1000)}, ensure_ascii=False)}\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control":"no-cache","X-Request-ID":str(request_id),"X-Trace-ID":str(trace_id)})

@router.get("/sessions/{session_id}/messages")
async def messages(session_id: UUID, claims=Depends(current_claims), db: AsyncSession = Depends(get_db)):
    items = await SessionService(db).history(session_id, UUID(claims["sub"]))
    return [{"id":m.id,"role":m.role,"content":m.content,"created_at":m.created_at} for m in items]
