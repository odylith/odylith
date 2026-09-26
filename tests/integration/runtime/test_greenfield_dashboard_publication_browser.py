"""Read the actual dashboard after SIGKILL, before any publication recovery."""

from __future__ import annotations

from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

import pytest

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _new_page, _static_server, playwright_sync,
)


SOURCE = Path(__file__).resolve().parents[3]
SURFACES = {
    "project": "odylith/index.html",
    "registry": "odylith/registry/registry.html",
    "casebook": "odylith/casebook/casebook.html",
    "atlas": "odylith/atlas/atlas.html",
    "radar": "odylith/radar/radar.html",
    "compass": "odylith/compass/compass.html",
}
MARKER = '<aside id="publication-proof" style="position:fixed;bottom:12px;left:12px;z-index:999999;background:white;color:black;border:2px solid black;padding:12px">BASELINE</aside>'
MAX_ASSET_CLOSURE_BYTES = 64 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


def _hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _tree_hashes(root):
    return {str(path.relative_to(root)): _hash(path) for path in root.rglob("*") if path.is_file()}


def _surface_readiness(page, *, require_marker=False):
    assert set(page.locator('[role="tab"][data-tab]').evaluate_all(
        'nodes => nodes.map(node => node.dataset.tab)')) == set(SURFACES)
    markers = {}
    for surface in SURFACES:
        page.locator("#tab-" + surface).click()
        page.locator(f'#tab-{surface}[aria-selected="true"]').wait_for()
        frame = page if surface == "project" else page.frame_locator("#frame-" + surface)
        if require_marker:
            marker = frame.locator("#publication-proof")
            marker.wait_for(state="visible", timeout=15000)
            markers[surface] = marker
        if surface == "atlas":
            frame.locator("#diagramId").wait_for()
            viewer = frame.locator("#viewerImage")
            playwright_sync.expect(viewer).to_have_js_property("complete", True, timeout=15000)
            playwright_sync.expect(viewer).not_to_have_js_property("naturalWidth", 0, timeout=15000)
        elif surface == "radar":
            frame.locator("#list button[data-idea-id]").first.wait_for(timeout=15000)
        elif surface == "registry":
            frame.locator("button[data-component]").first.wait_for(timeout=15000)
            frame.locator("#detail > *").first.wait_for(timeout=15000)
        elif surface == "casebook":
            frame.locator(".bug-row").first.wait_for(timeout=15000)
            frame.locator("#detailPane .detail-title").wait_for(timeout=15000)
        elif surface == "compass":
            frame.locator('body[data-surface-ready="ready"]').wait_for(timeout=15000)
            frame.locator("#risk-list .risk, #risk-list .empty").first.wait_for(timeout=15000)
            frame.locator("#digest-list > *").first.wait_for(timeout=15000)
            assert "Runtime data unavailable." not in frame.locator("#digest-list").inner_text()
            assert "Runtime Unavailable" not in frame.locator("#kpi-grid").inner_text()
    return markers


def _local_request_path(url, *, protocol, base_url):
    parsed = urlparse(url)
    if protocol == "file":
        if parsed.scheme != "file":
            return None
        candidate = Path(url2pathname(unquote(parsed.path))).resolve()
    else:
        if not url.startswith(base_url + "/"):
            return None
        candidate = (SOURCE / unquote(parsed.path).lstrip("/")).resolve()
    try:
        candidate.relative_to(SOURCE)
    except ValueError as exc:
        raise AssertionError(f"browser asset escaped the repository: {url}") from exc
    if candidate.is_symlink() or not candidate.is_file():
        raise AssertionError(f"browser asset is missing or unsafe: {url}")
    return candidate


