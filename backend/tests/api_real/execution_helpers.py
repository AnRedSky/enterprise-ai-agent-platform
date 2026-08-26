"""Real API Execution 触发与 Worker 竞争观察测试辅助函数。

职责：统一处理独立 Worker 与 HTTP `/run` 请求之间的合法 pending 抢占竞态，并允许调用方声明业务层可接受的多个 HTTP 结果。
边界：只观察真实 HTTP / PostgreSQL 持久化结果，不改变生产 Execution 状态机，也不自动控制服务进程。
"""

from __future__ import annotations

import time
from typing import Any

import httpx


_PENDING_RUN_CONFLICT = "只有 pending Execution 可以 Run"
_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}


def run_or_observe_execution(
    client: httpx.Client,
    execution_id: str,
    *,
    expected_http_status: int | tuple[int, ...] = 200,
    timeout_seconds: float = 20.0,
) -> tuple[int, dict[str, Any]]:
    """通过真实 HTTP `/run` 触发 Execution，并兼容 Worker 抢占与显式业务失败结果。

    Args:
        client: 已完成认证的真实 HTTP 客户端。
        execution_id: 待执行的 Workflow Execution ID。
        expected_http_status: 允许直接返回的 HTTP 状态码；并发业务边界可以声明多个合法结果。
        timeout_seconds: Worker 已抢占或业务失败异步落库时等待真实 Execution 进入终态的最长时间。

    Returns:
        二元组 `(run_http_status, persisted_execution)`；成功返回时直接使用 HTTP 响应对象，
        对预期的 4xx/5xx 业务结果则重新读取 PostgreSQL 对应的持久化 Execution，保证调用方
        永远拿到统一的 Execution 数据结构而不是 `{"detail": ...}` 错误响应。

    Raises:
        AssertionError: `/run` 返回非预期 HTTP 状态、409 原因不是合法 pending 抢占，
            或 Worker/Runtime 未在规定时间内写入终态。

    并发边界：独立 Worker 可以在创建 `pending` Execution 后先于手动 `/run` 请求
    claim。这里不把该 409 改写成生产成功，也不允许重复执行；测试只等待真实 Worker
    完成并验证 PostgreSQL 持久化终态。业务边界若本身允许 4xx/5xx，应通过
    `expected_http_status=(...)` 显式声明，而不是在辅助函数内部吞掉状态码。
    """
    response = client.post(f"/workflows/executions/{execution_id}/run")
    allowed_statuses = (
        (expected_http_status,)
        if isinstance(expected_http_status, int)
        else expected_http_status
    )
    if response.status_code in allowed_statuses:
        if 200 <= response.status_code < 300:
            return response.status_code, response.json()

        deadline = time.monotonic() + timeout_seconds
        last_payload: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            persisted = client.get(f"/workflows/executions/{execution_id}")
            assert persisted.status_code == 200, persisted.text
            last_payload = persisted.json()
            if last_payload.get("status") in _TERMINAL_STATUSES:
                return response.status_code, last_payload
            time.sleep(0.1)
        raise AssertionError(
            f"Expected HTTP {response.status_code} but Execution did not reach a terminal state "
            f"within {timeout_seconds}s: {last_payload}"
        )

    if response.status_code != 409 or response.json().get("detail") != _PENDING_RUN_CONFLICT:
        raise AssertionError(
            f"POST /workflows/executions/{execution_id}/run -> expected HTTP "
            f"{allowed_statuses} or legal Worker claim race, got {response.status_code}: {response.text}"
        )

    deadline = time.monotonic() + timeout_seconds
    last_payload = None
    while time.monotonic() < deadline:
        persisted = client.get(f"/workflows/executions/{execution_id}")
        assert persisted.status_code == 200, persisted.text
        last_payload = persisted.json()
        if last_payload.get("status") in _TERMINAL_STATUSES:
            return response.status_code, last_payload
        time.sleep(0.1)

    raise AssertionError(
        f"Worker claim race did not reach a terminal Execution state within {timeout_seconds}s: {last_payload}"
    )
