"""Resume Bootstrap tenant boundary 单元测试。"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.workflow.checkpoint.recovery.resume_bootstrap import _validate_resume_tenant_scope


def test_resume_bootstrap_requires_same_tenant() -> None:
    """Source 与 Resume 不同 tenant 时必须在复制 Durable Facts 前拒绝。"""
    with pytest.raises(ValueError, match="同一 tenant"):
        _validate_resume_tenant_scope(
            source_execution=SimpleNamespace(tenant_id=uuid4()),
            resume_execution=SimpleNamespace(tenant_id=uuid4()),
        )


def test_resume_bootstrap_accepts_same_tenant() -> None:
    """同一 tenant 的 Source 与 Resume 才允许进入 Bootstrap。"""
    tenant_id = uuid4()
    _validate_resume_tenant_scope(
        source_execution=SimpleNamespace(tenant_id=tenant_id),
        resume_execution=SimpleNamespace(tenant_id=tenant_id),
    )
