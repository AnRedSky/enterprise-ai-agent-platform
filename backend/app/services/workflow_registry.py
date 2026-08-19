from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
from app.models.workflow import Workflow, WorkflowVersion


class WorkflowRegistry:
    ALLOWED_STATUSES = {"draft", "testing", "published", "deprecated", "archived"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, owner_id: UUID, admin: bool = False) -> list[Workflow]:
        query = select(Workflow).order_by(Workflow.created_at.desc())
        if not admin:
            query = query.where(Workflow.owner_id == owner_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get(self, workflow_id: UUID, owner_id: UUID, admin: bool = False) -> Workflow:
        workflow = (await self.db.execute(select(Workflow).where(Workflow.id == workflow_id))).scalar_one_or_none()
        if not workflow or (not admin and workflow.owner_id != owner_id):
            raise HTTPException(404, "Workflow 不存在")
        return workflow

    async def create(self, owner_id: UUID, name: str, description: str) -> Workflow:
        workflow = Workflow(owner_id=owner_id, name=name, description=description, status="draft")
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def update(self, workflow: Workflow, name: str | None, description: str | None) -> Workflow:
        if workflow.status == "published":
            raise HTTPException(409, "已发布 Workflow 不允许原地修改")
        if workflow.status == "archived":
            raise HTTPException(409, "归档 Workflow 不允许修改")
        if name is not None:
            workflow.name = name
        if description is not None:
            workflow.description = description
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def delete(self, workflow: Workflow) -> None:
        if workflow.status == "published":
            raise HTTPException(409, "已发布 Workflow 不允许删除")
        await self.db.delete(workflow)
        await self.db.commit()

    async def versions(self, workflow_id: UUID) -> list[WorkflowVersion]:
        result = await self.db.execute(
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(WorkflowVersion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_version(self, workflow_id: UUID, version_id: UUID) -> WorkflowVersion:
        version = (
            await self.db.execute(
                select(WorkflowVersion).where(
                    WorkflowVersion.id == version_id,
                    WorkflowVersion.workflow_id == workflow_id,
                )
            )
        ).scalar_one_or_none()
        if not version:
            raise HTTPException(404, "Workflow 版本不存在")
        return version

    async def create_version(self, workflow: Workflow, created_by: UUID, definition: dict) -> WorkflowVersion:
        if workflow.status == "archived":
            raise HTTPException(409, "归档 Workflow 不允许创建新版本")
        versions = await self.versions(workflow.id)
        max_minor = -1
        for item in versions:
            try:
                major, minor, _patch = (int(part) for part in item.version.split("."))
            except ValueError:
                continue
            if major == 1 and minor > max_minor:
                max_minor = minor
        version = WorkflowVersion(
            workflow_id=workflow.id,
            version=f"1.{max_minor + 1}.0",
            definition=definition,
            status="draft",
            created_by=created_by,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        return version

    async def publish(self, workflow: Workflow, version: WorkflowVersion, actor_id: UUID) -> WorkflowVersion:
        if workflow.status == "archived":
            raise HTTPException(409, "归档 Workflow 不允许发布")
        if version.status in {"deprecated", "archived"}:
            raise HTTPException(409, "当前版本状态不允许发布")

        version.status = "published"
        workflow.status = "published"
        self.db.add(
            AuditLog(
                actor_id=actor_id,
                action="workflow.publish",
                resource_type="workflow_version",
                resource_id=str(version.id),
                status="success",
                metadata_json={"workflow_id": str(workflow.id), "version": version.version},
            )
        )
        await self.db.commit()
        await self.db.refresh(version)
        await self.db.refresh(workflow)
        return version
