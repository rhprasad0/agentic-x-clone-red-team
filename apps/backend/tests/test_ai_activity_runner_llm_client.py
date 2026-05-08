# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from scripts.ai_activity_runner_lib.config import AIActivityConfig
from scripts.ai_activity_runner_lib.llm_client import LocalCodexBridgeClient, parse_action_proposal


class FakeLLM(BaseHTTPRequestHandler):
    requests=[]; content='{"intent":"silence"}'
    def log_message(self, format, *args): return
    def do_POST(self):
        body=self.rfile.read(int(self.headers.get("Content-Length","0")))
        type(self).requests.append({"path":self.path,"authorization":self.headers.get("Authorization"),"body":json.loads(body.decode())})
        raw=json.dumps({"choices":[{"message":{"content":type(self).content}}]}).encode()
        self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
def serve_llm():
    FakeLLM.requests=[]; FakeLLM.content='{"intent":"silence"}'
    s=HTTPServer(("127.0.0.1",0),FakeLLM); t=threading.Thread(target=s.serve_forever,daemon=True); t.start(); return s,t,f"http://127.0.0.1:{s.server_port}/v1"
def cfg(url): return AIActivityConfig(llm_base_url=url,llm_api_key="bridge_local_key_placeholder")

def test_llm_client_openai_request_and_auth_isolated():
    s,t,url=serve_llm()
    try:
        c=LocalCodexBridgeClient(cfg(url)); assert c.complete([{"role":"user","content":"safe"}]) == '{"intent":"silence"}'
        req=FakeLLM.requests[0]
        assert req["path"] == "/v1/chat/completions" and req["authorization"] == "Bearer bridge_local_key_placeholder"
        assert req["body"]["model"] == "gpt-5.4-mini"
        assert "v2_runtime_token" not in json.dumps(req)
    finally: s.shutdown(); t.join(timeout=2)

def test_parse_structured_action_errors_and_safety():
    assert parse_action_proposal("not json").issue_class == "llm_malformed_json"
    assert parse_action_proposal('{"intent":"raw_route"}').issue_class == "llm_unsupported_intent"
    assert parse_action_proposal('{"intent":"root_post","text":"email me at person@example.net"}').issue_class == "safety_redaction_applied"
    p=parse_action_proposal('{"intent":"root_post","text":"Fictional sedan note","reason":"safe"}')
    assert p.intent == "root_post" and p.text == "Fictional sedan note"

def test_propose_action_includes_spicy_style_guidance_without_key():
    s, t, url = serve_llm()
    try:
        c = LocalCodexBridgeClient(cfg(url))
        c.propose_action(persona="Fictional gremlin", context={"style_pack": "auction_lot_cryptids"}, action_options=["silence"])
        messages = FakeLLM.requests[0]["body"]["messages"]
        blob = json.dumps(messages)
        assert "auction_lot_cryptids" in blob
        assert "Silliness=1.00" in blob
        assert "do not dogpile" in blob
        assert "bridge_local_key_placeholder" not in blob
    finally:
        s.shutdown(); t.join(timeout=2)
