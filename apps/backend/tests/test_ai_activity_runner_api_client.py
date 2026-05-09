# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class FakeV2Handler(BaseHTTPRequestHandler):
    requests=[]; signup_count=0
    def log_message(self, format, *args): return
    def _send(self, code, payload=None):
        raw=json.dumps(payload or {}).encode() if payload is not None else b""
        self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def _body(self):
        raw=self.rfile.read(int(self.headers.get("Content-Length","0"))); return json.loads(raw.decode() or "{}") if raw else {}
    def do_POST(self):
        body=self._body(); type(self).requests.append(("POST", self.path, self.headers.get("Authorization"), body))
        if self.path == "/agents/signup":
            type(self).signup_count += 1; h=body.get("handle", f"syn_fake_{type(self).signup_count}")
            return self._send(201,{"agent":{"handle":h,"display_name":body.get("display_name","Synthetic Agent"),"bio":body.get("bio","fictional")},"bearer_token":f"runtime_token_{type(self).signup_count}_not_public"})
        if self.path == "/posts": return self._send(201,{"id":"post_created", **body})
        if self.path.endswith("/like") or self.path.endswith("/repost") or self.path.endswith("/follow"): return self._send(201,{"ok": True, **body})
        return self._send(404,{"detail":"not found"})
    def do_GET(self):
        type(self).requests.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path.startswith("/timelines/public") or self.path.startswith("/timelines/home"):
            return self._send(200,{"items":[{"post":{"id":"post_1","text":"fictional civic note","author":{"handle":"other_agent"}}}]})
        if self.path == "/agents": return self._send(200,{"items":[]})
        if "/thread" in self.path: return self._send(200,{"root":{"id":"post_1"},"replies":[]})
        if self.path.startswith("/agents/"): return self._send(200,{"items":[]})
        return self._send(404,{"detail":"not found"})
    def do_DELETE(self): type(self).requests.append(("DELETE", self.path, self.headers.get("Authorization"), None)); self._send(204,None)
def serve(handler=FakeV2Handler):
    handler.requests=[]; handler.signup_count=0
    server=HTTPServer(("127.0.0.1",0),handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); return server,thread,f"http://127.0.0.1:{server.server_port}"

import uuid

import pytest
from scripts.ai_activity_runner_lib.api_client import V2APIClient
from scripts.ai_activity_runner_lib.config import ConfigError


def test_api_client_routes_auth_and_idempotency():
    server,thread,url=serve()
    try:
        c=V2APIClient(url)
        assert c.signup_agent({"handle":"syn_test","display_name":"Synthetic","bio":"fictional","persona_seed":"seed","avatar_seed":"avatar"}).ok
        assert FakeV2Handler.requests[-1][2] is None
        assert c.public_timeline().ok and FakeV2Handler.requests[-1][2] is None
        assert c.home_timeline("v2_runtime_token").ok and FakeV2Handler.requests[-1][2] == "Bearer v2_runtime_token"
        r=c.create_post("v2_runtime_token","Fictional note", agent_handle="syn_test")
        uuid.UUID(r.client_request_id); assert FakeV2Handler.requests[-1][3]["client_request_id"] == r.client_request_id
        assert c.like_post("v2_runtime_token","post_1", agent_handle="syn_test").ok
        assert c.repost("v2_runtime_token","post_1", agent_handle="syn_test").ok
        assert c.follow("v2_runtime_token","other_agent", agent_handle="syn_test").ok
        assert c.agent_posts("syn_test", tab="likes").ok
        assert c.thread("post_1").ok
    finally:
        server.shutdown(); thread.join(timeout=2)

def test_api_client_refuses_unsafe_targets_and_routes():
    with pytest.raises(ConfigError): V2APIClient("http://192.168.0.1:8001")
    c=V2APIClient("http://127.0.0.1:1")
    assert not c._request("GET","/fixtures/reset",route_class="bad").ok
    assert c.agent_posts("syn_test", tab="debug").issue_class == "api_route_forbidden"

def test_api_client_classifies_authenticated_401_as_token_rejected():
    class Rejecting(FakeV2Handler):
        def do_POST(self):
            body=self._body(); type(self).requests.append(("POST", self.path, self.headers.get("Authorization"), body))
            if self.path == "/posts": return self._send(401,{"detail":"Unauthorized"})
            return super().do_POST()
    server,thread,url=serve(Rejecting)
    try:
        result=V2APIClient(url).create_post("stale_runtime_token","Fictional gremlin note", agent_handle="syn_test")
        assert not result.ok
        assert result.status_code == 401
        assert result.issue_class == "token_rejected"
        assert "stale_runtime_token" not in result.safe_summary
    finally:
        server.shutdown(); thread.join(timeout=2)
