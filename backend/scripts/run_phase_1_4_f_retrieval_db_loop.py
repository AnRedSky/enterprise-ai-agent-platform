"""Local end-to-end Retrieval API -> Vector -> Hybrid -> Citation validation.

The script uses a real PostgreSQL/pgvector database and the real application
services. When EMBEDDING_PROVIDER=mock, only the embedding generation step is
deterministic/local; indexing, SQL retrieval, RBAC scope, hybrid fusion,
FastAPI routing, and citation hydration remain real application paths.
"""

from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

import httpx
from sqlalchemy import delete, select, text

from app.core.auth import current_claims
from app.core.config import settings
from app.dependencies.db import SessionLocal, engine, get_db
from app.main import app
from app.models.core import User
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentVersion
from app.services.knowledge_ingestion import KnowledgeIngestionService


async def run() -> None:
    if settings.vector_provider != "pgvector":
        raise RuntimeError("VECTOR_PROVIDER=pgvector is required")
    if settings.embedding_provider not in {"mock", "openai-compatible"}:
        raise RuntimeError("EMBEDDING_PROVIDER must be mock or openai-compatible")

    async with SessionLocal() as db:
        owner = (
            await db.execute(select(User).where(User.status == "active").order_by(User.created_at.asc()).limit(1))
        ).scalar_one_or_none()
        if owner is None:
            raise RuntimeError("No active user exists. Create/login a local user before running this validation.")

        knowledge_base_id = uuid4()
        document_id = uuid4()
        version_id = uuid4()
        knowledge_base = KnowledgeBase(
            id=knowledge_base_id,
            name="Phase 1.4-F DB Loop Fixture",
            description="Ephemeral local validation fixture",
            owner_id=owner.id,
            status="active",
        )
        document = KnowledgeDocument(
            id=document_id,
            knowledge_base_id=knowledge_base_id,
            title="Enterprise Agent Authorization Guide",
            source_type="manual",
            source_uri="local://phase-1.4-f",
            status="active",
        )
        version = KnowledgeDocumentVersion(
            id=version_id,
            document_id=document_id,
            version="1.0",
            status="draft",
            ingestion_status="pending",
            vector_index_status="pending",
            source_uri="local://phase-1.4-f",
            content_text=(
                "企业智能体权限控制要求在知识检索阶段执行 Knowledge Base owner isolation。"
                "检索结果进入模型上下文之前必须完成 RBAC 过滤，并保留文档、版本、Chunk 与 citation 可追溯信息。"
            ),
            created_by=owner.id,
        )
        db.add_all([knowledge_base, document, version])
        await db.commit()

        async def override_db():
            yield db

        app.dependency_overrides[current_claims] = lambda: {
            "sub": str(owner.id),
            "roles": ["user"],
        }
        app.dependency_overrides[get_db] = override_db

        try:
            _, chunk_count = await KnowledgeIngestionService(db).ingest(version_id, owner.id)
            if chunk_count == 0:
                raise RuntimeError("fixture ingestion produced no chunks")

            await db.refresh(version)
            if version.vector_index_status != "ready":
                raise RuntimeError(f"vector indexing did not become ready: {version.vector_index_status}")

            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.post(
                    "/api/v1/knowledge/retrieve",
                    json={
                        "query": "企业智能体权限控制",
                        "top_k": 5,
                        "mode": "hybrid",
                        "knowledge_base_id": str(knowledge_base_id),
                        "lexical_weight": 0.5,
                        "vector_weight": 0.5,
                        "dedupe": True,
                    },
                )

            if response.status_code != 200:
                raise RuntimeError(f"retrieval API failed: {response.status_code} {response.text}")

            payload = response.json()
            results = payload.get("results", [])
            if payload.get("retrieval_mode") != "hybrid":
                raise RuntimeError(f"unexpected retrieval mode: {payload.get('retrieval_mode')}")
            if not results:
                raise RuntimeError("hybrid retrieval returned no results")

            for item in results:
                required = {
                    "document_id",
                    "document_version_id",
                    "chunk_id",
                    "citation",
                    "content",
                    "source_document",
                    "relevance_score",
                }
                missing = sorted(required - item.keys())
                if missing:
                    raise RuntimeError(f"citation hydration missing fields: {missing}")

            print("Retrieval DB loop validation passed")
            print(f"source=PostgreSQL/pgvector; embedding={settings.embedding_provider}")
            print(f"knowledge_base_id={knowledge_base_id}; chunks={chunk_count}; results={len(results)}")
            for item in results:
                print(
                    f"citation={item['citation']} score={item['relevance_score']} "
                    f"sources={item.get('retrieval_sources', [])} chunk_id={item['chunk_id']}"
                )
        finally:
            app.dependency_overrides.pop(current_claims, None)
            app.dependency_overrides.pop(get_db, None)
            await db.rollback()
            await db.execute(
                text("DELETE FROM knowledge_chunks WHERE knowledge_base_id = :knowledge_base_id"),
                {"knowledge_base_id": str(knowledge_base_id)},
            )
            await db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
            await db.commit()

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as exc:
        print(f"Retrieval DB loop validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
