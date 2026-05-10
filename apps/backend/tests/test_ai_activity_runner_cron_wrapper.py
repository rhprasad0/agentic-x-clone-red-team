from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER = REPO_ROOT / "scripts" / "run_ai_activity_cron.sh"


def _write_fake_runner(path: Path, *, fail_validate: bool = False, marker: str = "") -> None:
    fail_check = " and command == 'validate-config'" if fail_validate else " and False"
    marker_line = f"print({marker!r})" if marker else ""
    path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from __future__ import annotations",
                "import os",
                "import sys",
                "calls_file = os.environ['FAKE_RUNNER_CALLS_FILE']",
                "command = sys.argv[1] if len(sys.argv) > 1 else ''",
                "with open(calls_file, 'a', encoding='utf-8') as handle:",
                "    handle.write(command + '\\n')",
                marker_line,
                f"if {fail_validate!r}{fail_check}:",
                "    raise SystemExit(2)",
                "raise SystemExit(0)",
            ]
        )
        + "\n"
    )
    path.chmod(0o755)


def _base_env(tmp_path: Path, fake_runner: Path, calls_file: Path) -> dict[str, str]:
    env_file = tmp_path / "runner.env"
    env_file.write_text(
        "\n".join(
            [
                "AI_ACTIVITY_MAX_WALL_SECONDS=1",
                f"FAKE_RUNNER_CALLS_FILE={calls_file}",
            ]
        )
        + "\n"
    )
    env = os.environ.copy()
    env.update(
        {
            "AI_ACTIVITY_CRON_ENV_FILE": str(env_file),
            "AI_ACTIVITY_CRON_PYTHON": sys.executable,
            "AI_ACTIVITY_CRON_RUNNER_CMD": str(fake_runner),
            "AI_ACTIVITY_CRON_LOCK_FILE": str(tmp_path / "cron.lock"),
            "AI_ACTIVITY_CRON_LOG_FILE": str(tmp_path / "logs" / "cron.log"),
            "AI_ACTIVITY_CRON_TIMEOUT_SECONDS": "5",
        }
    )
    return env


def _run_wrapper(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(WRAPPER)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cron_wrapper_requires_env_file(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["AI_ACTIVITY_CRON_ENV_FILE"] = str(tmp_path / "missing.env")

    completed = _run_wrapper(env)

    assert completed.returncode == 2
    assert "AI activity cron env file missing" in completed.stderr
    assert completed.stdout == ""


def test_cron_wrapper_runs_validate_before_synthetic_load(tmp_path: Path) -> None:
    fake_runner = tmp_path / "fake_runner.py"
    calls_file = tmp_path / "calls.txt"
    _write_fake_runner(fake_runner)

    completed = _run_wrapper(_base_env(tmp_path, fake_runner, calls_file))

    assert completed.returncode == 0, completed.stderr
    assert calls_file.read_text().splitlines() == ["validate-config", "synthetic-load"]


def test_cron_wrapper_writes_to_log_not_stdout(tmp_path: Path) -> None:
    fake_runner = tmp_path / "fake_runner.py"
    calls_file = tmp_path / "calls.txt"
    _write_fake_runner(fake_runner, marker="cron-wrapper-test-marker")
    env = _base_env(tmp_path, fake_runner, calls_file)

    completed = _run_wrapper(env)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == ""
    assert "cron-wrapper-test-marker" in Path(env["AI_ACTIVITY_CRON_LOG_FILE"]).read_text()


def test_cron_wrapper_shell_overrides_beat_env_file_values(tmp_path: Path) -> None:
    fake_runner = tmp_path / "fake_runner.py"
    calls_file = tmp_path / "calls.txt"
    env_file_log = tmp_path / "env-file.log"
    shell_log = tmp_path / "shell.log"
    _write_fake_runner(fake_runner, marker="override-marker")
    env = _base_env(tmp_path, fake_runner, calls_file)
    env_file = Path(env["AI_ACTIVITY_CRON_ENV_FILE"])
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write(f"AI_ACTIVITY_CRON_LOG_FILE={env_file_log}\n")
    env["AI_ACTIVITY_CRON_LOG_FILE"] = str(shell_log)

    completed = _run_wrapper(env)

    assert completed.returncode == 0, completed.stderr
    assert "override-marker" in shell_log.read_text()
    assert not env_file_log.exists()


def test_cron_wrapper_skips_when_lock_is_held(tmp_path: Path) -> None:
    fake_runner = tmp_path / "fake_runner.py"
    calls_file = tmp_path / "calls.txt"
    _write_fake_runner(fake_runner)
    env = _base_env(tmp_path, fake_runner, calls_file)
    lock_file = Path(env["AI_ACTIVITY_CRON_LOCK_FILE"])

    holder = subprocess.Popen(["flock", "-x", str(lock_file), "-c", "sleep 5"])
    try:
        time.sleep(0.2)
        completed = _run_wrapper(env)
    finally:
        holder.terminate()
        holder.wait(timeout=5)

    assert completed.returncode == 1
    assert not calls_file.exists()


def test_cron_wrapper_skips_synthetic_load_when_validate_config_fails(tmp_path: Path) -> None:
    fake_runner = tmp_path / "fake_runner.py"
    calls_file = tmp_path / "calls.txt"
    _write_fake_runner(fake_runner, fail_validate=True)

    completed = _run_wrapper(_base_env(tmp_path, fake_runner, calls_file))

    assert completed.returncode != 0
    assert calls_file.read_text().splitlines() == ["validate-config"]
