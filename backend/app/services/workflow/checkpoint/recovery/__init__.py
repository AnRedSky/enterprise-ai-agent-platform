"""Workflow Checkpoint Recovery 正式领域入口。

职责：暴露恢复评估、自动恢复策略、条件求值、DAG frontier、状态合并、Join、可观测性与 Resume 能力。
边界：Recovery Planner / Policy / Automatic Recovery Service / State Merge / Join / Trace Link 不直接启动 Runtime；实际 Execution 仍由 Worker + WorkflowExecutionService 完成。
关键依赖：各 Recovery 领域子模块及其纯内存 Contract。
"""

from app.services.workflow.checkpoint.recovery.automatic import WorkflowExecutionAutomaticRecoveryResult, WorkflowExecutionAutomaticRecoveryService
from app.services.workflow.checkpoint.recovery.condition import WorkflowConditionEvaluation, WorkflowConditionEvaluator
from app.services.workflow.checkpoint.recovery.dag_contract import WorkflowDagContract, WorkflowDagContractValidator, WorkflowDagEdge
from app.services.workflow.checkpoint.recovery.dag_join import WorkflowDagJoinReadiness, WorkflowDagJoinReadinessService
from app.services.workflow.checkpoint.recovery.dag_join_executor import WorkflowDagJoinExecutionResult, WorkflowDagJoinExecutor
from app.services.workflow.checkpoint.recovery.dag_planner import WorkflowDagResumePlan, WorkflowDagResumePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime import WorkflowDagResumeRuntimePlan, WorkflowDagResumeRuntimePlanner
from app.services.workflow.checkpoint.recovery.dag_runtime_sequence import WorkflowDagResumeRuntimeSequencePlanner
from app.services.workflow.checkpoint.recovery.dag_state_merge import WorkflowDagBranchState, WorkflowDagBranchStateMergeService, WorkflowDagStateMergePlan
from app.services.workflow.checkpoint.recovery.observability import RECOVERY_ATTEMPT, RECOVERY_SCAN_COMPLETED, RECOVERY_TRACE_FINISHED, RECOVERY_TRACE_STARTED, WorkflowRecoveryEvent, WorkflowRecoveryEventLogger, WorkflowRecoveryTelemetry
from app.services.workflow.checkpoint.recovery.planner import WorkflowExecutionResumePlanner, WorkflowResumePlan
from app.services.workflow.checkpoint.recovery.policy import WorkflowExecutionRecoveryDecision, WorkflowExecutionRecoveryPolicy, WorkflowExecutionRecoveryPolicyEvaluator
from app.services.workflow.checkpoint.recovery.service import WorkflowExecutionCheckpointRecoveryService, WorkflowExecutionResumeAssessment
from app.services.workflow.checkpoint.recovery.trace_link import WorkflowRecoveryTraceLinkService

__all__ = [
    "WorkflowConditionEvaluation", "WorkflowConditionEvaluator",
    "WorkflowDagBranchState", "WorkflowDagBranchStateMergeService", "WorkflowDagContract", "WorkflowDagContractValidator", "WorkflowDagEdge",
    "WorkflowDagJoinExecutionResult", "WorkflowDagJoinExecutor", "WorkflowDagJoinReadiness", "WorkflowDagJoinReadinessService",
    "WorkflowDagResumePlan", "WorkflowDagResumePlanner", "WorkflowDagResumeRuntimePlan", "WorkflowDagResumeRuntimePlanner", "WorkflowDagResumeRuntimeSequencePlanner", "WorkflowDagStateMergePlan",
    "WorkflowExecutionAutomaticRecoveryResult", "WorkflowExecutionAutomaticRecoveryService", "WorkflowExecutionCheckpointRecoveryService", "WorkflowExecutionRecoveryDecision", "WorkflowExecutionRecoveryPolicy", "WorkflowExecutionRecoveryPolicyEvaluator", "WorkflowExecutionResumeAssessment", "WorkflowExecutionResumePlanner",
    "WorkflowRecoveryEvent", "WorkflowRecoveryEventLogger", "WorkflowRecoveryTelemetry", "WorkflowRecoveryTraceLinkService", "WorkflowResumePlan",
    "RECOVERY_ATTEMPT", "RECOVERY_SCAN_COMPLETED", "RECOVERY_TRACE_STARTED", "RECOVERY_TRACE_FINISHED",
]
