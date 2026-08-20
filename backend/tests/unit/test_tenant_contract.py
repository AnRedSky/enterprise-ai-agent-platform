from uuid import UUID

from app.core.security import create_token, decode_token
from app.models.core import DEFAULT_TENANT_ID, Tenant, User
from app.models.workflow import Workflow


def test_access_token_contains_tenant_id():
    tenant_id = UUID("00000000-0000-0000-0000-000000000123")
    token = create_token(UUID("00000000-0000-0000-0000-000000000456"), ["user"], tenant_id=tenant_id)
    claims = decode_token(token)
    assert claims["tenant_id"] == str(tenant_id)


def test_legacy_default_tenant_contract_is_stable():
    assert DEFAULT_TENANT_ID == UUID("00000000-0000-0000-0000-000000000001")
    assert Tenant.__tablename__ == "tenants"
    assert User.__table__.c.tenant_id.nullable is False
    assert Workflow.__table__.c.tenant_id.nullable is False
