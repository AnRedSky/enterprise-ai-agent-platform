"""Workflow Durable Resume 自动恢复策略。

职责：集中定义 failed Execution 自动恢复的资格、冷却时间、最大恢复次数与安全边界。
边界：只做纯规则判断，不读取数据库、不创建 Resume Execution、不获取 Worker ownership。
关键依赖：WorkflowExecutionResumeAssessment 提供的 Checkpoint 恢复候选事实；调用方负责持久化与幂等。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class WorkflowExecutionRecoveryPolicy:
    """Durable Resume 自动恢复的稳定策略配置。"""

    max_attempts: int = 3
    cooldown_seconds: int = 60

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or self.max_attempts < 0:
            raise ValueError("max_attempts 必须为非负整数")
        if isinstance(self.cooldown_seconds, bool) or self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds 必须为非负整数")


@dataclass(frozen=True)
class WorkflowExecutionRecoveryDecision:
    """自动恢复策略的只读决策结果。"""

    eligible: bool
    reason_code: str
    attempt_count: int
    max_attempts: int
    retry_after: datetime | None = None


class WorkflowExecutionRecoveryPolicyEvaluator:
    """根据已持久化事实判断 failed Execution 是否允许自动 Resume。"""

    def __init__(self, policy: WorkflowExecutionRecoveryPolicy | None = None):
        self.policy = policy or WorkflowExecutionRecoveryPolicy()

    def evaluate(
        self,
        *,
        execution_status: str,
        worker_owner: str | None,
        checkpoint_eligible: bool,
        resume_attempt_count: int,
        ended_at: datetime | None,
        now: datetime | None = None,
    ) -> WorkflowExecutionRecoveryDecision:
        """评估自动 Resume 是否满足当前策略，不产生任何持久化副作用。

        Args:
            execution_status: 当前 Execution 持久化状态，自动恢复只接受 failed。
            worker_owner: 当前 Worker ownership；非空表示禁止恢复。
            checkpoint_eligible: Checkpoint Recovery Service 是否确认存在合法恢复边界。
            resume_attempt_count: 当前 Execution 之前已经发生的 Resume 恢复次数。
            ended_at: Source Execution 进入 failed 终态的时间，用于计算冷却窗口。
            now: 可选当前时间；未传入时使用 UTC 当前时间。

        Returns:
            包含 eligible、拒绝原因、已使用次数与下一次允许时间的只读决策。

        Raises:
            ValueError: 恢复次数为负数时拒绝非法调用。

        设计边界：
            1. 自动恢复不改变 failed 状态，真正创建 Resume Execution 必须继续走 Domain Service。
            2. active Worker ownership 优先阻断，避免自动恢复绕过 ownership fencing。
            3. 最大次数是恢复尝试次数，不是普通 Retry 次数；两套策略保持独立。
            4. 冷却窗口以 Source failed 的持久化 ended_at 为准，避免 Scheduler 高频轮询重复创建恢复任务。
            5. `max_attempts == 0` 明确表示关闭自动恢复，不影响人工 Resume API。
        """
        if resume_attempt_count < 0:
            raise ValueError("resume_attempt_count 不能为负数")
        current = now or datetime.now(UTC)
        if current.tzinfo is not None:
            current = current.astimezone(UTC).replace(tzinfo=None)
        if ended_at is not None and ended_at.tzinfo is not None:
            ended_at = ended_at.astimezone(UTC).replace(tzinfo=None)

        if self.policy.max_attempts == 0:
            return WorkflowExecutionRecoveryDecision(False, "automatic_recovery_disabled", resume_attempt_count, 0)
        if execution_status != "failed":
            return WorkflowExecutionRecoveryDecision(False, "execution_not_failed", resume_attempt_count, self.policy.max_attempts)
        if worker_owner is not None:
            return WorkflowExecutionRecoveryDecision(False, "worker_ownership_active", resume_attempt_count, self.policy.max_attempts)
        if not checkpoint_eligible:
            return WorkflowExecutionRecoveryDecision(False, "checkpoint_not_eligible", resume_attempt_count, self.policy.max_attempts)
        if resume_attempt_count >= self.policy.max_attempts:
            return WorkflowExecutionRecoveryDecision(False, "max_recovery_attempts_reached", resume_attempt_count, self.policy.max_attempts)

        retry_after = None
        if ended_at is not None:
            retry_after = ended_at + timedelta(seconds=self.policy.cooldown_seconds)
            if current < retry_after:
                return WorkflowExecutionRecoveryDecision(False, "recovery_cooldown_active", resume_attempt_count, self.policy.max_attempts, retry_after)

        return WorkflowExecutionRecoveryDecision(True, "eligible", resume_attempt_count, self.policy.max_attempts, retry_after)
