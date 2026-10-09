import socket

import httpx
import pytest

from app.core.config import get_settings
from app.core.outbound import OutboundError, agent_response, post_json, validate_headers, validate_url


@pytest.mark.parametrize("url", ["http://public.example/run", "https://127.0.0.1/run", "https://[::1]/",
    "https://169.254.169.254/metadata", "https://user:secret@public.example/", "https://public.example/?key=secret",
    "https://public.example/#fragment", "file:///etc/passwd", "https://public.example:0", "https://public.example/\n"])
def test_invalid_destinations(url):
    with pytest.raises(OutboundError):
        validate_url(url)


def test_dns_checks_every_address_and_pins_public_ip(monkeypatch, httpx_mock):
    addresses = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in ["93.184.215.14", "10.0.0.1"]]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: addresses)
    with pytest.raises(OutboundError):
        post_json("https://agent.example/run", body=b"{}", headers={})
    addresses.pop()
    httpx_mock.add_response(url="https://93.184.215.14/run", content=b"{}")
    assert post_json("https://agent.example/run", body=b"{}", headers={}) == b"{}"
    request = httpx_mock.get_request()
    assert request.headers["Host"] == "agent.example"
    assert request.extensions["sni_hostname"] == "agent.example"


def test_private_host_requires_exact_operator_allowlist(monkeypatch, httpx_mock):
    monkeypatch.setattr(get_settings(), "OUTBOUND_LOCAL_HOSTS", ["mock-agent"])
    assert validate_url("http://mock-agent:8080/run")
    with pytest.raises(OutboundError):
        validate_url("http://mock-agent.evil.example/run")
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("127.0.0.1", 8080))])
    httpx_mock.add_response(url="http://127.0.0.1:8080/run", content=b"{}")
    post_json("http://mock-agent:8080/run", body=b"{}", headers={})
    assert httpx_mock.get_request().headers["Host"] == "mock-agent:8080"


@pytest.mark.parametrize("headers", [{"Host": "internal"}, {"X-Key": "one\r\ntwo"}, {"Connection": "close"},
                                     {"Idempotency-Key": "override"}, {"Content-Length": "0"}])
def test_headers_cannot_override_transport(headers):
    with pytest.raises(ValueError):
        validate_headers(headers)


def test_redirects_and_oversized_responses_are_rejected(monkeypatch, httpx_mock):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **kw: [(2, 1, 6, "", ("93.184.215.14", 443))])
    httpx_mock.add_response(status_code=302, headers={"Location": "http://127.0.0.1/"})
    with pytest.raises(httpx.HTTPStatusError):
        post_json("https://agent.example/", body=b"{}", headers={})
    monkeypatch.setattr(get_settings(), "MAX_RESPONSE_BYTES", 5)
    httpx_mock.add_response(content=b"0123456")
    with pytest.raises(OutboundError):
        post_json("https://agent.example/", body=b"{}", headers={})
    assert len(httpx_mock.get_requests()) == 2


@pytest.mark.parametrize("payload", [[], {}, {"choices": []}, {"choices": [{"message": {"content": 42}}]},
    {"choices": [{"message": {"content": "valid"}}], "usage": {"prompt_tokens": -1}}])
def test_malformed_agent_payloads_fail(monkeypatch, payload):
    import json
    monkeypatch.setattr("app.core.outbound.post_json", lambda *a, **kw: json.dumps(payload).encode())
    with pytest.raises(OutboundError):
        agent_response("https://agent.example", {}, [], "test-key")


@pytest.mark.asyncio
async def test_admin_protected_and_keys_cannot_escalate(client, auth):
    assert (await client.post("/v1/admin/seed-corpus")).status_code == 403
    assert (await client.post("/v1/admin/seed-corpus", headers=auth)).status_code == 403
    assert (await client.get("/v1/accounts/me", headers=auth)).json()["email"] == "owner@example.com"
    limited = await client.post("/v1/keys", headers=auth, json={"scopes": ["run:read"], "rate_limit_rpm": 10})
    assert limited.status_code == 201
    child_auth = {"Authorization": f"Bearer {limited.json()['raw_key']}"}
    assert (await client.post("/v1/keys", headers=child_auth, json={})).status_code == 403
    revoked = await client.delete(f"/v1/keys/{limited.json()['id']}", headers=auth)
    assert revoked.status_code == 204
    assert (await client.get("/v1/runs", headers=child_auth)).status_code == 403


@pytest.mark.asyncio
async def test_health_fails_closed_without_error_details(client, monkeypatch):
    class Broken:
        async def ping(self):
            raise RuntimeError("private credentials")
    monkeypatch.setattr("app.api.v1.health.get_redis", Broken)
    res = await client.get("/v1/health")
    assert res.status_code == 503 and "credentials" not in res.text
