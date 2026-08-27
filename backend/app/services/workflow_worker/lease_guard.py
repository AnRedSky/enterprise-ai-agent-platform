"""Workflow Worker 租约失效控制。

职责：把 Worker 租约 heartbeat 的 ownership 结果转换为可取消的 Runtime 控制信号，
避免旧 Worker 在失去 lease 后继续执行 Runtime 或发起后续 Provider 调用。
边界：不负责 PostgreSQL lease 刷新本身，也不负责 WorkflowExecution 状态机；调用方提供
已经具备 ownership fencing 的租约刷新函数。
关键外部依赖：asyncio，以及调用方提供的异步 lease refresh 回调。
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


LeaseRenewCallback = Callable[[], Awaitable[bool]]


class WorkflowWorkerLeaseLost(RuntimeError):
    """表示 Worker 在 Runtime 执行期间已经失去 Execution ownership。"""


class WorkflowWorkerLeaseGuard:
    """监督 Runtime 与 Worker lease 生命周期，并在 ownership 丢失后主动中止 Runtime。"""

    def __init__(
        self,
        renew_lease: LeaseRenewCallback,
        interval_seconds: float,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds 必须大于 0")
        self.renew_lease = renew_lease
        self.interval_seconds = interval_seconds

    async def run(self, runtime: Awaitable[object]) -> object:
        """在租约监督下运行 Runtime，ownership 丢失后立即取消 Runtime。

        Args:
            runtime: 已创建或可创建 Task 的 Runtime 协程。

        Returns:
            Runtime 正常完成时返回其结果。

        Raises:
            WorkflowWorkerLeaseLost: heartbeat 明确返回不再拥有 Execution 时抛出。

        事务边界：本类不直接操作数据库；`renew_lease` 必须自行完成原子 ownership fencing。
        设计意图：租约丢失必须成为 Runtime 的主动取消信号，而不是等待下一次状态转换才发现 409。
        heartbeat 的瞬时异常不会立即取消 Runtime，因为短暂数据库故障不能等同于 ownership 已被其他 Worker 接管。
        """
        runtime_task = asyncio.ensure_future(runtime)
        lease_task = asyncio.create_task(self._monitor_lease())
        try:
            done, _ = await asyncio.wait(
                {runtime_task, lease_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if runtime_task in done:
                lease_task.cancel()
                try:
                    await lease_task
                except asyncio.CancelledError:
                    pass
                return runtime_task.result()

            try:
                await lease_task
            except WorkflowWorkerLeaseLost:
                runtime_task.cancel()
                try:
                    await runtime_task
                except asyncio.CancelledError:
                    pass
                raise
            except asyncio.CancelledError:
                runtime_task.cancel()
                try:
                    await runtime_task
                except asyncio.CancelledError:
                    pass
                raise
            raise RuntimeError("租约监督任务异常结束")
        finally:
            if not runtime_task.done():
                runtime_task.cancel()
                try:
                    await runtime_task
                except asyncio.CancelledError:
                    pass
            if not lease_task.done():
                lease_task.cancel()
                try:
                    await lease_task
                except asyncio.CancelledError:
                    pass

    async def _monitor_lease(self) -> None:
        """持续执行 lease refresh，并将明确的 ownership 丢失转换为取消信号。

        Args:
            无。

        Returns:
            无；持续监督直到 lease 丢失或任务被取消。

        事务边界：每次 refresh 由调用方独立完成短事务；数据库瞬时异常继续下一轮。
        """
        while True:
            try:
                owned = await self.renew_lease()
            except asyncio.CancelledError:
                raise
            except Exception:
                # 瞬时数据库故障不能直接判定 lease 已被其他 Worker 接管。
                await asyncio.sleep(self.interval_seconds)
                continue
            if not owned:
                raise WorkflowWorkerLeaseLost("Workflow Worker 已失去 Execution ownership")
            await asyncio.sleep(self.interval_seconds)
