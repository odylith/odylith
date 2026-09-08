"""Read the actual dashboard after SIGKILL, before any publication recovery."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from tests.integration.runtime.surface_browser_test_support import _assert_clean_page, _browser, _new_page, _static_server
from tests.unit.runtime.test_greenfield_commit_journal import _kill_commit_child


SOURCE = Path(__file__).resolve().parents[3]
SURFACES = {"atlas": "odylith/atlas/atlas.html", "radar": "odylith/radar/radar.html"}
MARKER = '<aside id="publication-proof" style="position:fixed;bottom:12px;left:12px;z-index:999999;background:white;color:black;border:2px solid black;padding:12px">BASELINE</aside>'


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_hashes(root):
    return {str(path.relative_to(root)): _hash(path) for path in root.rglob("*") if path.is_file()}


def _copy_frontend(source, destination):
    """Reuse the disclosed actual-shell counterexample's bounded asset selection."""
    hashes = {}
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix not in {".html", ".js", ".css", ".svg", ".png", ".woff", ".woff2", ".json"}:
            continue
        relative = path.relative_to(source)
        if any(part in {"source", "bugs", "skills", "technical-plans", "agents-guidelines"} for part in relative.parts) and path.suffix not in {".svg", ".png"}:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        hashes[str(relative)] = _hash(path)
    return hashes


def _protected_dashboard(tmp_path):
    root, stage = tmp_path / "repo", tmp_path / "stage"
    source_hashes = _copy_frontend(SOURCE / "odylith", root / "odylith")
    for relative in SURFACES.values():
        path = root / relative
        html = path.read_text(encoding="utf-8")
        assert "</body>" in html and 'id="publication-proof"' not in html
        atomic_write_text(path, html.replace("</body>", MARKER + "</body>"))
    baseline = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=root)
    manifest = store.compile_greenfield_generation_manifest(baseline)
    entry = state.compile_greenfield_publication_entry(
        write_set_hash=baseline["write_set_hash"],
        generation_manifest_sha256=hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
    )
    generation = store.materialize_immutable_greenfield_generation(repo_root=root, write_set=baseline, manifest_text=manifest)
    store.publish_greenfield_generation(repo_root=root, generation=generation, write_set=baseline, publication_entry_text=entry)
    atomic_write_text(root / "odylith/tooling-shell.html", (generation.repository_root / "odylith/index.html").read_text(encoding="utf-8"))
    # This is a protected baseline setup, not proof of first activation through CONFIRM.
    shutil.copytree(generation.repository_root / "odylith", stage / "odylith", copy_function=os.link)
    for relative in SURFACES.values():
        path = stage / relative
        atomic_write_text(path, path.read_text(encoding="utf-8").replace(
            ">BASELINE</aside>", ">SEALED NEXT</aside>",
        ))
        assert ">BASELINE</aside>" in (generation.repository_root / relative).read_text(encoding="utf-8")
    transition = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=stage)
    assert transition["write_count"] == 2
    assert {row["path"] for row in transition["writes"]} == set(SURFACES.values())
    return root, generation, transition, source_hashes


