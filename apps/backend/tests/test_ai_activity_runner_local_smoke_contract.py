# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]

def test_fake_llm_server_contract_and_live_smoke_opt_in_gate():
    skipped=subprocess.run([sys.executable,"scripts/ai_activity_runner.py","llm-smoke"],cwd=ROOT,text=True,capture_output=True,check=True)
    assert "Skipped live LLM smoke" in skipped.stdout
    proc=subprocess.Popen([sys.executable,"scripts/fake_openai_compatible_llm.py","--host","127.0.0.1","--port","4019"],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        line=proc.stdout.readline().strip(); assert json.loads(line)["endpoint"] == "http://127.0.0.1:4019/v1"
        env=os.environ.copy(); env.update({"AI_ACTIVITY_LIVE_LLM_SMOKE":"1","AI_ACTIVITY_LLM_BASE_URL":"http://127.0.0.1:4019/v1","AI_ACTIVITY_LLM_API_KEY":"placeholder_bridge_key"})
        live=subprocess.run([sys.executable,"scripts/ai_activity_runner.py","llm-smoke"],cwd=ROOT,text=True,capture_output=True,env=env,timeout=10)
        assert live.returncode == 0 and "placeholder_bridge_key" not in live.stdout
    finally:
        proc.terminate(); proc.wait(timeout=5)
