import pytest

from app.tools.exceptions import ToolExecutionError
from app.tools import http_executor


def test_redirect_to_restricted_target_is_revalidated(monkeypatch):
    calls = []

    def validate(url):
        calls.append(url)
        if "127.0.0.1" in url:
            raise ToolExecutionError("SSRF_BLOCKED", "restricted")
        return "public.example.test", 443

    class Response:
        status = 302
        headers = {"Location": "http://127.0.0.1/internal"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *_):
            raise AssertionError("redirect response should not be read as a body")

    class Opener:
        def open(self, *_args, **_kwargs):
            from urllib.error import HTTPError
            from io import BytesIO

            raise HTTPError("https://public.example.test", 302, "redirect", self.headers, BytesIO())

        headers = {"Location": "http://127.0.0.1/internal"}

    monkeypatch.setattr(http_executor, "_validate_target", validate)
    monkeypatch.setattr(http_executor, "_opener", Opener())

    with pytest.raises(ToolExecutionError, match="restricted"):
        http_executor._request("https://public.example.test", "GET", {}, None, 1)
    assert calls == ["https://public.example.test", "http://127.0.0.1/internal"]


def test_redirect_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(http_executor, "_validate_target", lambda url: ("public.example.test", 443))

    class Opener:
        def open(self, *_args, **_kwargs):
            from urllib.error import HTTPError
            from io import BytesIO

            raise HTTPError("https://public.example.test", 302, "redirect", {"Location": "https://public.example.test/next"}, BytesIO())

    monkeypatch.setattr(http_executor, "_opener", Opener())

    with pytest.raises(ToolExecutionError, match="limit"):
        http_executor._request("https://public.example.test", "GET", {}, None, 1)
