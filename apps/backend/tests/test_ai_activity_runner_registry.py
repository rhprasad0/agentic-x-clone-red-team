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

import re

import pytest
from scripts.ai_activity_runner_lib.agent_registry import AgentRegistry
from scripts.ai_activity_runner_lib.api_client import V2APIClient


def test_registry_signs_up_twenty_and_redacts_tokens():
    server,thread,url=serve()
    try:
        reg=AgentRegistry(V2APIClient(url), run_id="run_publicsafe", count=20)
        agents=reg.signup_all()
        assert len(agents) == 20 and len(reg.vault) == 20
        assert FakeV2Handler.signup_count == 20
        seen=set()
        for a in agents:
            assert re.match(r"^[a-z0-9]+(?:_[a-z0-9]+)*$", a.handle)
            assert 3 <= len(a.handle) <= 24 and a.handle not in seen
            seen.add(a.handle)
            assert "runtime_token" not in str(a.redacted_summary())
            assert not a.credential_ref.startswith(a.handle)
    finally:
        server.shutdown(); thread.join(timeout=2)

def test_registry_aborts_when_signup_falls_short():
    class Failing(FakeV2Handler):
        def do_POST(self):
            if self.path == "/agents/signup" and type(self).signup_count >= 1: return self._send(429,{"detail":"rate limited"})
            return super().do_POST()
    server,thread,url=serve(Failing)
    try:
        reg=AgentRegistry(V2APIClient(url), run_id="run_x", count=2)
        with pytest.raises(RuntimeError): reg.signup_all()
        assert any(i["issue_class"] == "signup_failed" for i in reg.issues)
    finally:
        server.shutdown(); thread.join(timeout=2)
