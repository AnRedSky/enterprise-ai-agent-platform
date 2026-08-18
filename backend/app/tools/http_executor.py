import asyncio
import ipaddress
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.tools.exceptions import ToolExecutionError

MAX_RESPONSE_BYTES = 1_048_576
DEFAULT_TIMEOUT_SECONDS = 10


def _validate_target(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ToolExecutionError("UNSAFE_URL", "Only HTTP/HTTPS URLs are allowed")

    host = parsed.hostname
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ToolExecutionError("DNS_ERROR", "Unable to resolve target host") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved, ip.is_unspecified)):
            raise ToolExecutionError("SSRF_BLOCKED", "Target resolves to a restricted network address")

    return parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80)


def _request(url: str, method: str, headers: dict[str, str], body: bytes | None, timeout: float) -> dict:
    _validate_target(url)
    request = Request(url, data=body, headers=headers, method=method.upper())
    try:
        with urlopen(request, timeout=timeout) as response:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(64 * 1024, MAX_RESPONSE_BYTES - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ToolExecutionError("RESPONSE_TOO_LARGE", "Tool response exceeds size limit")
                chunks.append(chunk)
            return {"status_code": response.status, "headers": dict(response.headers), "body": b"".join(chunks).decode("utf-8", errors="replace")}
    except asyncio.TimeoutError as exc:
        raise ToolExecutionError("TIMEOUT", "Tool request timed out") from exc
    except TimeoutError as exc:
        raise ToolExecutionError("TIMEOUT", "Tool request timed out") from exc
    except ToolExecutionError:
        raise
    except Exception as exc:
        raise ToolExecutionError("HTTP_ERROR", "Tool HTTP request failed") from exc


async def execute_http_tool(arguments: dict, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> dict:
    url = arguments["url"]
    method = arguments.get("method", "GET")
    headers = arguments.get("headers", {})
    body = arguments.get("body")
    body_bytes = body.encode("utf-8") if isinstance(body, str) else None
    return await asyncio.to_thread(_request, url, method, headers, body_bytes, timeout)
