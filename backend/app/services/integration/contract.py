"""Enterprise Integration 领域事件契约。

职责：定义跨 Workflow、Agent、Scheduler、Webhook 等边界传递的统一事件信封。
边界：只负责事件身份、版本、租户、幂等与上下文约束，不负责持久化、投递和消息中间件。
关键外部依赖：Python 标准库。
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

_EVENT_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")


@dataclass(frozen=True, slots=True)
class IntegrationEvent:
    """表示一个可持久化、可投递的企业集成事件。

    Args:
        tenant_id: 事件所属租户标识，事件不得跨租户复用。
        event_type: 稳定事件类型，例如 ``workflow.execution.completed``。
        source: 产生事件的领域或组件标识。
        subject: 事件作用对象标识。
        idempotency_key: 生产者提供的幂等键，唯一性由租户、来源和事件类型共同约束。
        payload: 业务载荷；必须是 JSON 可序列化的数据结构。
        schema_version: 事件载荷契约版本。
        event_id: 全局事件标识；未提供时由平台生成。
        occurred_at: 业务事件发生时间；未提供时使用 UTC 当前时间。
        request_id: 关联 HTTP/API 请求标识。
        trace_id: 关联分布式追踪标识。
        metadata: 不参与业务语义的扩展元数据。
    """

    tenant_id: uuid.UUID
    event_type: str
    source: str
    subject: str
    idempotency_key: str
    payload: dict[str, Any]
    schema_version: int = 1
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    request_id: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """校验事件身份和不可变契约约束，避免非法事件进入后续持久化或投递层。"""
        if not _EVENT_TYPE_PATTERN.fullmatch(self.event_type):
            raise ValueError("event_type 必须使用小写字母、数字及 ._- 组成的稳定标识")
        if not self.source.strip():
            raise ValueError("source 不能为空")
        if not self.subject.strip():
            raise ValueError("subject 不能为空")
        if not self.idempotency_key.strip():
            raise ValueError("idempotency_key 不能为空")
        if self.schema_version < 1:
            raise ValueError("schema_version 必须从 1 开始")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at 必须包含时区信息")

    @property
    def deduplication_scope(self) -> tuple[uuid.UUID, str, str, str]:
        """返回幂等唯一性作用域，供后续 Repository 建立数据库唯一约束。"""
        return (self.tenant_id, self.source, self.event_type, self.idempotency_key)

    def as_dict(self) -> dict[str, Any]:
        """返回稳定的 JSON 语义结构，供持久化、日志和测试使用。

        Returns:
            不包含 Python UUID/Datetime 原生对象的事件字典。
        """
        return {
            "event_id": str(self.event_id),
            "tenant_id": str(self.tenant_id),
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "source": self.source,
            "subject": self.subject,
            "idempotency_key": self.idempotency_key,
            "occurred_at": self.occurred_at.isoformat(),
            "request_id": self.request_id,
            "trace_id": self.trace_id,
            "payload": self.payload,
            "metadata": self.metadata,
        }
