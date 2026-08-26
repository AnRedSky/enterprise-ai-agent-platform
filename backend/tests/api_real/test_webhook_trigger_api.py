"""真实 HTTP Webhook Trigger 验收：覆盖鉴权、幂等、事件身份与禁用边界。"""

import asyncio
import os
import time
import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")
TOKEN = os.getenv("ACCESS_TOKEN")
TRIGGER_WORKFLOW_ID = os.getenv("TRIGGER_WORKFLOW_ID")

pytestmark = pytest.mark.real_api


@pytest.fixture(scope="module")
def webhook_event_loop():
    """创建只由本模块主动驱动的测试事件循环，避免 pytest-asyncio 生命周期接管并提前关闭。

    返回值：
        本模块复用的独立事件循环。
    """
    loop = asyncio.new_event_loop()
    try:
        # 不把专用循环注册为当前事件循环。pytest-asyncio 可能在测试阶段管理并关闭
        # 当前循环；本模块的异步操作全部显式通过 _run_async 驱动专用循环。
        yield loop
    finally:
        if not loop.is_closed():
            loop.close()


def _run_async(loop: asyncio.AbstractEventLoop, coroutine):
    """在测试专用事件循环中执行异步数据库操作。

    参数：
        loop: 当前模块复用的测试事件循环。
        coroutine: 待执行的协程对象。

    返回值：
        协程实际返回值。
    """
    return loop.run_until_complete(coroutine)


def _client() -> httpx.Client:
    """创建带真实 API Token 的 HTTP 客户端。

    返回值：
        指向当前 Real API 地址的 HTTP 客户端。
    """
    if not TOKEN:
        pytest.fail("ACCESS_TOKEN is required for real API validation")
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=20.0,
    )


async def _execution_rows(idempotency_key: str) -> list[dict]:
    """读取真实 PostgreSQL 中指定 Webhook 幂等键的 WorkflowExecution。

    参数：
        idempotency_key: Webhook 持久化幂等键。

    返回值：
        按创建时间排序的真实 WorkflowExecution 行。
    """
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT id, status, idempotency_key, input_data "
                    "FROM workflow_executions "
                    "WHERE idempotency_key = :idempotency_key "
                    "ORDER BY created_at ASC"
                ),
                {"idempotency_key": idempotency_key},
            )
            return [dict(row._mapping) for row in result]
    finally:
        await engine.dispose()