def _observe_dashboard(root, evidence, phase, expected_hash, expected_marker):
    observations = []
    try:
        with _static_server(root=root) as base_url:
            for _pw, browser in _browser():
                for width in (1440, 430):
                    context = browser.new_context(viewport={"width": width, "height": 1000})
                    try:
                        page, *errors = _new_page(context)
                        requested = []
                        page.on("request", lambda request: requested.append(request.url))
                        row = {"width": width, "phase": phase, "surfaces": {}}
                        observations.append(row)
                        for surface, relative in SURFACES.items():
                            page.goto(base_url + "/odylith/index.html?tab=" + surface, wait_until="networkidle")
                            frame = page.frame_locator("#frame-" + surface)
                            marker = frame.locator("#publication-proof")
                            marker.wait_for(state="visible", timeout=15000)
                            if surface == "atlas":
                                frame.locator("#diagramId").wait_for()
                                page.wait_for_function("""() => {
                                    const image = document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
                                    return image && image.complete && image.naturalWidth > 0;
                                }""", timeout=15000)
                            else:
                                frame.locator("#list button[data-idea-id]").first.wait_for(timeout=15000)
                            row["surfaces"][surface] = {"marker": marker.inner_text(), "shell_url": page.url,
                                "child_url": page.locator("#frame-" + surface).evaluate("node => node.contentWindow.location.href")}
                            page.screenshot(path=str(evidence / f"{phase}-{width}-{surface}.png"))
                            expected_prefix = "/.odylith/runtime/greenfield/generations/" + expected_hash + "/repository/"
                            assert expected_prefix + "odylith/index.html" in page.url
                            assert expected_prefix + relative in row["surfaces"][surface]["child_url"]
                            assert row["surfaces"][surface]["marker"] == expected_marker
                        row["requests"] = requested
                        row["errors"] = errors
                        assert not any(
                            "/generations/" in url and expected_hash not in url for url in requested
                        ), requested
                        _assert_clean_page(page, *errors)
                    finally:
                        context.close()
    finally:
        (evidence / f"{phase}-observations.json").write_text(json.dumps(observations, indent=2) + "\n", encoding="utf-8")
    return observations


def test_actual_dashboard_remains_one_generation_after_killed_writer_before_recovery(tmp_path):
    evidence = Path(os.environ.get("ODYLITH_PUBLICATION_CRASH_EVIDENCE", str(tmp_path / "evidence")))
    evidence.mkdir(parents=True, exist_ok=False)
    root, baseline, write_set, source_hashes = _protected_dashboard(tmp_path)
    (evidence / "source-assets.json").write_text(json.dumps(source_hashes, indent=2) + "\n", encoding="utf-8")
    all_rows = []
    for phase in ("first_write", "before_pointer", "after_pointer"):
        child = _kill_commit_child(root=root, write_set=write_set, mode=phase)
        assert child.returncode == -signal.SIGKILL, child.stderr
        journal = GreenfieldCommitJournal(repo_root=root, transaction_hash="a" * 64, write_set=write_set)
        before_record = json.loads(journal.state_path.read_text(encoding="utf-8"))
        assert before_record["state"] == "projecting"
        before = _tree_hashes(root)
        selected_hash = write_set["write_set_hash"] if phase == "after_pointer" else baseline.write_set_hash
        selected_marker = "SEALED NEXT" if phase == "after_pointer" else "BASELINE"
        compatibility = {surface: ">SEALED NEXT</aside>" in (root / relative).read_text(encoding="utf-8")
                         for surface, relative in SURFACES.items()}
        assert compatibility == ({"atlas": True, "radar": False} if phase == "first_write" else {"atlas": True, "radar": True})
        try:
            all_rows.extend(_observe_dashboard(root, evidence, phase, selected_hash, selected_marker))
            assert _tree_hashes(root) == before
            assert json.loads(journal.state_path.read_text(encoding="utf-8")) == before_record
        finally:
            with greenfield_repository_lock.greenfield_repository_lock(root):
                result = journal.recover_or_return_committed()
            record = json.loads(journal.state_path.read_text(encoding="utf-8"))
            (evidence / f"{phase}-receipt.json").write_text(json.dumps({
                "child_returncode": child.returncode, "child_stderr": child.stderr,
                "before_recovery_journal": before_record, "compatibility_markers_next": compatibility,
                "after_recovery_journal": record, "active_publication": state.read_active_publication(root),
                "expected_generation": selected_hash,
            }, indent=2) + "\n", encoding="utf-8")
            assert record["state"] == ("closed" if phase == "after_pointer" else "aborted")
            assert (result is not None) == (phase == "after_pointer")
            if phase == "after_pointer":
                kernel.require_greenfield_repository_after_state(repo_root=root, write_set=write_set)
            else:
                kernel.require_greenfield_repository_preconditions(repo_root=root, write_set=write_set)
                journal.discard_recovered_abort()
    assert len(all_rows) == 6
    assert {relative: _hash(SOURCE / "odylith" / relative) for relative in source_hashes} == source_hashes
