import pytest

from app.tools.exceptions import ToolExecutionError
from app.tools.http_executor import _NoRedirectHandler, _validate_target


def test_redirect_handler_does_not_follow_automatically():
    assert _NoRedirectHandler().redirect_request(None, None, 302, "Found", {}, "http://example.com") is None


def test_unsafe_scheme_is_rejected():
    with pytest.raises(ToolExecutionError, match="HTTP/HTTPS"):
        _validate_target("file:///etc/passwd")