def _wait_for_execution(loop: asyncio.AbstractEventLoop, idempotency_key: str, timeout_seconds: float = 15.0):
    """轮询真实 PostgreSQL，等待 Webhook Execution 持久化。

    参数：
        loop: 当前模块复用的测试事件循环。
        idempotency_key: 目标 Webhook 幂等键。
        timeout_seconds: 最大等待秒数。

    返回值：
        当前数据库中该幂等键对应的全部 Execution 行。
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        rows = _run_async(loop, _execution_rows(idempotency_key))
        if rows:
            return rows
        time.sleep(1.0)
    return _run_async(loop, _execution_rows(idempotency_key))


def test_webhook_trigger_real_http_accepts_duplicate_and_rejects_invalid_secret(webhook_event_loop):
    """验证真实 Webhook 鉴权、首次接收、重复事件幂等与最终 Execution。"""
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for webhook validation")

    name = f"api-real-webhook-{uuid.uuid4().hex[:8]}"
    secret = f"real-webhook-{uuid.uuid4().hex}"
    event_id = f"event-{uuid.uuid4().hex}"
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={
                "name": name,
                "trigger_type": "webhook",
                "config": {"auth_mode": "secret", "secret": secret, "event_id_field": "event_id"},
            },
        )
        assert created.status_code == 201, created.text
        trigger = created.json()
        trigger_id = trigger["id"]
        assert trigger["trigger_type"] == "webhook"
        assert trigger["status"] == "enabled"
        assert trigger["config"]["auth_mode"] == "secret"
        assert trigger["config"]["event_id_field"] == "event_id"
        assert "secret" not in trigger["config"]
        assert "secret_hash" not in trigger["config"]

        invalid = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": event_id, "source": "real-api"},
            headers={"X-Webhook-Secret": "wrong-secret"},
        )
        assert invalid.status_code == 401, invalid.text

        accepted = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": event_id, "source": "real-api"},
            headers={"X-Webhook-Secret": secret, "X-Request-ID": "webhook-real-request-1"},
        )
        assert accepted.status_code == 202, accepted.text
        accepted_body = accepted.json()
        assert accepted_body["status"] == "accepted"
        assert accepted_body["request_id"] == "webhook-real-request-1"
        durable_key = accepted_body["idempotency_key"]
        assert durable_key.startswith("webhook:")
        assert len(durable_key) <= 100

        duplicate = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": event_id, "source": "real-api"},
            headers={"X-Webhook-Secret": secret, "X-Request-ID": "webhook-real-request-2"},
        )
        assert duplicate.status_code == 200, duplicate.text
        duplicate_body = duplicate.json()
        assert duplicate_body["status"] == "duplicate"
        assert duplicate_body["execution_id"] == accepted_body["execution_id"]
        assert duplicate_body["idempotency_key"] == durable_key

        rows = _wait_for_execution(webhook_event_loop, durable_key)
        assert len(rows) == 1, rows
        assert rows[0]["idempotency_key"] == durable_key
        assert rows[0]["input_data"] == {"event_id": event_id, "source": "real-api"}
        assert rows[0]["status"] == "completed", rows

        disabled = client.patch(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}",
            json={"status": "disabled"},
        )
        assert disabled.status_code == 200, disabled.text

        rejected_disabled = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": f"disabled-{uuid.uuid4().hex}"},
            headers={"X-Webhook-Secret": secret},
        )
        assert rejected_disabled.status_code == 409, rejected_disabled.text

        deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert deleted.status_code == 204, deleted.text

        missing = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": f"deleted-{uuid.uuid4().hex}"},
            headers={"X-Webhook-Secret": secret},
        )
        assert missing.status_code == 404, missing.text


def test_webhook_trigger_real_http_requires_event_identity():
    """验证真实 Webhook 必须提供 Contract 要求的事件身份字段。"""
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for webhook validation")

    name = f"api-real-webhook-identity-{uuid.uuid4().hex[:8]}"
    secret = f"real-webhook-identity-{uuid.uuid4().hex}"
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "webhook", "config": {"auth_mode": "secret", "secret": secret, "event_id_field": "event_id"}},
        )
        assert created.status_code == 201, created.text
        trigger_id = created.json()["id"]

        missing_identity = client.post(
            f"/webhooks/{trigger_id}",
            json={"source": "real-api"},
            headers={"X-Webhook-Secret": secret},
        )
        assert missing_identity.status_code == 422, missing_identity.text

        deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert deleted.status_code == 204, deleted.text


def test_webhook_trigger_real_http_bounds_long_idempotency_key_deterministically(webhook_event_loop):
    """验证真实 Webhook 对超长事件身份生成固定长度的持久化幂等键。"""
    if not TRIGGER_WORKFLOW_ID:
        pytest.fail("TRIGGER_WORKFLOW_ID is required for webhook validation")

    name = f"api-real-webhook-long-key-{uuid.uuid4().hex[:8]}"
    secret = f"real-webhook-long-key-{uuid.uuid4().hex}"
    event_identity = "x" * 100
    trigger_id = None

    with _client() as client:
        created = client.post(
            f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers",
            json={"name": name, "trigger_type": "webhook", "config": {"auth_mode": "secret", "secret": secret, "event_id_field": "event_id"}},
        )
        assert created.status_code == 201, created.text
        trigger_id = created.json()["id"]

        first = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": event_identity, "source": "real-api"},
            headers={"X-Webhook-Secret": secret, "Idempotency-Key": event_identity},
        )
        assert first.status_code == 202, first.text
        first_body = first.json()
        durable_key = first_body["idempotency_key"]
        assert durable_key.startswith("webhook:")
        assert len(durable_key) == len("webhook:") + 64

        duplicate = client.post(
            f"/webhooks/{trigger_id}",
            json={"event_id": event_identity, "source": "real-api"},
            headers={"X-Webhook-Secret": secret, "Idempotency-Key": event_identity},
        )
        assert duplicate.status_code == 200, duplicate.text
        duplicate_body = duplicate.json()
        assert duplicate_body["status"] == "duplicate"
        assert duplicate_body["execution_id"] == first_body["execution_id"]
        assert duplicate_body["idempotency_key"] == durable_key

        rows = _wait_for_execution(webhook_event_loop, durable_key)
        assert len(rows) == 1, rows
        assert rows[0]["idempotency_key"] == durable_key
        assert rows[0]["status"] == "completed", rows

        deleted = client.delete(f"/workflows/{TRIGGER_WORKFLOW_ID}/triggers/{trigger_id}")
        assert deleted.status_code == 204, deleted.text
