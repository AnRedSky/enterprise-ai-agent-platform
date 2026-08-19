"""Phase 1.4-F-03 real database-backed hybrid retrieval quality evaluation."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import httpx
from sqlalchemy import delete, select, text

from app.core.auth import current_claims
from app.core.config import settings
from app.dependencies.db import SessionLocal, engine, get_db
from app.main import app
from app.models.core import User
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentChunk, KnowledgeDocumentVersion
from app.services.knowledge_ingestion import KnowledgeIngestionService
from app.services.retrieval_evaluation import RetrievalEvaluationCase, RetrievalEvaluationObservation, aggregate_observations

CASES_PATH = BACKEND_ROOT / "evaluation" / "hybrid_retrieval_quality_cases.json"
FIXTURES = [
    ("FastAPI Agent Runtime", "FastAPI Agent Runtime 使用 FastAPI 暴露企业智能体运行时 Retrieval API，并通过统一运行时服务执行请求。"),
    ("报销规则", "报销规则要求员工提交费用明细、发票和审批依据；超过额度时必须进入审批流程。"),
    ("PostgreSQL 知识库", "PostgreSQL 知识库使用 PostgreSQL 与 pgvector 保存知识 Chunk 和向量索引，并支持数据库检索。"),
    ("审批流程", "审批流程包含申请、主管审批、财务复核和最终归档步骤，审批结果需要保留审计信息。"),
    ("Citation Retrieval", "Citation Retrieval 要求检索结果保留 document、version、chunk 和 citation 信息，便于结果追溯。"),
]


def load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


async def run() -> int:
    if settings.vector_provider != "pgvector":
        raise RuntimeError("VECTOR_PROVIDER=pgvector is required for F-03")
    if settings.embedding_provider not in {"mock", "openai-compatible"}:
        raise RuntimeError("EMBEDDING_PROVIDER must be mock or openai-compatible")

    raw_cases = load_cases()
    async with SessionLocal() as db:
        owner = (
            await db.execute(select(User).where(User.status == "active").order_by(User.created_at.asc()).limit(1))
        ).scalar_one_or_none()
        if owner is None:
            raise RuntimeError("No active user exists. Create/login a local user before F-03.")

        kb_id = uuid4()
        db.add(KnowledgeBase(id=kb_id, name="Phase 1.4-F-03 Hybrid Quality Fixture", description="Ephemeral real database evaluation fixture", owner_id=owner.id, status="active"))
        await db.flush()

        version_ids: list[UUID] = []
        for title, content in FIXTURES:
            document = KnowledgeDocument(id=uuid4(), knowledge_base_id=kb_id, title=title, source_type="manual", source_uri=f"local://phase-1-4-f/{title}", status="active")
            version = KnowledgeDocumentVersion(
                id=uuid4(), document_id=document.id, version="1.0", status="draft",
                ingestion_status="pending", vector_index_status="pending", source_uri=document.source_uri,
                content_text=content, created_by=owner.id,
            )
            db.add_all([document, version])
            version_ids.append(version.id)
        await db.commit()

        async def override_db():
            yield db

        app.dependency_overrides[current_claims] = lambda: {"sub": str(owner.id), "roles": ["user"]}
        app.dependency_overrides[get_db] = override_db

        try:
            for version_id in version_ids:
                _, count = await KnowledgeIngestionService(db).ingest(version_id, owner.id)
                if count == 0:
                    raise RuntimeError(f"ingestion produced no chunks for version {version_id}")

            chunk_rows = (
                await db.execute(
                    select(KnowledgeDocument.title, KnowledgeDocumentChunk.id)
                    .join(KnowledgeDocumentVersion, KnowledgeDocumentVersion.document_id == KnowledgeDocument.id)
                    .join(KnowledgeDocumentChunk, KnowledgeDocumentChunk.document_version_id == KnowledgeDocumentVersion.id)
                    .where(KnowledgeDocument.knowledge_base_id == kb_id)
                )
            ).all()
            chunk_by_title = {title: str(chunk_id) for title, chunk_id in chunk_rows}
            if len(chunk_by_title) != len(FIXTURES):
                raise RuntimeError(f"expected {len(FIXTURES)} fixture chunks, found {len(chunk_by_title)}")

            expected_by_query = {
                case["query"]: {chunk_by_title[title] for title in case["relevant_documents"]}
                for case in raw_cases
            }
            transport = httpx.ASGITransport(app=app)
            observations_by_mode: dict[str, list[RetrievalEvaluationObservation]] = {}
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                for mode in ("lexical-v2", "vector", "hybrid"):
                    observations: list[RetrievalEvaluationObservation] = []
                    for case in raw_cases:
                        started = time.perf_counter()
                        try:
                            response = await client.post(
                                "/api/v1/knowledge/retrieve",
                                json={
                                    "query": case["query"], "top_k": 3, "mode": mode,
                                    "knowledge_base_id": str(kb_id), "lexical_weight": 0.5,
                                    "vector_weight": 0.5, "dedupe": True,
                                },
                            )
                            latency_ms = (time.perf_counter() - started) * 1000
                            if response.status_code != 200:
                                observations.append(RetrievalEvaluationObservation((), latency_ms, f"HTTP {response.status_code}: {response.text}"))
                                continue
                            results = response.json().get("results", [])
                            required = ("document_id", "document_version_id", "chunk_id", "citation", "content", "source_document", "relevance_score")
                            for item in results:
                                missing = [field for field in required if field not in item]
                                if missing:
                                    raise RuntimeError(f"{mode}/{case['query']}: missing citation fields {missing}")
                            observations.append(RetrievalEvaluationObservation(tuple(str(item["chunk_id"]) for item in results), latency_ms))
                        except Exception as exc:
                            observations.append(RetrievalEvaluationObservation((), (time.perf_counter() - started) * 1000, str(exc)))
                    observations_by_mode[mode] = observations

            cases = [RetrievalEvaluationCase(case["query"], frozenset(expected_by_query[case["query"]])) for case in raw_cases]
            metrics = {mode: aggregate_observations(cases, observations, k=3) for mode, observations in observations_by_mode.items()}
            hybrid, lexical = metrics["hybrid"], metrics["lexical-v2"]
            failures: list[str] = []
            for metric in ("recall_at_k", "mrr"):
                if float(hybrid[metric]) < float(lexical[metric]):
                    failures.append(f"hybrid {metric} regressed: {hybrid[metric]} < lexical baseline {lexical[metric]}")
            if float(hybrid["error_rate"]) > 0:
                failures.append(f"hybrid error rate is non-zero: {hybrid['error_rate']}")

            print(json.dumps({
                "source": "PostgreSQL/pgvector via FastAPI Retrieval API",
                "embedding_provider": settings.embedding_provider,
                "k": 3,
                "knowledge_base_id": str(kb_id),
                "modes": metrics,
                "quality_gate": "passed" if not failures else "failed",
                "failures": failures,
            }, ensure_ascii=False, indent=2))
            return 0 if not failures else 1
        finally:
            app.dependency_overrides.pop(current_claims, None)
            app.dependency_overrides.pop(get_db, None)
            await db.rollback()
            await db.execute(text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :knowledge_base_id"), {"knowledge_base_id": str(kb_id)})
            await db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))
            await db.commit()

    await engine.dispose()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except Exception as exc:
        print(f"F-03 hybrid quality evaluation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
