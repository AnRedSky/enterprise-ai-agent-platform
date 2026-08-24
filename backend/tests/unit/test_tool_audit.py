"""Tool 审计适配器单元测试。

职责：验证 Tool 审计元数据的敏感字段脱敏规则。
边界：不测试数据库写入与 API 行为。
"""

from app.services.tool import sanitize_tool_metadata


def test_sensitive_tool_metadata_is_redacted():
    result = sanitize_tool_metadata({
        "Authorization": "Bearer secret",
        "api_key": "key",
        "nested": {"password": "pw", "value": "ok"},
    })
    assert result["Authorization"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["nested"]["password"] == "[REDACTED]"
