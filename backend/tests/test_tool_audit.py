from app.services.tool_audit import sanitize_tool_metadata


def test_sensitive_tool_metadata_is_redacted():
    result = sanitize_tool_metadata({
        "Authorization": "Bearer secret",
        "api_key": "key",
        "nested": {"password": "pw", "value": "ok"},
    })
    assert result["Authorization"] == "[REDACTED]"
    assert result["api_key"] == "[REDACTED]"
    assert result["nested"]["password"] == "[REDACTED]"
    assert result["nested"]["value"] == "ok"
