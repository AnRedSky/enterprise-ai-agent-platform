"""FastAPI 生命周期测试：验证 Scheduler 后台任务按配置启动、停止并完成退出。"""

import asyncio

import pytest

import app.main as main_module


class _FakeScheduler:
    """生命周期测试替身，只验证 Scheduler 的启动与停止边界，不复制生产调度规则。"""

    instances: list["_FakeScheduler"] = []

    def __init__(self, poll_interval_seconds: float):
        self.poll_interval_seconds = poll_interval_seconds
        self.started = asyncio.Event()
        self.finished = asyncio.Event()
        self.stopped = False
        self.__class__.instances.append(self)

    async def run_forever(self) -> None:
        """等待停止请求并明确标记后台任务已经完成。"""
        self.started.set()
        while not self.stopped:
            await asyncio.sleep(0)
        self.finished.set()

    def stop(self) -> None:
        """记录生命周期退出请求。"""
        self.stopped = True


@pytest.mark.asyncio
async def test_lifespan_starts_scheduler_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scheduler 开启时必须创建后台任务，并在应用退出时停止且完成任务退出。"""
    _FakeScheduler.instances.clear()
    monkeypatch.setattr(main_module, "ScheduledTriggerScheduler", _FakeScheduler)
    monkeypatch.setattr(main_module.settings, "scheduler_enabled", True)
    monkeypatch.setattr(main_module.settings, "scheduler_poll_interval_seconds", 2.5)

    async with main_module.lifespan(main_module.app):
        scheduler = _FakeScheduler.instances[-1]
        await asyncio.wait_for(scheduler.started.wait(), timeout=1)
        assert scheduler.poll_interval_seconds == 2.5
        assert scheduler.stopped is False
        assert not main_module.app.state.scheduled_trigger_scheduler is None

    assert scheduler.stopped is True
    assert scheduler.finished.is_set() is True


@pytest.mark.asyncio
async def test_lifespan_does_not_start_scheduler_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scheduler 关闭时不得创建后台轮询任务，但应用仍应初始化 Scheduler 状态对象。"""
    _FakeScheduler.instances.clear()
    monkeypatch.setattr(main_module, "ScheduledTriggerScheduler", _FakeScheduler)
    monkeypatch.setattr(main_module.settings, "scheduler_enabled", False)

    async with main_module.lifespan(main_module.app):
        scheduler = _FakeScheduler.instances[-1]
        await asyncio.sleep(0)
        assert scheduler.started.is_set() is False
        assert main_module.app.state.scheduled_trigger_scheduler is scheduler

    assert scheduler.stopped is True
    assert scheduler.finished.is_set() is False
