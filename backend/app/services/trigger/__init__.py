"""Trigger 领域服务公开入口。

职责：统一暴露手动、定时和 Webhook Trigger 的领域服务与配置契约。
边界：不实现 Workflow Registry、Execution 状态机或 Scheduler 持久化；这些能力分别复用对应正式模块。
关键依赖：Trigger Service、Webhook Service、Trigger 配置契约。
"""

from .schedule import ScheduledTriggerConfig, WebhookTriggerConfig, validate_trigger_config, verify_webhook_secret
from .service import WorkflowTriggerService
from .webhook import WebhookTriggerService

__all__ = [
    "ScheduledTriggerConfig",
    "WebhookTriggerConfig",
    "WorkflowTriggerService",
    "WebhookTriggerService",
    "validate_trigger_config",
    "verify_webhook_secret",
]
