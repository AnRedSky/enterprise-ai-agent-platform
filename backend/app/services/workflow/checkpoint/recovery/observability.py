"""Workflow Recovery 可观测事件模型。

职责：定义 Recovery Domain 与 Scheduler 共用的结构化事件字段，统一日志事件名称与敏感数据边界。
边界：只负责事件建模与日志输出，不负责数据库持久化、Metrics exporter 或 Trace provider 生命周期。
关键依赖：Python logging、dataclasses、UUID、datetime。
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID


RECOVERY_SCAN_COMPLETED = "workflow.recovery.scan.completed"
RECOVERY_ATTEMPT = "workflow.recovery.attempt"


@dataclass(frozen=True)
class WorkflowRecoveryEvent:
    """单次 Recovery 可观测事件的稳定字段。"""

    event_name: str
    execution_id: UUID | None = None
    resume_execution_id: UUID | None = None
    reason_code: str | None = None
    attempt_count: int | None = None
    max_attempts: int | None = None
    candidates: int | None = None
    eligible: int | None = None
    recovered: int | None = None
    rejected: int | None = None
    contention: int | None = None
    failed: int | None = None
    scan_limit: int | None = None
    occurred_at: datetime | None = None

    def to_log_fields(self) -> dict[str, object]:
        """转换为结构化日志字段。

        Returns:
            可直接作为 Python logging `extra` 使用的字段字典；不包含 Checkpoint state_data 或 Secret。
        """
        fields = asdict(self)
        fields = {key: value for key, value in fields.items() if value is not None}
        if self.occurred_at is not None:
            fields["occurred_at"] = self.occurred_at.isoformat()
        for key in ("execution_id", "resume_execution_id"):
            value = fields.get(key)
            if isinstance(value, UUID):
                fields[key] = str(value)
        return fields


class WorkflowRecoveryEventLogger:
    """Recovery 事件的统一日志出口。"""

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def emit(self, event: WorkflowRecoveryEvent, *, level: int = logging.INFO) -> None:
        """输出一个 Recovery 结构化事件。

        Args:
            event: 要输出的 Recovery 事件；调用方不得把业务 payload、Secret 或 Checkpoint state_data 放入事件。
            level: Python logging 日志等级。

        Returns:
            None。

        副作用：写入当前应用日志；不会修改数据库或 Recovery 状态。
        """
        self.logger.log(level, event.event_name, extra=event.to_log_fields())
