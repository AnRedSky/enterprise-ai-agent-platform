from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.schemas.knowledge_ingestion import KnowledgeChunkOut, KnowledgeIngestRequest, KnowledgeIngestOut
from app.services.knowledge_ingestion import KnowledgeIngestionService

router = APIRouter()


def _identity(claims: dict) -> tuple[UUID, bool]:
    return UUID(claims["sub"]), "admin" in claims.get("roles", [])


@router.post("/versions/{version_id}/ingest", response_model=KnowledgeIngestOut)
async def ingest_version(
    version_id: UUID,
    payload: KnowledgeIngestRequest | None = None,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    options = payload or KnowledgeIngestRequest()
    version, chunk_count = await KnowledgeIngestionService(db).ingest(
        version_id,
        owner_id,
        is_admin,
        max_chars=options.max_chars,
        overlap_chars=options.overlap_chars,
    )
    return {
        "version_id": version.id,
        "ingestion_status": version.ingestion_status,
        "vector_index_status": version.vector_index_status,
        "embedding_model": version.embedding_model,
        "chunk_count": chunk_count,
        "content_hash": version.content_hash or "",
    }


@router.get("/versions/{version_id}/chunks", response_model=list[KnowledgeChunkOut])
async def list_chunks(
    version_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    return await KnowledgeIngestionService(db).list_chunks(version_id, owner_id, is_admin)
