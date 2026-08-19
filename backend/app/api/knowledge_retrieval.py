from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.dependencies.db import get_db
from app.schemas.knowledge_retrieval import KnowledgeRetrievalRequest, KnowledgeRetrievalResponse
from app.services.vector_knowledge_retrieval import KnowledgeRetrievalRouterService

router = APIRouter()


def _identity(claims: dict) -> tuple[UUID, bool]:
    return UUID(claims["sub"]), "admin" in claims.get("roles", [])


@router.post("/retrieve", response_model=KnowledgeRetrievalResponse)
async def retrieve_knowledge(
    payload: KnowledgeRetrievalRequest,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    results, retrieval_mode, fallback_used = await KnowledgeRetrievalRouterService(db).retrieve(
        mode=payload.mode,
        fallback_to_lexical=payload.fallback_to_lexical,
        query=payload.query,
        top_k=payload.top_k,
        owner_id=owner_id,
        is_admin=is_admin,
        knowledge_base_id=payload.knowledge_base_id,
        document_id=payload.document_id,
        min_score=payload.min_score,
        dedupe=payload.dedupe,
    )
    return {
        "query": payload.query,
        "top_k": payload.top_k,
        "min_score": payload.min_score,
        "retrieval_mode": retrieval_mode,
        "fallback_used": fallback_used,
        "results": results,
    }
