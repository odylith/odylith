#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
ledger_path="${repo_root}/.odylith/runtime/odylith-benchmarks/in-progress.v1.json"
log_path="${ODYLITH_BENCHMARK_LOG_PATH:-/tmp/odylith-proof-gpt54-medium.log}"
interval_seconds="${ODYLITH_BENCHMARK_WATCH_INTERVAL_SECONDS:-5}"
once=0

while (($# > 0)); do
  case "$1" in
    --once)
      once=1
      shift
      ;;
    --repo-root)
      repo_root="$2"
      ledger_path="${repo_root}/.odylith/runtime/odylith-benchmarks/in-progress.v1.json"
      shift 2
      ;;
    --log-path)
      log_path="$2"
      shift 2
      ;;
    --interval)
      interval_seconds="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--once] [--repo-root PATH] [--log-path PATH] [--interval SECONDS]" >&2
      exit 2
      ;;
  esac
done

render() {
  if [[ -t 1 ]]; then
    clear
  fi

  date
  echo "repo_root: ${repo_root}"
  echo "ledger: ${ledger_path}"
  echo "log_path: ${log_path}"
  echo

  python - <<'PY' "${ledger_path}" "${log_path}"
import json
import os
import sys
from pathlib import Path

ledger_path = Path(sys.argv[1])
log_path = Path(sys.argv[2])

if not ledger_path.exists():
    print("No in-progress benchmark ledger found.")
else:
    try:
        obj = json.loads(ledger_path.read_text())
    except Exception as exc:  # pragma: no cover - shell helper
        print(f"Failed to parse ledger: {exc}")
    else:
        for key in (
            "report_id",
            "status",
            "phase",
            "completed_results",
            "total_results",
            "current_cache_profile",
            "current_scenario_id",
            "current_mode",
            "updated_utc",
            "error",
        ):
            print(f"{key}: {obj.get(key)}")

print()
if log_path.exists():
    print(f"log_exists: yes ({log_path.stat().st_size} bytes)")
else:
    print("log_exists: no")
PY

  echo
  echo "active benchmark children:"
  ps -axo pid,etime,command | rg 'codex exec .*odylith-benchmark|odylith benchmark --repo-root .* --profile proof|caffeinate -dimsu bash -lc' || echo "none"
  echo "-----"
}

while true; do
  render
  if [[ "${once}" == "1" ]]; then
    break
  fi
  sleep "${interval_seconds}"
done
