"""Production publication carrier proof, not complete dashboard or journal qualification."""

from contextlib import nullcontext
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
)


def _carrier(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    entries = {}
    for name in ("A", "B"):
        staged = tmp_path / name
        surface = staged / "odylith"
        surface.mkdir(parents=True)
        (surface / "index.html").write_text(
            '<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<link rel="stylesheet" href="registry/carrier.css">'
            f'<h1>Carrier {name}</h1><p>Minimal immutable shell; not full product UX.</p>'
            '<iframe id="child" title="Generation child" src="registry/child.html"></iframe>', encoding="utf-8",
        )
        (surface / "registry").mkdir()
        (surface / "registry/child.html").write_text(f'<!doctype html><p id="child">Child {name}</p>', encoding="utf-8")
        (surface / "registry/carrier.css").write_text(
            "body{font:18px/1.5 system-ui;margin:24px}iframe{width:100%;box-sizing:border-box;border:1px solid #999}",
            encoding="utf-8",
        )
        write_set = write_sets.compile_greenfield_repository_write_set(source_root=repo, staged_root=staged)
        manifest = generations.compile_greenfield_generation_manifest(write_set)
        text = publication.compile_greenfield_publication_entry(
            write_set_hash=write_set["write_set_hash"],
            generation_manifest_sha256=hashlib.sha256(manifest.encode("utf-8")).hexdigest(),
        )
        pinned = generations.materialize_immutable_greenfield_generation(
            repo_root=repo, write_set=write_set, manifest_text=manifest,
        )
        assert (pinned.repository_root / "odylith/registry/child.html").is_file()
        assert (pinned.repository_root / "odylith/registry/carrier.css").is_file()
        entries[name] = (text, pinned)
    entry = repo / "odylith/index.html"
    entry.parent.mkdir()
    entry.write_text(entries["A"][0], encoding="utf-8")
    return repo, entry, entries


def _snapshot(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*") if path.is_file()}


def _capture(page, name):
    target = _failure_screenshot_path(name)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(target), full_page=True)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("protocol", ["file", "http"])
@pytest.mark.parametrize("state", ["normal", "malformed", "duplicate", "extra"])
def test_production_publication_carrier_preserves_generation_or_reports_corruption(tmp_path, width, protocol, state):
    repo, entry, entries = _carrier(tmp_path)
    text, generation = entries["A"]
    if state != "normal":
        record = json.dumps({"generation_manifest_sha256": generation.manifest_sha256,
                             "version": publication.PUBLICATION_ENTRY_VERSION,
                             "write_set_hash": generation.write_set_hash}, sort_keys=True, separators=(",", ":"))
        damaged = {"malformed": "{", "duplicate": '{"write_set_hash":' + json.dumps(generation.write_set_hash) + "," + record[1:],
                   "extra": '{"extra":true,' + record[1:]}[state]
        entry.write_text(text.replace(record, damaged), encoding="utf-8")
    before = _snapshot(repo)
    server = _static_server(root=repo) if protocol == "http" else nullcontext(None)
    with server as base_url:
        entry_url = base_url + "/odylith/index.html" if base_url else entry.as_uri()
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": width, "height": 1000})
            try:
                page, *errors = _new_page(context)
                requests = []
                page.on("request", lambda request: requests.append(request.url))
                page.goto(entry_url + "?tab=registry#retained-fragment", wait_until="domcontentloaded")
                if state == "normal":
                    page.get_by_role("heading", name="Carrier A", exact=True).wait_for()
                    assert page.frame_locator("#child").locator("#child").inner_text() == "Child A"
                    target_path = "/.odylith/runtime/greenfield/generations/" + generation.write_set_hash + "/repository/odylith/"
                    assert target_path in urlparse(page.url).path
                    assert urlparse(page.url).query == "tab=registry"
                    assert urlparse(page.url).fragment == "retained-fragment"
                    assert any(target_path + "registry/carrier.css" in url for url in requests)
                    assert any(target_path + "registry/child.html" in url for url in requests)
                    assert not any(entries["B"][1].write_set_hash in url for url in requests)
                else:
                    page.get_by_role("heading", name="Project unavailable", exact=True).wait_for()
                    assert page.get_by_role("status").inner_text() == (
                        "The published view could not be opened. No partial project is shown. Reload after recovery."
                    )
                    assert page.get_by_role("button", name="Reload", exact=True).is_visible()
                    assert not any("/generations/" in url for url in requests)
                    assert page.locator("iframe").count() == 0
                assert not page.locator("body").evaluate("node => node.scrollWidth > innerWidth + 1")
                _capture(page, f"publication-carrier-{protocol}-{width}-{state}")
                _assert_clean_page(page, *errors)
            finally:
                context.close()
    assert _snapshot(repo) == before


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_http_cached_entry_rechecks_current_publication_before_latching(tmp_path, width):
    repo, entry, entries = _carrier(tmp_path)
    before = _snapshot(repo)
    with _static_server(root=repo) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": width, "height": 1000})
            try:
                page, *errors = _new_page(context)
                carrier_requests = []

                def response(route):
                    carrier_requests.append(route.request.resource_type)
                    # Retained old navigation response, followed by the current production entry.
                    name = "A" if route.request.is_navigation_request() else "B"
                    route.fulfill(status=200, content_type="text/html", body=entries[name][0])

                page.route(base_url + "/odylith/index.html?tab=project", response)
                page.goto(base_url + "/odylith/index.html?tab=project", wait_until="domcontentloaded")
                page.get_by_role("heading", name="Carrier B", exact=True).wait_for()
                assert page.frame_locator("#child").locator("#child").inner_text() == "Child B"
                assert entries["B"][1].write_set_hash in page.url
                assert carrier_requests == ["document", "fetch"]
                _capture(page, f"publication-carrier-http-{width}-fresh-read")
                _assert_clean_page(page, *errors)
            finally:
                context.close()
    assert _snapshot(repo) == before
