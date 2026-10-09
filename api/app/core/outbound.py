"""Bounded outbound HTTP with DNS pinning, TLS SNI and no redirects/proxies."""

import ipaddress
import json
import re
import socket
import time
from urllib.parse import urlsplit

import httpx

from .config import get_settings


class OutboundError(ValueError):
    pass


def validate_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise OutboundError("Invalid destination URL") from exc
    local = host in get_settings().OUTBOUND_LOCAL_HOSTS
    if (
        not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "\\" in value
        or re.search(r"[\s\x00-\x1f\x7f]", value)
        or parsed.scheme not in ({"http", "https"} if local else {"https"})
        or port == 0
    ):
        raise OutboundError("Use an HTTPS URL without credentials, query or fragment")
    # Reject literals at submission, and check all resolved addresses at connection time.
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return value
    if not local and not addr.is_global:
        raise OutboundError("Destination must be public")
    return value


def validate_headers(headers: dict[str, str]) -> dict[str, str]:
    forbidden = {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "proxy-authorization",
        "proxy-connection",
        "upgrade",
        "te",
        "trailer",
        "content-type",
        "idempotency-key",
    }
    if len(headers) > 32:
        raise ValueError("At most 32 agent headers are allowed")
    for name, value in headers.items():
        if (
            name.lower() in forbidden
            or not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name)
            or re.search(r"[\x00-\x1f\x7f]", value)
            or len(value) > 8192
        ):
            raise ValueError("Invalid or reserved agent header")
    return headers


def post_json(url: str, *, body: bytes, headers: dict[str, str], timeout: float = 120) -> bytes:
    validate_url(url)
    target = httpx.URL(url)
    host = target.host
    try:
        addresses = socket.getaddrinfo(
            host, target.port or (443 if target.scheme == "https" else 80), type=socket.SOCK_STREAM
        )
    except OSError as exc:
        raise OutboundError("Destination DNS lookup failed") from exc
    ips = list(dict.fromkeys(row[4][0] for row in addresses))
    if not ips or (
        host not in get_settings().OUTBOUND_LOCAL_HOSTS and any(not ipaddress.ip_address(ip).is_global for ip in ips)
    ):
        raise OutboundError("Destination must resolve exclusively to public addresses")
    # Connect to the validated address, preserving the original HTTP Host and TLS SNI.
    pinned = target.copy_with(host=ips[0])
    started = time.monotonic()
    with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
        with client.stream(
            "POST",
            pinned,
            content=body,
            headers={**headers, "Host": target.netloc.decode(), "Content-Type": "application/json"},
            extensions={"sni_hostname": host},
        ) as response:
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if time.monotonic() - started > timeout:
                    raise OutboundError("Response exceeded time budget")
                if size > get_settings().MAX_RESPONSE_BYTES:
                    raise OutboundError("Response exceeds size limit")
                chunks.append(chunk)
            return b"".join(chunks)


def agent_response(url: str, headers: dict[str, str], messages: list[dict], key: str) -> dict:
    payload = json.loads(
        post_json(url, body=json.dumps({"messages": messages}).encode(), headers={**headers, "Idempotency-Key": key})
    )
    if not isinstance(payload, dict):
        raise OutboundError("Expected JSON response object")
    # Fail malformed responses rather than awarding an empty response a high score.
    extract_text(payload)
    usage = payload.get("usage", {})
    if not isinstance(usage, dict):
        raise OutboundError("Invalid usage object")
    for name in ("prompt_tokens", "completion_tokens", "input_tokens", "output_tokens"):
        value = usage.get(name)
        if value is not None and (type(value) is not int or value < 0 or value > 2_000_000_000):
            raise OutboundError("Invalid token count")
    return payload


def extract_text(payload: dict) -> str:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if content is None and isinstance(message.get("tool_calls"), list) and message["tool_calls"]:
                return ""
    content = payload.get("content")
    if isinstance(content, list) and content:
        if all(isinstance(part, dict) for part in content) and any(
            isinstance(part.get("text"), str) or part.get("type") == "tool_use" for part in content
        ):
            return "\n".join(part["text"] for part in content if isinstance(part.get("text"), str))
    raise OutboundError("Expected an OpenAI message or Anthropic content list")
