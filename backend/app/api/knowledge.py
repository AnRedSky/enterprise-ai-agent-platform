from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import current_claims, require_roles
from app.dependencies.db import get_db
from app.schemas.knowledge import (
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBasePage,
    KnowledgeBaseUpdate,
    KnowledgeDocumentCreate,
    KnowledgeDocumentOut,
    KnowledgeDocumentPage,
    KnowledgeDocumentUpdate,
    KnowledgeDocumentVersionCreate,
    KnowledgeDocumentVersionOut,
)
from app.services.knowledge_registry import KnowledgeRegistry

router = APIRouter()


def _identity(claims: dict) -> tuple[UUID, bool]:
    return UUID(claims["sub"]), "admin" in claims.get("roles", [])


@router.get("", response_model=KnowledgeBasePage)
async def list_knowledge_bases(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    items, total = await KnowledgeRegistry(db).list_knowledge_bases(owner_id, page, page_size, is_admin)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("", response_model=KnowledgeBaseOut)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, _ = _identity(claims)
    return await KnowledgeRegistry(db).create_knowledge_base(owner_id, **payload.model_dump())


@router.get("/{knowledge_base_id}", response_model=KnowledgeBaseOut)
async def get_knowledge_base(
    knowledge_base_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    return await KnowledgeRegistry(db).get_knowledge_base(knowledge_base_id, owner_id, is_admin)


@router.patch("/{knowledge_base_id}", response_model=KnowledgeBaseOut)
async def update_knowledge_base(
    knowledge_base_id: UUID,
    payload: KnowledgeBaseUpdate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    registry = KnowledgeRegistry(db)
    item = await registry.get_knowledge_base(knowledge_base_id, owner_id, is_admin)
    return await registry.update_knowledge_base(item, **payload.model_dump(exclude_unset=True))


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    knowledge_base_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    registry = KnowledgeRegistry(db)
    item = await registry.get_knowledge_base(knowledge_base_id, owner_id, is_admin)
    await registry.delete_knowledge_base(item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{knowledge_base_id}/documents", response_model=KnowledgeDocumentPage)
async def list_documents(
    knowledge_base_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    items, total = await KnowledgeRegistry(db).list_documents(knowledge_base_id, owner_id, page, page_size, is_admin)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/{knowledge_base_id}/documents", response_model=KnowledgeDocumentOut)
async def create_document(
    knowledge_base_id: UUID,
    payload: KnowledgeDocumentCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    return await KnowledgeRegistry(db).create_document(knowledge_base_id, owner_id, payload.model_dump(), is_admin)


@router.get("/{knowledge_base_id}/documents/{document_id}", response_model=KnowledgeDocumentOut)
async def get_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    item = await KnowledgeRegistry(db).get_document(document_id, owner_id, is_admin)
    if item.knowledge_base_id != knowledge_base_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document 不存在或无权访问")
    return item


@router.patch("/{knowledge_base_id}/documents/{document_id}", response_model=KnowledgeDocumentOut)
async def update_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    payload: KnowledgeDocumentUpdate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    registry = KnowledgeRegistry(db)
    item = await registry.get_document(document_id, owner_id, is_admin)
    if item.knowledge_base_id != knowledge_base_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document 不存在或无权访问")
    return await registry.update_document(item, **payload.model_dump(exclude_unset=True))


@router.delete("/{knowledge_base_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    knowledge_base_id: UUID,
    document_id: UUID,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    registry = KnowledgeRegistry(db)
    item = await registry.get_document(document_id, owner_id, is_admin)
    if item.knowledge_base_id != knowledge_base_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document 不存在或无权访问")
    await registry.delete_document(item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{knowledge_base_id}/documents/{document_id}/versions", response_model=list[KnowledgeDocumentVersionOut])
async def list_versions(
    knowledge_base_id: UUID,
    document_id: UUID,
    claims=Depends(current_claims),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    registry = KnowledgeRegistry(db)
    document = await registry.get_document(document_id, owner_id, is_admin)
    if document.knowledge_base_id != knowledge_base_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document 不存在或无权访问")
    return await registry.list_versions(document, owner_id, is_admin)


@router.post("/{knowledge_base_id}/documents/{document_id}/versions", response_model=KnowledgeDocumentVersionOut)
async def create_version(
    knowledge_base_id: UUID,
    document_id: UUID,
    payload: KnowledgeDocumentVersionCreate,
    claims=Depends(require_roles("user", "admin")),
    db: AsyncSession = Depends(get_db),
):
    owner_id, is_admin = _identity(claims)
    registry = KnowledgeRegistry(db)
    document = await registry.get_document(document_id, owner_id, is_admin)
    if document.knowledge_base_id != knowledge_base_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document 不存在或无权访问")
    return await registry.create_version(document, owner_id, owner_id, payload.model_dump(), is_admin)
