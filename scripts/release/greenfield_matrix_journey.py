"""Run the installed show, sealed proposal and explicit terminal decision journey."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
import time
from typing import Any

from greenfield_matrix_transaction_evidence import CompiledCreateExecution, commit_precompiled_transaction
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
)


def run_compiled_greenfield_journey(
    *,
    repo_root: Path,
    env: Mapping[str, str],
    repair_tier: str,
    invoke_cli: Callable[[Sequence[str], int], Any],
    invoke_propose: Callable[[int], Any],
    raw_streams: dict[str, str] | None = None,
) -> CompiledCreateExecution:
    profile_id = model_profile_id_for_repair_tier(repair_tier)
    if str(env.get("ODYLITH_GREENFIELD_MODEL_PROFILE") or "").strip() != profile_id:
        raise ValueError("release proof repair tier does not match its configured model profile")
    shown = invoke_cli(("./.odylith/bin/odylith", "show", "--repo-root", "."), 60)
    if raw_streams is not None:
        raw_streams.update({"show.stdout": shown.stdout, "show.stderr": shown.stderr})
    if shown.returncode != 0 or "Odylith read this repo" not in shown.stdout:
        raise RuntimeError("installed Greenfield journey failed its initial capability show")
    started = time.perf_counter()
    proposed = invoke_propose(int(get_greenfield_model_profile(profile_id).operational_timeout_seconds))
    proposal_seconds = round(time.perf_counter() - started, 3)
    execution = commit_precompiled_transaction(
        repo_root=repo_root, proposed=proposed, proposal_seconds=proposal_seconds,
        invoke_cli=lambda command: invoke_cli(command, 60),
    )
    if raw_streams is not None:
        raw_streams["terminal-journal.v1.json"] = execution.terminal_journal_text
        for label, result in (
            ("propose", proposed), ("decide", execution.decision),
            ("retry-decide", execution.retry_decision),
        ):
            for stream in ("stdout", "stderr"):
                raw_streams[f"{label}.{stream}"] = str(getattr(result, stream, "") or "")
    return execution
