"""验证 API Service 与 Scheduler Service 的进程职责边界。

测试范围：API 应用不再创建 Scheduler；Scheduler Service 独立入口只负责生命周期编排，并复用正式
`ScheduledTriggerScheduler`、`WorkflowRecoveryScheduler`、`RuntimeAlertScheduler` 与
`RuntimeNotificationScheduler` 实现，不复制调度、恢复、告警或通知路由业务规则。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.entrypoints import scheduler as scheduler_entrypoint


def test_api_service_does_not_start_scheduler():
    """API Service 启动后只提供 HTTP 能力，不创建 Scheduler 后台任务。"""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["service"] == "api"
    assert not hasattr(app.state, "scheduled_trigger_scheduler")


@pytest.mark.asyncio
async def test_scheduler_service_owns_scheduler_lifecycle():
    """Scheduler Dispatch 异常时，全部后台循环必须停止并传播原始异常。"""
    fake_scheduler = MagicMock()
    fake_scheduler.run_forever = AsyncMock(side_effect=RuntimeError("test-stop"))
    fake_scheduler.stop = MagicMock()

    fake_recovery_scheduler = MagicMock()
    fake_recovery_scheduler.run_forever = AsyncMock()
    fake_recovery_scheduler.stop = MagicMock()

    fake_alert_scheduler = MagicMock()
    fake_alert_scheduler.run_forever = AsyncMock()
    fake_alert_scheduler.stop = MagicMock()

    fake_notification_scheduler = MagicMock()
    fake_notification_scheduler.run_forever = AsyncMock()
    fake_notification_scheduler.stop = MagicMock()

    with patch.object(
        scheduler_entrypoint, "ScheduledTriggerScheduler", return_value=fake_scheduler
    ) as scheduler_factory, patch.object(
        scheduler_entrypoint,
        "WorkflowRecoveryScheduler",
        return_value=fake_recovery_scheduler,
    ) as recovery_factory, patch.object(
        scheduler_entrypoint,
        "RuntimeAlertScheduler",
        return_value=fake_alert_scheduler,
    ) as alert_factory, patch.object(
        scheduler_entrypoint,
        "RuntimeNotificationScheduler",
        return_value=fake_notification_scheduler,
    ) as notification_factory:
        with pytest.raises(RuntimeError, match="test-stop"):
            await scheduler_entrypoint.run_scheduler_service()

    scheduler_factory.assert_called_once_with(settings.scheduler_poll_interval_seconds)
    recovery_factory.assert_called_once_with(
        poll_interval_seconds=settings.scheduler_poll_interval_seconds
    )
    alert_factory.assert_called_once_with(settings.scheduler_poll_interval_seconds)
    notification_factory.assert_called_once_with(settings.scheduler_poll_interval_seconds)
    fake_scheduler.run_forever.assert_awaited_once()
    fake_scheduler.stop.assert_called_once()
    fake_recovery_scheduler.stop.assert_called_once()
    fake_recovery_scheduler.run_forever.assert_awaited_once()
    fake_alert_scheduler.stop.assert_called_once()
    fake_alert_scheduler.run_forever.assert_awaited_once()
    fake_notification_scheduler.stop.assert_called_once()
    fake_notification_scheduler.run_forever.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_service_recovers_from_recovery_scan_failure_by_failing_service():
    """Recovery Scan 异常时不能留下其他后台循环，必须统一失败收敛。"""
    fake_scheduler = MagicMock()
    fake_scheduler.run_forever = AsyncMock()
    fake_scheduler.stop = MagicMock()

    fake_recovery_scheduler = MagicMock()
    fake_recovery_scheduler.run_forever = AsyncMock(side_effect=RuntimeError("recovery-stop"))
    fake_recovery_scheduler.stop = MagicMock()

    fake_alert_scheduler = MagicMock()
    fake_alert_scheduler.run_forever = AsyncMock()
    fake_alert_scheduler.stop = MagicMock()

    fake_notification_scheduler = MagicMock()
    fake_notification_scheduler.run_forever = AsyncMock()
    fake_notification_scheduler.stop = MagicMock()

    with patch.object(
        scheduler_entrypoint, "ScheduledTriggerScheduler", return_value=fake_scheduler
    ), patch.object(
        scheduler_entrypoint,
        "WorkflowRecoveryScheduler",
        return_value=fake_recovery_scheduler,
    ), patch.object(
        scheduler_entrypoint,
        "RuntimeAlertScheduler",
        return_value=fake_alert_scheduler,
    ), patch.object(
        scheduler_entrypoint,
        "RuntimeNotificationScheduler",
        return_value=fake_notification_scheduler,
    ):
        with pytest.raises(RuntimeError, match="recovery-stop"):
            await scheduler_entrypoint.run_scheduler_service()

    fake_scheduler.stop.assert_called_once()
    fake_recovery_scheduler.stop.assert_called_once()
    fake_alert_scheduler.stop.assert_called_once()
    fake_notification_scheduler.stop.assert_called_once()
    fake_scheduler.run_forever.assert_awaited_once()
    fake_recovery_scheduler.run_forever.assert_awaited_once()
    fake_alert_scheduler.run_forever.assert_awaited_once()
    fake_notification_scheduler.run_forever.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_service_identity_is_not_configuration_switch():
    """Scheduler Service 的进程身份不由 SCHEDULER_ENABLED 配置决定。"""
    assert not hasattr(settings, "scheduler_enabled")

    fake_scheduler = MagicMock()
    fake_scheduler.run_forever = AsyncMock(side_effect=RuntimeError("test-stop"))
    fake_scheduler.stop = MagicMock()

    fake_recovery_scheduler = MagicMock()
    fake_recovery_scheduler.run_forever = AsyncMock()
    fake_recovery_scheduler.stop = MagicMock()

    fake_alert_scheduler = MagicMock()
    fake_alert_scheduler.run_forever = AsyncMock()
    fake_alert_scheduler.stop = MagicMock()

    fake_notification_scheduler = MagicMock()
    fake_notification_scheduler.run_forever = AsyncMock()
    fake_notification_scheduler.stop = MagicMock()

    with patch.object(
        scheduler_entrypoint, "ScheduledTriggerScheduler", return_value=fake_scheduler
    ), patch.object(
        scheduler_entrypoint,
        "WorkflowRecoveryScheduler",
        return_value=fake_recovery_scheduler,
    ), patch.object(
        scheduler_entrypoint,
        "RuntimeAlertScheduler",
        return_value=fake_alert_scheduler,
    ), patch.object(
        scheduler_entrypoint,
        "RuntimeNotificationScheduler",
        return_value=fake_notification_scheduler,
    ):
        with pytest.raises(RuntimeError, match="test-stop"):
            await scheduler_entrypoint.run_scheduler_service()

    fake_scheduler.stop.assert_called_once()
    fake_recovery_scheduler.stop.assert_called_once()
    fake_alert_scheduler.stop.assert_called_once()
    fake_notification_scheduler.stop.assert_called_once()
