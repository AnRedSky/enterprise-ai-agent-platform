"""检索评估运行追踪服务。

职责：将离线检索评估运行、case 结果和质量门禁结果写入统一 Observability/Audit 模型。
边界：不执行生产检索、不创建第二套审计或可观测性实现。
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog
# 独立的真实 Provider 评估脚本不会导入 Workflow API/Router，因此这里显式注册
# AuditLog 所依赖的执行、模型和 Workflow ORM 映射，避免 SQLAlchemy 在独立入口下缺少表。
from app.models.execution import Execution, ExecutionEvent  # noqa: F401
from app.models.model_provider import ModelProfile, ModelProvider  # noqa: F401
from app.models.workflow import Workflow, WorkflowVersion  # noqa: F401
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution  # noqa: F401
from app.services.observability import ObservabilityService


class RetrievalEvaluationTraceService:
    """将评估运行与 Case 结果持久化到既有可观测性和审计模型。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.observability = ObservabilityService(db)

    async def record_run(
        self,
        *,
        evaluation_run_id: str,
        owner_id: UUID,
        tenant_id: UUID | None,
        metadata: dict[str, Any],
        case_reports: list[dict[str, Any]],
        metrics: dict[str, Any],
        regression: dict[str, Any] | None,
        quality_gate: str,
        failures: list[str],
    ):
        execution = await self.observability.start_execution(
            request_id=f"retrieval-evaluation:{evaluation_run_id}",
            trace_id=evaluation_run_id,
            session_id=None,
            agent_id=None,
            agent_version=None,
            model_id=str(metadata.get("model")) if metadata.get("model") else None,
        )

        for index, case in enumerate(case_reports):
            await self.observability.record_event(
                execution,
                span_type="retrieval_evaluation_case",
                started_at=execution.started_at,
                status="failed" if case.get("error") else "completed",
                model_id=str(metadata.get("model")) if metadata.get("model") else None,
                error_message=case.get("error"),
                metadata={
                    "evaluation_run_id": evaluation_run_id,
                    "case_index": index,
                    **case,
                },
            )

        await self.observability.record_event(
            execution,
            span_type="retrieval_evaluation_summary",
            started_at=execution.started_at,
            status="completed" if quality_gate == "passed" else "failed",
            model_id=str(metadata.get("model")) if metadata.get("model") else None,
            metadata={
                "evaluation_run_id": evaluation_run_id,
                **metadata,
                "metrics": metrics,
                "regression": regression,
                "quality_gate": quality_gate,
                "failures": failures,
            },
        )

        await self.observability.finish_execution(
            execution,
            status="completed" if quality_gate in {"passed", "baseline_created"} else "failed",
            error_code="RETRIEVAL_QUALITY_GATE_FAILED" if failures else None,
            error_message="; ".join(failures) if failures else None,
        )

        audit = AuditLog(
            actor_id=owner_id,
            tenant_id=tenant_id,
            execution_id=execution.id,
            action="retrieval_evaluation.completed",
            resource_type="retrieval_evaluation",
            resource_id=evaluation_run_id,
            trace_id=evaluation_run_id,
            status="success" if not failures else "failed",
            error_code="RETRIEVAL_QUALITY_GATE_FAILED" if failures else None,
            metadata_json={
                "evaluation_run_id": evaluation_run_id,
                **metadata,
                "metrics": metrics,
                "regression": regression,
                "quality_gate": quality_gate,
                "failures": failures,
            },
        )
        self.db.add(audit)
        await self.db.commit()
        return execution
