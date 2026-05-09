# ruff: noqa: E501,E701,E702,E402,E401,I001,B904,UP037

import json
import os
import subprocess
import sys
from pathlib import Path

from test_ai_activity_runner_api_client import FakeV2Handler, serve
from test_ai_activity_runner_llm_client import FakeLLM, serve_llm

ROOT = Path(__file__).resolve().parents[3]

def env(base_url, llm_url, tmp_path):
    e=os.environ.copy(); e.update({
        "AI_ACTIVITY_API_BASE_URL": base_url,
        "AI_ACTIVITY_OUTPUT_DIR": str(tmp_path/".hermes"/"tmp"/"ai-activity-runner"),
        "AI_ACTIVITY_LLM_BASE_URL": llm_url,
        "AI_ACTIVITY_LLM_API_KEY": "bridge_local_key_placeholder",
        "AI_ACTIVITY_AGENT_COUNT": "2",
        "AI_ACTIVITY_MAX_STEPS": "3",
        "AI_ACTIVITY_MAX_WALL_SECONDS": "20",
        "AI_ACTIVITY_RUN_ID": "run_cli_test",
    }); return e

def test_validate_config_success_and_failure(tmp_path):
    e=os.environ.copy(); e["AI_ACTIVITY_LLM_API_KEY"]="bridge_local_key_placeholder"; e["AI_ACTIVITY_OUTPUT_DIR"]=str(tmp_path/".hermes"/"tmp"/"ai-activity-runner")
    ok=subprocess.run([sys.executable,"scripts/ai_activity_runner.py","validate-config"],cwd=ROOT,text=True,capture_output=True,env=e)
    assert ok.returncode == 0 and "bridge_local_key_placeholder" not in ok.stdout
    bad=subprocess.run([sys.executable,"scripts/ai_activity_runner.py","validate-config"],cwd=ROOT,text=True,capture_output=True,env={})
    assert bad.returncode == 2 and "Traceback" not in bad.stderr

def test_llm_smoke_skips_without_opt_in():
    out=subprocess.run([sys.executable,"scripts/ai_activity_runner.py","llm-smoke"],cwd=ROOT,text=True,capture_output=True,check=True)
    assert "AI_ACTIVITY_LIVE_LLM_SMOKE=1" in out.stdout

def test_synthetic_load_fake_servers_writes_redacted_artifacts(tmp_path):
    v2,tv2,url=serve(); llm,tllm,llm_url=serve_llm(); FakeLLM.content='{"intent":"root_post","text":"Fictional used car note."}'
    try:
        run=subprocess.run([sys.executable,"scripts/ai_activity_runner.py","synthetic-load"],cwd=ROOT,text=True,capture_output=True,env=env(url,llm_url,tmp_path),timeout=30)
        assert run.returncode == 0, run.stderr
        assert "runtime_token" not in run.stdout and "bridge_local_key_placeholder" not in run.stdout
        assert "runtime_token" not in run.stderr and "bridge_local_key_placeholder" not in run.stderr
        assert "runner_started" in run.stderr and "runner_completed" in run.stderr
        payload=json.loads(run.stdout); assert payload["steps"] == 3
        run_dir=tmp_path/".hermes"/"tmp"/"ai-activity-runner"/"run_cli_test"
        assert (run_dir/"activity.jsonl").exists() and (run_dir/"summary.json").exists() and (run_dir/"agents.redacted.jsonl").exists()
        assert "runtime_token" not in (run_dir/"agents.redacted.jsonl").read_text()
        assert max(sum(1 for r in FakeV2Handler.requests if r[0] == "POST"), 0) >= 2
    finally:
        v2.shutdown(); tv2.join(timeout=2); llm.shutdown(); tllm.join(timeout=2)
