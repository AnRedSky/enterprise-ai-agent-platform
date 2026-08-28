"""Agent Delegation 超时运行时规则。

职责：计算 Delegation 剩余执行时间并区分 Delegation timeout 与 Workflow Runtime 自身 timeout。
边界：不修改数据库、不推进状态机；终态持久化由 completion 模块负责。
关键依赖：Delegation timeout_at、统一 UTC 时钟以及现有 Workflow Runtime timeout。
"""

from __future__ import annotations

from datetime import datetime


def remaining_timeout_seconds(timeout_at: datetime | None, *, now: datetime) -> float | None:
    """计算 Delegation 距离超时边界的剩余秒数。

    Args:
        timeout_at: 持久化的 Delegation 超时时刻；为空表示没有 Delegation 生命周期限制。
        now: 调用方提供的统一当前时间。

    Returns:
        float | None: 剩余秒数；已到期时返回 0；未配置超时时返回 None。
    """
    if timeout_at is None:
        return None
    return max(0.0, (timeout_at - now).total_seconds())


def effective_runtime_timeout_seconds(
    runtime_timeout_seconds: float,
    delegation_timeout_at: datetime | None,
    *,
    now: datetime,
) -> tuple[float, bool]:
    """计算本次 Worker Runtime 的最短超时边界。

    Args:
        runtime_timeout_seconds: 既有 Workflow Runtime 的执行时间上限。
        delegation_timeout_at: Delegation 自身的生命周期超时时刻。
        now: 统一当前时间，用于避免同一执行内重复读取系统时钟。

    Returns:
        tuple[float, bool]: 有效超时秒数，以及该边界是否由 Delegation timeout 主导。

    Raises:
        ValueError: Workflow Runtime timeout 小于等于 0。
    """
    if runtime_timeout_seconds <= 0:
        raise ValueError("Workflow Runtime timeout 必须大于 0")
    remaining = remaining_timeout_seconds(delegation_timeout_at, now=now)
    if remaining is None:
        return runtime_timeout_seconds, False
    if remaining <= runtime_timeout_seconds:
        return remaining, True
    return runtime_timeout_seconds, False
