#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ENV_FILE="${AI_ACTIVITY_CRON_ENV_FILE:-.hermes/private/ai-activity-runner.env}"
PRE_LOCK_FILE="${AI_ACTIVITY_CRON_LOCK_FILE:-}"
PRE_LOG_FILE="${AI_ACTIVITY_CRON_LOG_FILE:-}"
PRE_PYTHON_BIN="${AI_ACTIVITY_CRON_PYTHON:-}"
PRE_RUNNER_CMD="${AI_ACTIVITY_CRON_RUNNER_CMD:-}"
PRE_TIMEOUT_SECONDS="${AI_ACTIVITY_CRON_TIMEOUT_SECONDS:-}"
DEFAULT_LOCK_FILE=".hermes/tmp/ai-activity-runner/cron.lock"
DEFAULT_LOG_FILE=".hermes/tmp/ai-activity-runner/logs/cron.log"
DEFAULT_PYTHON_BIN="python3"
DEFAULT_RUNNER_CMD="scripts/ai_activity_runner.py"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "AI activity cron env file missing: ${ENV_FILE}" >&2
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

LOCK_FILE="${PRE_LOCK_FILE:-${AI_ACTIVITY_CRON_LOCK_FILE:-${DEFAULT_LOCK_FILE}}}"
LOG_FILE="${PRE_LOG_FILE:-${AI_ACTIVITY_CRON_LOG_FILE:-${DEFAULT_LOG_FILE}}}"
PYTHON_BIN="${PRE_PYTHON_BIN:-${AI_ACTIVITY_CRON_PYTHON:-${DEFAULT_PYTHON_BIN}}}"
RUNNER_CMD="${PRE_RUNNER_CMD:-${AI_ACTIVITY_CRON_RUNNER_CMD:-${DEFAULT_RUNNER_CMD}}}"
TIMEOUT_SECONDS="${PRE_TIMEOUT_SECONDS:-${AI_ACTIVITY_CRON_TIMEOUT_SECONDS:-}}"

mkdir -p "$(dirname "${LOCK_FILE}")" "$(dirname "${LOG_FILE}")"

if [[ -z "${TIMEOUT_SECONDS}" ]]; then
  TIMEOUT_SECONDS="$(( ${AI_ACTIVITY_MAX_WALL_SECONDS:-480} + 60 ))"
fi

exec flock -n "${LOCK_FILE}" timeout "${TIMEOUT_SECONDS}" bash -ec '
  "$1" "$2" validate-config
  "$1" "$2" synthetic-load
' _ "${PYTHON_BIN}" "${RUNNER_CMD}" >> "${LOG_FILE}" 2>&1