def _asset_closure(protocol):
    requested = []
    server = _static_server(root=SOURCE) if protocol == "http" else nullcontext(None)
    with server as base_url:
        entry_url = base_url + "/odylith/index.html" if base_url else (SOURCE / "odylith/index.html").as_uri()
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            try:
                with _new_page(context) as (page, observation):
                    page.on("request", lambda request: requested.append(request.url))
                    page.goto(entry_url + "?tab=project", wait_until="networkidle")
                    _surface_readiness(page)
                    _assert_clean_page(page, observation)
            finally:
                context.close()
        assets = {
            path
            for url in requested
            if (path := _local_request_path(url, protocol=protocol, base_url=base_url)) is not None
        }
    assert SOURCE / "odylith/index.html" in assets
    closure_bytes = sum(path.stat().st_size for path in assets)
    assert closure_bytes <= MAX_ASSET_CLOSURE_BYTES, (
        f"browser asset closure is {closure_bytes} bytes, above {MAX_ASSET_CLOSURE_BYTES}"
    )
    return assets, closure_bytes


def _materialize_baseline(root):
    compile_script = """
import hashlib
import json
from pathlib import Path
import sys

from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel

root = Path(sys.argv[1])
baseline = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=root)
manifest = store.compile_greenfield_generation_manifest(baseline)
entry = state.compile_greenfield_publication_entry(
    write_set_hash=baseline["write_set_hash"],
    generation_manifest_sha256=hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
)
(root.parent / "baseline.json").write_text(json.dumps({
    "write_set": baseline,
    "manifest_text": manifest,
    "publication_entry_text": entry,
}, sort_keys=True), encoding="utf-8")
print(baseline["write_set_hash"])
"""
    publish_script = """
import json
from pathlib import Path
import sys

from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence import greenfield_generation_store as store

root = Path(sys.argv[1])
sealed = json.loads((root.parent / "baseline.json").read_text(encoding="utf-8"))
baseline = sealed["write_set"]
generation = store.materialize_immutable_greenfield_generation(
    repo_root=root, write_set=baseline, manifest_text=sealed["manifest_text"],
)
store.publish_greenfield_generation(
    repo_root=root,
    generation=generation,
    write_set=baseline,
    publication_entry_text=sealed["publication_entry_text"],
)
atomic_write_text(
    root / "odylith/tooling-shell.html",
    (generation.repository_root / "odylith/index.html").read_text(encoding="utf-8"),
)
"""
    environment = {**os.environ, "PYTHONPATH": str(SOURCE / "src")}
    compiled = subprocess.run(
        [sys.executable, "-c", compile_script, str(root)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    assert compiled.returncode == 0, compiled.stderr
    baseline_hash = compiled.stdout.strip()
    assert len(baseline_hash) == 64
    published = subprocess.run(
        [sys.executable, "-c", publish_script, str(root)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    assert published.returncode == 0, published.stderr
    (root.parent / "baseline.json").unlink()
    return baseline_hash


def _compile_transition_child(root, stage):
    script = """
import hashlib
import json
from pathlib import Path
import sys

from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel

root, stage = Path(sys.argv[1]), Path(sys.argv[2])
write_set = kernel.compile_greenfield_repository_write_set(source_root=root, staged_root=stage)
manifest = store.compile_greenfield_generation_manifest(write_set)
publication = state.compile_greenfield_publication_entry(
    write_set_hash=write_set["write_set_hash"],
    generation_manifest_sha256=hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
)
(root.parent / "write-set.json").write_text(
    json.dumps({
        "write_set": write_set,
        "manifest_text": manifest,
        "publication_entry_text": publication,
    }, sort_keys=True), encoding="utf-8",
)
print(json.dumps({
    "write_set_hash": write_set["write_set_hash"],
    "write_count": write_set["write_count"],
    "write_paths": sorted(row["path"] for row in write_set["writes"]),
}, sort_keys=True))
"""
    environment = {**os.environ, "PYTHONPATH": str(SOURCE / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), str(stage)],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    identity = json.loads(completed.stdout)
    assert isinstance(identity, dict)
    return identity


def _kill_writer_child(root, phase):
    script = """
import json
import os
from pathlib import Path
import signal
import sys

from odylith.runtime.domain_intelligence import greenfield_generation_store as store
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction

root, phase = Path(sys.argv[1]), sys.argv[2]
sealed = json.loads((root.parent / "write-set.json").read_text(encoding="utf-8"))
write_set = sealed["write_set"]
journal = GreenfieldCommitJournal(repo_root=root, transaction_hash="a" * 64, write_set=write_set)
journal.prepare()
transaction = GreenfieldApplyTransaction(
    root, paths=journal.paths, snapshot_root=journal.snapshot_root, retain_snapshot=True,
)
with transaction:
    journal.mark_prepared()
    result = {"repository_write_set": {"write_set_hash": write_set["write_set_hash"]}}
    generation = store.materialize_immutable_greenfield_generation(
        repo_root=root, write_set=write_set, manifest_text=sealed["manifest_text"],
    )
    journal.mark_projecting(
        result,
        generation_manifest_sha256=generation.manifest_sha256,
        publication_entry_text=sealed["publication_entry_text"],
    )
    if phase == "first_write":
        original = kernel.atomic_write_bytes
        calls = 0
        def kill_after_first(path, data, *, mode=None, temporary_directory=None):
            global calls
            calls += 1
            result = original(path, data, mode=mode, temporary_directory=temporary_directory)
            if calls == 1:
                os.kill(os.getpid(), signal.SIGKILL)
            return result
        kernel.atomic_write_bytes = kill_after_first
    kernel.apply_compiled_greenfield_repository_write_set(repo_root=root, write_set=write_set)
    if phase == "before_pointer":
        os.kill(os.getpid(), signal.SIGKILL)
    if phase == "after_pointer":
        transaction.publish(
            lambda: store.publish_greenfield_generation(
                repo_root=root,
                generation=generation,
                write_set=write_set,
                publication_entry_text=sealed["publication_entry_text"],
            ),
            published_probe=journal.publication_is_active,
        )
        os.kill(os.getpid(), signal.SIGKILL)
"""
    environment = {**os.environ, "PYTHONPATH": str(SOURCE / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), phase],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    return {"returncode": completed.returncode, "stderr": completed.stderr}


def _recover_commit_child(root, *, expect_committed):
    script = """
import json
from pathlib import Path
import sys

from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as kernel
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal

root = Path(sys.argv[1])
expect_committed = sys.argv[2] == "committed"
sealed = json.loads((root.parent / "write-set.json").read_text(encoding="utf-8"))
journal = GreenfieldCommitJournal(
    repo_root=root, transaction_hash="a" * 64, write_set=sealed["write_set"],
)
before_state = json.loads(journal.state_path.read_text(encoding="utf-8"))["state"]
if before_state != "projecting":
    raise AssertionError(f"expected projecting journal before recovery, got {before_state}")
with greenfield_repository_lock.greenfield_repository_lock(root):
    result = journal.recover_or_return_committed()
after_state = json.loads(journal.state_path.read_text(encoding="utf-8"))["state"]
if result is None:
    identity = {"outcome": "aborted", "before_state": before_state, "after_state": after_state}
    if expect_committed:
        raise AssertionError("expected committed recovery")
    if after_state != "aborted":
        raise AssertionError(f"expected aborted journal after recovery, got {after_state}")
    kernel.require_greenfield_repository_preconditions(repo_root=root, write_set=sealed["write_set"])
    journal.discard_recovered_abort()
else:
    identity = {
        "outcome": "committed",
        "before_state": before_state,
        "after_state": after_state,
        "write_set_hash": result["repository_write_set"]["write_set_hash"],
    }
    if not expect_committed:
        raise AssertionError("expected aborted recovery")
    if after_state != "closed":
        raise AssertionError(f"expected closed journal after recovery, got {after_state}")
    kernel.require_greenfield_repository_after_state(repo_root=root, write_set=sealed["write_set"])
print(json.dumps(identity, sort_keys=True))
"""
    environment = {**os.environ, "PYTHONPATH": str(SOURCE / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", script, str(root), "committed" if expect_committed else "aborted"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    identity = json.loads(completed.stdout)
    assert isinstance(identity, dict)
    return identity


def _protected_dashboard(tmp_path, protocol):
    root, stage = tmp_path / "repo", tmp_path / "stage"
    assets, closure_bytes = _asset_closure(protocol)
    sources = {}
    for source in sorted(assets):
        relative = source.relative_to(SOURCE)
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        sources[relative.as_posix()] = source
    source_hashes = {relative: _hash(path) for relative, path in sources.items()}
    for relative in SURFACES.values():
        path = root / relative
        html = path.read_text(encoding="utf-8")
        assert "</body>" in html and 'id="publication-proof"' not in html
        atomic_write_text(path, html.replace("</body>", MARKER + "</body>"))
    baseline_hash = _materialize_baseline(root)
    generation_root = store.generation_root(root, baseline_hash) / "repository"
    # This is a protected baseline setup, not proof of first activation through CONFIRM.
    shutil.copytree(generation_root / "odylith", stage / "odylith", copy_function=os.link)
    for relative in SURFACES.values():
        path = stage / relative
        atomic_write_text(path, path.read_text(encoding="utf-8").replace(
            ">BASELINE</aside>", ">SEALED NEXT</aside>",
        ))
        assert ">BASELINE</aside>" in (generation_root / relative).read_text(encoding="utf-8")
    transition = _compile_transition_child(root, stage)
    assert transition["write_count"] == len(SURFACES)
    assert set(transition["write_paths"]) == set(SURFACES.values())
    return root, baseline_hash, transition, source_hashes, closure_bytes


def _observe_dashboard(root, evidence, phase, expected_hash, expected_marker, protocol):
    observations = []
    try:
        server = _static_server(root=root) if protocol == "http" else nullcontext(None)
        with server as base_url:
            entry_url = base_url + "/odylith/index.html" if base_url else (root / "odylith/index.html").as_uri()
            for _pw, browser in _browser():
                for width in (1440, 430):
                    context = browser.new_context(viewport={"width": width, "height": 1000})
                    try:
                        with _new_page(context) as (page, observation):
                            requested = []
                            page.on("request", lambda request: requested.append(request.url))
                            row = {"width": width, "phase": phase, "surfaces": {}}
                            observations.append(row)
                            page.goto(entry_url + "?tab=project", wait_until="networkidle")
                            markers = _surface_readiness(page, require_marker=True)
                            expected_prefix = "/.odylith/runtime/greenfield/generations/" + expected_hash + "/repository/"
                            for surface, relative in SURFACES.items():
                                page.locator("#tab-" + surface).click()
                                page.locator(f'#tab-{surface}[aria-selected="true"]').wait_for()
                                frame = page if surface == "project" else page.frame_locator("#frame-" + surface)
                                row["surfaces"][surface] = {"marker": markers[surface].inner_text(), "shell_url": page.url,
                                    "child_url": page.url if surface == "project" else page.locator("#frame-" + surface).element_handle().content_frame().url}
                                page.screenshot(path=str(evidence / f"{phase}-{width}-{surface}.png"))
                                assert expected_prefix + "odylith/index.html" in page.url
                                assert expected_prefix + relative in row["surfaces"][surface]["child_url"]
                                assert row["surfaces"][surface]["marker"] == expected_marker
                            row["requests"] = requested
                            assert not any(
                                "/generations/" in url and expected_hash not in url for url in requested
                            ), requested
                            local = [url for url in requested if urlparse(url).scheme == "file" or
                                     (base_url and url.startswith(base_url + "/"))]
                            assert all(urlparse(url).path == urlparse(entry_url).path or expected_prefix in urlparse(url).path
                                       for url in local), local
                            snapshot = observation.finish()
                            row["errors"] = {
                                "console": snapshot.console_errors,
                                "page": snapshot.page_errors,
                                "http": [{"status": error.status, "url": error.url} for error in snapshot.http_errors],
                                "native": snapshot.native_result.errors if snapshot.native_result else None,
                                "complete": snapshot.complete,
                                "lifecycle": snapshot.lifecycle_errors,
                            }
                            _assert_clean_page(page, observation)
                    finally:
                        context.close()
    finally:
        (evidence / f"{phase}-observations.json").write_text(json.dumps(observations, indent=2) + "\n", encoding="utf-8")
    return observations


def _file_identity(path):
    return {"sha256": _hash(path), "size_bytes": path.stat().st_size}


@pytest.mark.parametrize("protocol", ["file", "http"])
def test_actual_dashboard_remains_one_generation_after_killed_writer_before_recovery(tmp_path, protocol):
    evidence = Path(os.environ.get("ODYLITH_PUBLICATION_CRASH_EVIDENCE", str(tmp_path / "evidence"))) / protocol
    evidence.mkdir(parents=True, exist_ok=False)
    root, baseline_hash, write_set, source_hashes, closure_bytes = _protected_dashboard(tmp_path, protocol)
    (evidence / "source-assets.json").write_text(json.dumps(source_hashes, indent=2) + "\n", encoding="utf-8")
    (evidence / "fixture.json").write_text(json.dumps({
        "root": str(root), "stage": str(tmp_path / "stage"), "protocol": protocol,
        "baseline_write_set_hash": baseline_hash, "next_write_set_hash": write_set["write_set_hash"],
        "asset_closure_bytes": closure_bytes, "asset_count": len(source_hashes),
    }, indent=2) + "\n", encoding="utf-8")
    before_normal = _tree_hashes(root)
    all_rows = _observe_dashboard(root, evidence, "normal", baseline_hash, "BASELINE", protocol)
    assert _tree_hashes(root) == before_normal
    for phase in ("first_write", "before_pointer", "after_pointer"):
        child = _kill_writer_child(root, phase)
        assert child["returncode"] == -signal.SIGKILL, child["stderr"]
        journal_state_path = (
            root / ".odylith/runtime/greenfield/create-journal" / ("a" * 64) / "state.v1.json"
        )
        journal_before_browser = _file_identity(journal_state_path)
        before = _tree_hashes(root)
        selected_hash = write_set["write_set_hash"] if phase == "after_pointer" else baseline_hash
        selected_marker = "SEALED NEXT" if phase == "after_pointer" else "BASELINE"
        layout = kernel.greenfield_repository_layout(root)
        compatibility = {surface: ">SEALED NEXT</aside>" in layout.target_path(relative).read_text(encoding="utf-8")
                         for surface, relative in SURFACES.items()}
        assert sum(compatibility.values()) == (1 if phase == "first_write" else len(SURFACES))
        journal_after_browser = None
        try:
            all_rows.extend(_observe_dashboard(root, evidence, phase, selected_hash, selected_marker, protocol))
            assert _tree_hashes(root) == before
            journal_after_browser = _file_identity(journal_state_path)
            assert journal_after_browser == journal_before_browser
        finally:
            result_identity = _recover_commit_child(root, expect_committed=phase == "after_pointer")
            active_publication = state.read_active_publication(root)
            (evidence / f"{phase}-receipt.json").write_text(json.dumps({
                "phase": phase,
                "child_returncode": child["returncode"], "child_stderr": child["stderr"],
                "journal_before_browser": journal_before_browser,
                "journal_after_browser": journal_after_browser,
                "compatibility_markers_next": compatibility,
                "recovery_result": result_identity, "active_publication": active_publication,
                "expected_generation": selected_hash,
            }, indent=2) + "\n", encoding="utf-8")
            if phase == "after_pointer":
                assert result_identity == {
                    "outcome": "committed",
                    "before_state": "projecting",
                    "after_state": "closed",
                    "write_set_hash": write_set["write_set_hash"],
                }
            else:
                assert result_identity == {
                    "outcome": "aborted",
                    "before_state": "projecting",
                    "after_state": "aborted",
                }
    assert len(all_rows) == 8
    assert {relative: _hash(SOURCE / relative) for relative in source_hashes} == source_hashes
