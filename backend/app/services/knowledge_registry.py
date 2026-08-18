from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentVersion


class KnowledgeRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _is_admin(is_admin: bool) -> bool:
        return is_admin

    async def get_knowledge_base(self, knowledge_base_id: UUID, owner_id: UUID, is_admin: bool = False) -> KnowledgeBase:
        stmt = select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id)
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        item = (await self.db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Knowledge Base 不存在或无权访问")
        return item

    async def list_knowledge_bases(self, owner_id: UUID, page: int, page_size: int, is_admin: bool = False):
        filters = [] if is_admin else [KnowledgeBase.owner_id == owner_id]
        total = int((await self.db.execute(select(func.count()).select_from(KnowledgeBase).where(*filters))).scalar_one())
        items = (await self.db.execute(
            select(KnowledgeBase).where(*filters).order_by(KnowledgeBase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return items, total

    async def create_knowledge_base(self, owner_id: UUID, name: str, description: str, status: str):
        item = KnowledgeBase(owner_id=owner_id, name=name, description=description, status=status)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_knowledge_base(self, item: KnowledgeBase, **values):
        for key, value in values.items():
            if value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_knowledge_base(self, item: KnowledgeBase):
        await self.db.delete(item)
        await self.db.commit()

    async def get_document(self, document_id: UUID, owner_id: UUID, is_admin: bool = False) -> KnowledgeDocument:
        stmt = select(KnowledgeDocument).join(KnowledgeBase, KnowledgeBase.id == KnowledgeDocument.knowledge_base_id).where(KnowledgeDocument.id == document_id)
        if not is_admin:
            stmt = stmt.where(KnowledgeBase.owner_id == owner_id)
        item = (await self.db.execute(stmt)).scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Document 不存在或无权访问")
        return item

    async def list_documents(self, knowledge_base_id: UUID, owner_id: UUID, page: int, page_size: int, is_admin: bool = False):
        await self.get_knowledge_base(knowledge_base_id, owner_id, is_admin)
        filters = [KnowledgeDocument.knowledge_base_id == knowledge_base_id]
        total = int((await self.db.execute(select(func.count()).select_from(KnowledgeDocument).where(*filters))).scalar_one())
        items = (await self.db.execute(
            select(KnowledgeDocument).where(*filters).order_by(KnowledgeDocument.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )).scalars().all()
        return items, total

    async def create_document(self, knowledge_base_id: UUID, owner_id: UUID, values: dict, is_admin: bool = False):
        await self.get_knowledge_base(knowledge_base_id, owner_id, is_admin)
        item = KnowledgeDocument(knowledge_base_id=knowledge_base_id, **values)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_document(self, item: KnowledgeDocument, **values):
        for key, value in values.items():
            if value is not None:
                setattr(item, key, value)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_document(self, item: KnowledgeDocument):
        await self.db.delete(item)
        await self.db.commit()

    async def list_versions(self, document: KnowledgeDocument, owner_id: UUID, is_admin: bool = False):
        await self.get_document(document.id, owner_id, is_admin)
        return (await self.db.execute(
            select(KnowledgeDocumentVersion).where(KnowledgeDocumentVersion.document_id == document.id).order_by(KnowledgeDocumentVersion.created_at.desc())
        )).scalars().all()

    async def create_version(self, document: KnowledgeDocument, owner_id: UUID, created_by: UUID, values: dict, is_admin: bool = False):
        await self.get_document(document.id, owner_id, is_admin)
        version = KnowledgeDocumentVersion(document_id=document.id, created_by=created_by, **values)
        self.db.add(version)
        await self.db.flush()
        if version.status == "ready":
            document.current_version_id = version.id
        await self.db.commit()
        await self.db.refresh(version)
        await self.db.refresh(document)
        return version
