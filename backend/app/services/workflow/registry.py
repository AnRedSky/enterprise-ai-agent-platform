"""Workflow Registry 领域服务。

职责：管理 Workflow、版本及发布状态，并维护租户与所有者访问边界。
边界：只处理 Workflow 领域状态与发布事务，不执行 Workflow Runtime，也不负责 API 协议。
关键依赖：Workflow/WorkflowVersion ORM、AuditLog、Workflow Runtime 与 SQLAlchemy AsyncSession。
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
from app.models.workflow import Workflow, WorkflowVersion


class WorkflowRegistry:
    """Workflow 及版本生命周期领域服务。"""

    ALLOWED_STATUSES = {"draft", "testing", "published", "deprecated", "archived"}
    VERSION_PUBLISHABLE_STATUSES = {"draft", "testing"}

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, tenant_id: UUID, owner_id: UUID, admin: bool = False) -> list[Workflow]:
        query = select(Workflow).where(Workflow.tenant_id == tenant_id).order_by(Workflow.created_at.desc())
        if not admin:
            query = query.where(Workflow.owner_id == owner_id)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get(self, workflow_id: UUID, tenant_id: UUID, owner_id: UUID, admin: bool = False) -> Workflow:
        query = select(Workflow).where(Workflow.id == workflow_id, Workflow.tenant_id == tenant_id)
        if not admin:
            query = query.where(Workflow.owner_id == owner_id)
        workflow = (await self.db.execute(query)).scalar_one_or_none()
        if not workflow:
            raise HTTPException(404, "Workflow 不存在")
        return workflow

    async def create(self, tenant_id: UUID, owner_id: UUID, name: str, description: str) -> Workflow:
        workflow = Workflow(tenant_id=tenant_id, owner_id=owner_id, name=name, description=description, status="draft")
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
            select(WorkflowVersion).where(WorkflowVersion.workflow_id == workflow_id).order_by(
                WorkflowVersion.created_at.desc(), WorkflowVersion.id.desc()
            )
        )
        return list(result.scalars().all())

    async def get_version(self, workflow_id: UUID, version_id: UUID) -> WorkflowVersion:
        version = (
            await self.db.execute(
                select(WorkflowVersion).where(WorkflowVersion.id == version_id, WorkflowVersion.workflow_id == workflow_id)
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
        """发布经过 Runtime Contract 校验的 Workflow 版本。

        Args:
            workflow: 待发布的 Workflow。
            version: 与 Workflow 绑定且处于可发布状态的版本。
            actor_id: 执行发布操作的用户 ID。

        Returns:
            已完成发布状态变更的 WorkflowVersion。

        Raises:
            HTTPException: Workflow、版本关系或 Runtime Definition Contract 不满足发布条件时抛出。
        """
        if workflow.status == "archived":
            raise HTTPException(409, "归档 Workflow 不允许发布")
        if version.workflow_id != workflow.id:
            raise HTTPException(400, "Workflow 与版本不匹配")
        if workflow.published_version_id == version.id and version.status == "published":
            return version
        if version.status not in self.VERSION_PUBLISHABLE_STATUSES and version.status != "published":
            raise HTTPException(409, "当前版本状态不允许发布")

        # 延迟导入避免 Workflow Registry 与 Runtime/Trigger 聚合入口形成循环依赖。
        # 发布版本会直接成为 Scheduler/Trigger/Runtime 的执行输入，必须复用唯一 Runtime Contract。
        from app.runtime.workflow import WorkflowRuntime

        WorkflowRuntime.validate_definition(version.definition)

        previous_id = workflow.published_version_id
        if previous_id and previous_id != version.id:
            previous = (await self.db.execute(select(WorkflowVersion).where(WorkflowVersion.id == previous_id))).scalar_one_or_none()
            if previous and previous.status == "published":
                previous.status = "deprecated"
        version.status = "published"
        workflow.status = "published"
        workflow.published_version_id = version.id
        self.db.add(
            AuditLog(
                actor_id=actor_id,
                action="workflow.publish",
                resource_type="workflow_version",
                resource_id=str(version.id),
                status="success",
                metadata_json={
                    "workflow_id": str(workflow.id),
                    "tenant_id": str(workflow.tenant_id),
                    "version": version.version,
                    "previous_version_id": str(previous_id) if previous_id else None,
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(version)
        await self.db.refresh(workflow)
        return version
