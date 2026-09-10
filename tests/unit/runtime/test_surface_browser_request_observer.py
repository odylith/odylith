"""Native-ID cancellation contracts for the unintegrated browser observer candidate."""

from dataclasses import FrozenInstanceError
import json
import traceback
from types import SimpleNamespace

import pytest

from tests.integration.runtime.surface_browser_request_observer import NativeRequestObserver, RequestLedger
from tests.integration.runtime import surface_browser_request_observer as observation_owner


BASE = "http://127.0.0.1:9876"


class Flow:
    def __init__(self, original_url=None, original_status=200):
        self.ledger = RequestLedger("target", "context")
        self.parents = {"main": None}
        self.requests = {}
        self.ledger.seed_frame_tree({"frame": {"id": "main", "loaderId": "seed-is-not-proof"}})
        self.nav("original", "main", url=original_url)
        self.complete("original", status=original_status)

    def emit(self, method, **params):
        self.ledger.ingest(method, params)

    def child(self, identifier="child", parent="main"):
        self.parents[identifier] = parent
        self.emit("Page.frameAttached", frameId=identifier, parentFrameId=parent)
        self.nav(identifier + "-document", identifier)
        self.complete(identifier + "-document")
        return identifier

    def nav(self, identifier, frame="main", *, loader=None, url=None, kind="Document"):
        data = dict(requestId=identifier, frameId=frame, loaderId=loader or identifier + "-loader",
                    type=kind, request={"url": BASE + "/" + identifier + ".html" if url is None else url})
        self.requests[identifier] = data
        self.ledger.ingest("Network.requestWillBeSent", data)

    def resource(self, identifier="asset", frame="child", *, url=None):
        self.nav(identifier, frame, loader=frame + "-document-loader", kind="Script", url=url)

    def response(self, identifier, status=200):
        data = self.requests[identifier]
        self.emit("Network.responseReceived", requestId=identifier, frameId=data["frameId"],
                  loaderId=data["loaderId"], response={"url": data["request"]["url"], "status": status})

    def commit(self, identifier):
        data = self.requests[identifier]
        self.emit("Page.frameNavigated", frame={"id": data["frameId"], "loaderId": data["loaderId"],
                  "parentId": self.parents[data["frameId"]], "url": data["request"]["url"]})

    def finish(self, identifier):
        self.emit("Network.loadingFinished", requestId=identifier)

    def complete(self, identifier, *, status=200):
        self.response(identifier, status)
        self.commit(identifier)
        self.finish(identifier)

    def fail(self, identifier, reason="net::ERR_ABORTED", canceled=True):
        self.emit("Network.loadingFailed", requestId=identifier, errorText=reason, canceled=canceled)

    def redirect(self, identifier, url, status=302):
        data = dict(self.requests[identifier])
        data["redirectResponse"] = {"status": status, "url": data["request"]["url"]}
        data["request"] = {"url": url}
        self.requests[identifier] = data
        self.ledger.ingest("Network.requestWillBeSent", data)

    def remove(self, frame="child", reason="remove"):
        self.emit("Page.frameDetached", frameId=frame, reason=reason)

    def assert_failed(self):
        result = self.ledger.cutoff()
        assert result.errors
        assert not result.cancellations
        return result


@pytest.mark.parametrize("url", (BASE + "/legacy.html", BASE + "/.odylith/runtime/greenfield/generations/arbitrary/repository/selected.html", BASE + "/original.html"))
@pytest.mark.parametrize("order", ("normal", "finish-before-commit", "same-document-event"))
def test_exact_distinct_loader_success_reconciles_document_abort_without_url_identity(url, order):
    flow = Flow()
    flow.nav("aborted")
    flow.fail("aborted")
    flow.nav("successor", url=url)
    flow.response("successor")
    if order == "same-document-event":
        flow.emit("Page.navigatedWithinDocument", frameId="main", url=BASE + "/history-mutated")
    if order == "finish-before-commit":
        flow.finish("successor")
    flow.commit("successor")
    if order != "finish-before-commit":
        flow.finish("successor")
    result = flow.ledger.cutoff()
    assert result.errors == ()
    assert len(result.cancellations) == 1
    proof = result.cancellations[0]
    assert (proof.request_id, proof.replacement_id) == ("aborted", "successor")
    assert proof.loader_id != proof.replacement_loader_id
    assert flow.ledger.failures[0].reason == "net::ERR_ABORTED"


@pytest.mark.parametrize("counterexample", (
    "different-frame", "same-loader", "unknown-reason", "not-canceled", "reset", "missing-origin",
    "file", "different-port", "different-host", "different-scheme", "missing-response", "missing-commit",
    "missing-finish", "failed-successor", "failed-then-successful", "incomplete-then-successful",
    "already-committed-source", "unmatched-transition", "old-loader-commit", "same-document-only",
))
def test_document_abort_requires_unbroken_immediate_native_successor(counterexample):
    flow = Flow()
    if counterexample == "different-frame":
        flow.child()
    source_url = "" if counterexample == "missing-origin" else "file:///tmp/local.html" if counterexample == "file" else BASE + "/failed.html"
    flow.nav("aborted", url=source_url)
    if counterexample == "already-committed-source":
        flow.response("aborted")
        flow.commit("aborted")
    flow.fail("aborted", reason=None if counterexample == "unknown-reason" else "net::ERR_CONNECTION_RESET" if counterexample == "reset" else "net::ERR_ABORTED", canceled=counterexample != "not-canceled")
    if counterexample == "unmatched-transition":
        flow.emit("Page.frameNavigated", frame={"id": "main", "loaderId": "unrepresented", "url": BASE + "/failed.html"})
    if counterexample == "old-loader-commit":
        flow.commit("original")
    target_url = {"different-port": "http://127.0.0.1:9999/selected", "different-host": "http://localhost:9876/selected", "different-scheme": "https://127.0.0.1:9876/selected"}.get(counterexample, BASE + "/selected")
    flow.nav("successor", "child" if counterexample == "different-frame" else "main",
             loader="aborted-loader" if counterexample == "same-loader" else None, url=target_url)
    if counterexample != "missing-response":
        flow.response("successor")
    if counterexample == "same-document-only":
        flow.emit("Page.navigatedWithinDocument", frameId="main", url=target_url)
    elif counterexample != "missing-commit":
        flow.commit("successor")
    if counterexample in {"failed-successor", "failed-then-successful"}:
        flow.fail("successor", "net::ERR_EMPTY_RESPONSE", False)
    if counterexample not in {"missing-finish", "incomplete-then-successful"}:
        flow.finish("successor")
    if counterexample in {"failed-then-successful", "incomplete-then-successful"}:
        flow.nav("later")
        flow.complete("later")
    flow.assert_failed()


@pytest.mark.parametrize("target", (BASE + "/after-redirect", "http://localhost:9876/foreign-hop"))
@pytest.mark.parametrize("status", (302, 404, 503))
def test_redirects_are_one_identity_history_and_cannot_erase_origin_or_http_errors(target, status):
    flow = Flow()
    flow.nav("aborted")
    flow.fail("aborted")
    flow.nav("successor")
    flow.redirect("successor", target, status)
    flow.redirect("successor", BASE + "/final")
    flow.complete("successor")
    result = flow.ledger.cutoff()
    if status == 302 and target.startswith(BASE):
        assert result.errors == ()
        assert result.cancellations[0].replacement_id == "successor"
    else:
        assert result.errors
        assert result.cancellations == ()


@pytest.mark.parametrize("status", (404, 503))
@pytest.mark.parametrize("origin", (BASE, "https://elsewhere.invalid", "file:///tmp"))
def test_all_http_errors_remain_errors_even_with_exact_abort_or_loading_finished(status, origin):
    flow = Flow()
    flow.nav("error", url=origin + "/required")
    flow.response("error", status)
    flow.fail("error")
    flow.commit("error")
    flow.finish("error")
    flow.nav("later")
    flow.complete("later")
    result = flow.assert_failed()
    assert any(f"HTTP {status}" in error for error in result.errors)


@pytest.mark.parametrize("nesting", (1, 2))
def test_resource_abort_uses_exact_removed_child_and_already_inflight_ancestor(nesting):
    flow = Flow()
    flow.child()
    frame = flow.child("nested", "child") if nesting == 2 else "child"
    flow.resource(frame=frame)
    flow.nav("replacement")
    flow.fail("asset")
    flow.remove(frame)
    flow.complete("replacement")
    result = flow.ledger.cutoff()
    assert result.errors == ()
    proof = result.cancellations[0]
    assert proof.frame_id == frame
    assert proof.replacement_frame_id == "main"
    assert proof.removal_index < proof.commit_index


@pytest.mark.parametrize("early_removal", (False, True))
def test_repeated_native_detach_preserves_first_removal_and_fails_coverage(early_removal):
    flow = Flow()
    flow.child()
    flow.resource()
    if early_removal:
        flow.remove()
    flow.nav("replacement")
    flow.fail("asset")
    if not early_removal:
        flow.remove()
    first_removal = next(event.index for event in flow.ledger.observations
                         if event.method == "Page.frameDetached")
    flow.remove()
    flow.complete("replacement")
    assert flow.ledger._frames["child"].removed == first_removal
    assert any("coverage failure" in error for error in flow.assert_failed().errors)
    assert len([event for event in flow.ledger.observations if event.method == "Page.frameDetached"]) == 2
    assert flow.ledger.failures[0].reason == "net::ERR_ABORTED"


@pytest.mark.parametrize("frame", ("nested", "child"))
@pytest.mark.parametrize("transition", ("owned", "unmatched", "A-to-B-to-A"))
@pytest.mark.parametrize("moment", ("before-parent", "during-parent", "after-abort"))
def test_resource_departure_requires_uninterrupted_lower_loader_lineage(frame, transition, moment):
    flow = Flow()
    flow.child()
    flow.child("nested", "child")
    flow.resource(frame="nested")
    if moment != "before-parent":
        flow.nav("replacement")
    if moment == "after-abort":
        flow.fail("asset")
    if transition == "unmatched":
        flow.emit("Page.frameNavigated", frame={"id": frame, "parentId": flow.parents[frame],
                  "loaderId": "unrepresented", "url": BASE + "/arbitrary"})
    else:
        flow.nav("intervening", frame)
        flow.complete("intervening")
        if transition == "A-to-B-to-A":
            flow.commit(frame + "-document")
    if moment == "before-parent":
        flow.nav("replacement")
    if moment != "after-abort":
        flow.fail("asset")
    flow.remove("nested")
    flow.complete("replacement")
    result = flow.assert_failed()
    assert not any("coverage failure" in error for error in result.errors)
    assert flow.ledger.failures[0].reason == "net::ERR_ABORTED"


@pytest.mark.parametrize("frame", ("nested", "child"))
def test_same_document_events_preserve_lower_loader_continuity(frame):
    flow = Flow()
    flow.child()
    flow.child("nested", "child")
    flow.resource(frame="nested")
    flow.nav("replacement")
    flow.fail("asset")
    flow.emit("Page.navigatedWithinDocument", frameId=frame, url=BASE + "/history#fragment")
    flow.remove("nested")
    flow.complete("replacement")
    result = flow.ledger.cutoff()
    assert result.errors == ()
    assert len(result.cancellations) == 1


@pytest.mark.parametrize("moment", ("before-request", "after-removal"))
def test_lower_frame_transitions_outside_resource_lifetime_do_not_break_departure(moment):
    flow = Flow()
    flow.child()
    flow.child("nested", "child")
    if moment == "before-request":
        flow.nav("earlier", "child")
        flow.complete("earlier")
        flow.commit("child-document")
    flow.resource(frame="nested")
    flow.nav("replacement")
    flow.fail("asset")
    flow.remove("nested")
    if moment == "after-removal":
        flow.nav("later", "child")
        flow.complete("later")
    flow.complete("replacement")
    result = flow.ledger.cutoff()
    assert result.errors == ()
    assert len(result.cancellations) == 1


@pytest.mark.parametrize("counterexample", (
    "future-navigation", "removal-before-navigation", "future-removal-after-commit", "abort-after-commit",
    "no-removal", "different-child-removal", "swap", "unknown-detach", "failed-first-navigation",
    "incomplete-first-navigation", "source-http-error", "different-origin", "same-frame-navigation",
))
def test_resource_abort_cannot_borrow_future_departure_or_later_ancestor_success(counterexample):
    flow = Flow()
    flow.child()
    flow.child("sibling")
    flow.resource(url="http://localhost:9876/asset.js" if counterexample == "different-origin" else None)
    if counterexample == "source-http-error":
        flow.response("asset", 404)
    if counterexample == "removal-before-navigation":
        flow.remove()
    if counterexample == "future-navigation":
        flow.fail("asset")
    flow.nav("replacement", "child" if counterexample == "same-frame-navigation" else "main")
    if counterexample == "abort-after-commit":
        flow.response("replacement")
        flow.commit("replacement")
    if counterexample != "future-navigation":
        flow.fail("asset")
    if counterexample not in {"no-removal", "removal-before-navigation", "future-removal-after-commit"}:
        flow.remove("sibling" if counterexample == "different-child-removal" else "child",
                    "swap" if counterexample == "swap" else "unknown" if counterexample == "unknown-detach" else "remove")
    if counterexample == "failed-first-navigation":
        flow.fail("replacement", "net::ERR_EMPTY_RESPONSE", False)
    if counterexample not in {"incomplete-first-navigation", "abort-after-commit"}:
        flow.complete("replacement")
    if counterexample == "abort-after-commit":
        flow.finish("replacement")
    if counterexample == "future-removal-after-commit":
        flow.remove()
    if counterexample in {"failed-first-navigation", "incomplete-first-navigation"}:
        flow.nav("later")
        flow.complete("later")
    flow.assert_failed()


@pytest.mark.parametrize("gap", ("unknown-request", "unknown-frame", "empty-loader", "response-mismatch", "iframe-target", "worker-target", "prerender-page", "session-loss", "target-loss"))
def test_coverage_gaps_permanently_fail_interval_even_after_a_qualifying_replacement(gap):
    flow = Flow()
    flow.nav("aborted")
    flow.fail("aborted")
    if gap == "unknown-request":
        flow.emit("Network.loadingFinished", requestId="missing")
    elif gap in {"unknown-frame", "empty-loader"}:
        flow.emit("Network.requestWillBeSent", requestId="bad", frameId="missing" if gap == "unknown-frame" else "main", loaderId="" if gap == "empty-loader" else "bad-loader", type="Document", request={"url": BASE})
    elif gap == "response-mismatch":
        flow.emit("Network.responseReceived", requestId="aborted", frameId="main", loaderId="wrong", response={"status": 200})
    elif gap in {"iframe-target", "worker-target", "prerender-page"}:
        # Ordinary pages are outside the observed frame tree; prerenders are not.
        info = {"targetId": "other", "browserContextId": "context", "type": {"iframe-target": "iframe", "worker-target": "worker", "prerender-page": "page"}[gap]}
        if gap == "prerender-page":
            info["subtype"] = "prerender"
        flow.emit("Target.targetCreated", targetInfo=info)
    elif gap == "target-loss":
        flow.emit("Target.targetDestroyed", targetId="target")
    else:
        flow.emit("Inspector.detached", reason="target_closed")
    flow.nav("successor")
    flow.complete("successor")
    assert any("coverage failure" in error for error in flow.assert_failed().errors)


def test_seeded_loader_is_topology_not_transport_or_committed_document_proof():
    ledger = RequestLedger("target", "context")
    ledger.seed_frame_tree({"frame": {"id": "main", "loaderId": "seed"}})
    ledger.ingest("Network.requestWillBeSent", {"requestId": "asset", "frameId": "main", "loaderId": "seed", "type": "Script", "request": {"url": BASE + "/asset.js"}})
    assert ledger.cutoff().errors


@pytest.mark.parametrize("payload", (None, [], {"requestId": "missing"}))
def test_malformed_network_payload_is_audited_as_permanent_coverage_loss(payload):
    ledger = RequestLedger("target", "context")
    ledger.ingest("Network.loadingFailed", payload)
    assert any("coverage failure" in error for error in ledger.cutoff().errors)
    assert json.loads(ledger.observations[0].payload) == payload


def test_unknown_structured_error_does_not_expose_mutable_failure_audit():
    flow = Flow()
    flow.nav("aborted")
    flow.fail("aborted", {"message": "not-the-protocol-string"})
    assert flow.ledger.failures[0].reason == "<unknown failure>"
    assert "not-the-protocol-string" in flow.ledger.observations[-1].payload


def test_explicit_port_zero_is_not_default_port_origin():
    flow = Flow(original_url="http://127.0.0.1/original")
    flow.nav("aborted", url="http://127.0.0.1:0/source")
    flow.fail("aborted")
    flow.nav("successor", url="http://127.0.0.1/target")
    flow.complete("successor")
    flow.assert_failed()


def test_malformed_seed_parent_cannot_lend_ancestor_ownership():
    ledger = RequestLedger("target", "context")
    ledger.seed_frame_tree({"frame": {"id": "main"}, "childFrames": [{"frame": {"id": "child", "parentId": "elsewhere"}}]})
    assert ledger.cutoff().errors


@pytest.mark.parametrize("gap", ("root-removed", "empty-target-context"))
def test_late_root_or_unscoped_target_loss_invalidates_prior_qualification(gap):
    flow = Flow()
    flow.nav("aborted")
    flow.fail("aborted")
    flow.nav("successor")
    flow.complete("successor")
    if gap == "root-removed":
        flow.remove("main")
    else:
        flow.emit("Target.targetCreated", targetInfo={"targetId": "unscoped", "browserContextId": "", "type": "worker"})
    assert any("coverage failure" in error for error in flow.assert_failed().errors)


def test_http_error_in_originating_ancestor_cannot_lend_cancellation_authority():
    flow = Flow(original_status=404)
    flow.child()
    flow.resource()
    flow.nav("replacement")
    flow.fail("asset")
    flow.remove()
    flow.complete("replacement")
    flow.assert_failed()


def test_raw_failure_is_immutable_and_post_cutoff_events_cannot_rewrite_result():
    flow = Flow()
    flow.nav("aborted")
    params = {"requestId": "aborted", "errorText": "net::ERR_ABORTED", "canceled": True}
    flow.ledger.ingest("Network.loadingFailed", params)
    params["errorText"] = "changed-by-caller"
    result = flow.ledger.cutoff()
    flow.nav("late")
    flow.complete("late")
    flow.fail("aborted", "cleanup-error", False)
    assert flow.ledger.cutoff() is result
    assert result.errors and not result.cancellations
    assert len(flow.ledger.failures) == 2
    assert flow.ledger.failures[0].reason == "net::ERR_ABORTED"
    with pytest.raises(FrozenInstanceError):
        flow.ledger.failures[0].reason = "overwrite"
    original = next(row for row in flow.ledger.observations if row.method == "Network.loadingFailed")
    assert json.loads(original.payload)["errorText"] == "net::ERR_ABORTED"


class Session:
    def __init__(self, fail_detach=False):
        self.handlers, self.commands, self.fail_detach = {}, [], fail_detach

    def on(self, name, callback):
        self.handlers[name] = callback

    def send(self, method, params=None):
        self.commands.append((method, params))
        if method == "Target.getTargetInfo":
            return {"targetInfo": {"targetId": "target", "browserContextId": "context", "type": "page"}}
        if method == "Page.getFrameTree":
            return {"frameTree": {"frame": {"id": "main"}}}
        return {}

    def detach(self):
        if self.fail_detach:
            raise RuntimeError("TargetClosed")


@pytest.mark.parametrize("close_before_cutoff", (False, True))
def test_public_adapter_cutoff_precedes_cleanup_without_late_snapshot_commands(close_before_cutoff):
    session = Session()
    page = SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda target: session), on=lambda *args: None)
    observer = NativeRequestObserver(page)
    commands = tuple(session.commands)
    if not close_before_cutoff:
        assert observer.cutoff().errors == ()
    observer.close()
    assert bool(observer.cutoff().errors) is close_before_cutoff
    assert tuple(session.commands) == commands


def test_public_adapter_explicit_lost_target_close_is_audited_and_raised():
    session = Session(fail_detach=True)
    page = SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda target: session), on=lambda *args: None)
    observer = NativeRequestObserver(page)
    observer.cutoff()
    with pytest.raises(RuntimeError, match="TargetClosed"):
        observer.close()
    assert "explicit CDP detach failed" in observer.ledger.observations[-1].payload


@pytest.mark.parametrize("method", ("Target.getTargetInfo", "Page.enable", "Network.enable"))
def test_adapter_initialization_failure_releases_its_owned_session(method):
    session = Session()
    detached = []
    original = session.send
    def send(name, params=None):
        if name == method:
            raise RuntimeError("setup failed")
        return original(name, params)
    session.send = send
    session.detach = lambda: detached.append(True)
    page = SimpleNamespace(context=SimpleNamespace(new_cdp_session=lambda target: session), on=lambda *args: None)
    with pytest.raises(RuntimeError, match="setup failed"):
        NativeRequestObserver(page)
    assert detached == [True]


class PublicSession(Session):
    """Public CDP session double shared by event and recording contract controls."""

    def __init__(self, context):
        super().__init__()
        self.context = context

    def send(self, method, params=None):
        if method in self.context.faults:
            raise RuntimeError("setup failed: " + method)
        return super().send(method, params)

    def detach(self):
        self.context.actions.append("detach")
        if "detach" in self.context.faults:
            raise RuntimeError("detach failed")


class PublicPage:
    def __init__(self, context):
        self.context, self.handlers, self.closed = context, {}, False

    def on(self, name, callback):
        self.handlers.setdefault(name, []).append(callback)

    def emit(self, name, value):
        for callback in self.handlers.get(name, ()):
            callback(value)

    def is_closed(self):
        return self.closed

    def screenshot(self, **kwargs):
        self.context.actions.append("screenshot")
        if "screenshot" in self.context.faults:
            raise RuntimeError("screenshot failed")

    def close(self):
        self.context.actions.append("close")
        if "close" in self.context.faults:
            raise RuntimeError("close failed")
        self.closed = True
        self.emit("close", self)


class PublicContext:
    def __init__(self, *faults):
        self.faults, self.actions = faults, []
        self.page = PublicPage(self)
        self.session = PublicSession(self)

    def new_page(self):
        self.actions.append("new_page")
        return self.page

    def new_cdp_session(self, page):
        assert page is self.page
        if "attach" in self.faults:
            raise RuntimeError("attach failed")
        return self.session

    def native(self, method, **params):
        self.session.handlers[method](params)


def test_owned_observation_finishes_once_before_clean_assertion_returns():
    context = PublicContext()
    with observation_owner.PageObservation(context) as (page, observation):
        observation_owner.assert_clean_page(page, observation)
        snapshot = observation.finish()
        assert snapshot is observation.snapshot
        assert snapshot.complete and not snapshot.errors
        assert page.is_closed()
    assert context.actions == ["new_page", "detach", "close"]


@pytest.mark.parametrize("faults", (("attach",), ("Page.enable",), ("attach", "close"), ("Page.enable", "detach", "close")))
def test_owned_observation_setup_failure_closes_page_and_preserves_combined_faults(faults):
    context = PublicContext(*faults)
    with pytest.raises(BaseException) as caught:
        with observation_owner.PageObservation(context):
            pytest.fail("setup failure must not enter the body")
    assert context.actions.count("close") == 1
    rendered = "".join(traceback.format_exception(caught.value))
    for fault in faults:
        assert fault in rendered


def test_missing_declared_finalization_is_incomplete_even_with_no_network_errors():
    context = PublicContext()
    with pytest.raises(AssertionError, match="incomplete observation"):
        with observation_owner.PageObservation(context) as (_page, observation):
            pass
    assert not observation.snapshot.complete
    assert observation.snapshot.native_result.errors == ()
    assert context.actions == ["new_page", "detach", "close"]


@pytest.mark.parametrize("faults", ((), ("detach",), ("close",), ("detach", "close")))
def test_early_body_exception_and_cleanup_failures_remain_visible(faults):
    context = PublicContext(*faults)
    original = ValueError("body failed")
    with pytest.raises(BaseExceptionGroup) as caught:
        with observation_owner.PageObservation(context) as (_page, observation):
            raise original
    assert caught.value.exceptions[0] is original
    rendered = "".join(traceback.format_exception(caught.value))
    assert "incomplete observation" in rendered
    for fault in faults:
        assert fault + " failed" in rendered
    assert not observation.snapshot.complete
    assert context.actions.count("detach") == context.actions.count("close") == 1


@pytest.mark.parametrize("faults", (("detach",), ("close",), ("detach", "close"), ("screenshot", "detach", "close")))
def test_explicit_finish_exposes_lifecycle_failures_and_context_exit_cannot_ignore_them(tmp_path, faults):
    context = PublicContext(*faults)
    with pytest.raises(AssertionError, match="lifecycle errors"):
        with observation_owner.PageObservation(context) as (page, observation):
            page.emit("console", SimpleNamespace(type="error", text="original console error"))
            snapshot = observation.finish(screenshot_path=tmp_path / "failure.png")
            assert snapshot is observation.finish()
            assert not snapshot.complete
            assert snapshot.console_errors == ("original console error",)
            for fault in faults:
                assert any(fault + " failed" in error for error in snapshot.lifecycle_errors)
    assert context.actions == ["new_page", "screenshot", "detach", "close"]


def test_finalization_orders_cutoff_screenshot_detach_close_before_assertion(monkeypatch, tmp_path):
    context = PublicContext()
    original = NativeRequestObserver.cutoff
    def cutoff(observer):
        context.actions.append("cutoff")
        return original(observer)
    monkeypatch.setattr(NativeRequestObserver, "cutoff", cutoff)
    with observation_owner.PageObservation(context) as (page, observation):
        page.emit("pageerror", ValueError("page error"))
        with pytest.raises(AssertionError, match="page errors"):
            observation_owner.assert_clean_page(page, observation, screenshot_path=tmp_path / "error.png")
        assert context.actions == ["new_page", "cutoff", "screenshot", "detach", "close"]


def test_intentional_native_error_snapshot_is_immutable_and_keeps_exact_typed_failures():
    context = PublicContext()
    with observation_owner.PageObservation(context) as (_page, observation):
        context.native("Network.requestWillBeSent", requestId="request", frameId="main", loaderId="loader",
                       type="Document", request={"url": BASE + "/missing"})
        context.native("Network.responseReceived", requestId="request", frameId="main", loaderId="loader",
                       response={"status": 404, "url": BASE + "/missing"})
        snapshot = observation.finish()
        assert snapshot.complete and not snapshot.lifecycle_errors
        assert snapshot.native_result.coverage_errors == ()
        assert snapshot.native_failures[0].http_status == 404
        with pytest.raises(FrozenInstanceError):
            snapshot.complete = False
        with pytest.raises(FrozenInstanceError):
            snapshot.native_failures[0].http_status = 200
        context.native("Network.loadingFailed", requestId="request", errorText="late cleanup", canceled=False)
        assert snapshot is observation.finish()
        assert len(snapshot.failures) == 1


def test_clean_assertion_rejects_a_different_page_without_closing_it():
    context, other = PublicContext(), PublicContext()
    with observation_owner.PageObservation(context) as (page, observation):
        with pytest.raises(AssertionError, match="different page"):
            observation_owner.assert_clean_page(other.page, observation)
        observation_owner.assert_clean_page(page, observation)
    assert not other.page.closed


def test_page_closed_before_finalization_retains_native_coverage_error():
    context = PublicContext()
    with observation_owner.PageObservation(context) as (page, observation):
        page.close()
        snapshot = observation.finish()
        assert snapshot.native_result.coverage_errors
        assert snapshot.native_result.errors


@pytest.mark.parametrize("faults", ((), ("detach",), ("close",), ("detach", "close")))
@pytest.mark.parametrize("cutoff_owner", (NativeRequestObserver, RequestLedger))
def test_cutoff_failure_still_attempts_detach_and_page_close_without_fake_result(monkeypatch, faults, cutoff_owner):
    context = PublicContext(*faults)
    def cutoff(_observer):
        raise RuntimeError("cutoff failed")
    monkeypatch.setattr(cutoff_owner, "cutoff", cutoff)
    with pytest.raises(AssertionError, match="cutoff failed"):
        with observation_owner.PageObservation(context) as (_page, observation):
            snapshot = observation.finish()
            assert snapshot.native_result is None
            assert not snapshot.complete
    assert context.actions == ["new_page", "detach", "close"]
    assert any("cutoff failed" in error for error in snapshot.lifecycle_errors)


def test_page_ownership_cannot_be_reassigned_or_reentered():
    context = PublicContext()
    with observation_owner.PageObservation(context) as (page, observation):
        with pytest.raises(AttributeError):
            observation.page = PublicContext().page
        with pytest.raises(RuntimeError, match="entered twice"):
            observation.__enter__()
        observation_owner.assert_clean_page(page, observation)
    assert context.actions == ["new_page", "detach", "close"]


def test_finish_before_enter_has_no_page_or_fake_native_result():
    context = PublicContext()
    observation = observation_owner.PageObservation(context)
    with pytest.raises(RuntimeError, match="not active"):
        observation.finish()
    assert observation.snapshot is None
    assert context.actions == []


@pytest.mark.parametrize("cleanup_failure", (False, True))
def test_body_exception_after_explicit_finish_preserves_original_and_prior_cleanup_failure(cleanup_failure):
    context = PublicContext(*(("detach", "close") if cleanup_failure else ()))
    original = ValueError("body failed after finish")
    with pytest.raises(BaseExceptionGroup if cleanup_failure else ValueError) as caught:
        with observation_owner.PageObservation(context) as (_page, observation):
            snapshot = observation.finish()
            raise original
    if cleanup_failure:
        assert caught.value.exceptions[0] is original
        assert snapshot.lifecycle_errors
    else:
        assert caught.value is original
    assert context.actions == ["new_page", "detach", "close"]


def test_coverage_failure_is_typed_separately_from_transport_and_http_failures():
    context = PublicContext()
    with observation_owner.PageObservation(context) as (page, observation):
        context.native("Inspector.detached", reason="lost target")
        with pytest.raises(AssertionError, match="coverage failure"):
            observation_owner.assert_clean_page(page, observation)
        snapshot = observation.snapshot
        assert snapshot.complete and not snapshot.lifecycle_errors
        assert snapshot.native_result.coverage_errors == ("CDP session detached",)
        assert snapshot.native_failures == snapshot.http_errors == ()


def _ordinary_page_info(**changes):
    return {"targetId": "popup", "browserContextId": "context", "type": "page", **changes}


@pytest.mark.parametrize("opener", ({}, {"canAccessOpener": False}, {"openerId": "target"},
    {"openerId": "target", "openerFrameId": "main", "canAccessOpener": True},
    {"openerId": "target", "openerFrameId": "child", "canAccessOpener": False}))
def test_ordinary_page_target_is_outside_observed_frame_tree_with_or_without_opener(opener):
    flow = Flow()
    flow.child()
    flow.resource()
    info = _ordinary_page_info(**opener)
    flow.emit("Target.targetCreated", targetInfo=info)
    flow.emit("Target.targetInfoChanged", targetInfo={**info, "url": "https://example.invalid/destination"})
    flow.emit("Target.targetInfoChanged", targetInfo={**info, "attached": False})
    flow.emit("Target.targetDestroyed", targetId="popup")
    flow.nav("replacement")
    flow.fail("asset")
    flow.remove()
    flow.complete("replacement")
    result = flow.ledger.cutoff()
    assert result.errors == ()
    assert len(result.cancellations) == 1
    created = next(row for row in flow.ledger.observations if row.method == "Target.targetCreated")
    assert json.loads(created.payload)["targetInfo"] == info
    assert [row.index for row in flow.ledger.observations] == list(range(1, result.cutoff_index + 1))


@pytest.mark.parametrize("kind", ("page", "iframe", "worker"))
def test_valid_foreign_context_target_does_not_expand_observed_scope(kind):
    flow = Flow()
    flow.emit("Target.targetCreated", targetInfo=_ordinary_page_info(browserContextId="foreign", type=kind))
    flow.emit("Target.targetDestroyed", targetId="popup")
    assert flow.ledger.cutoff().errors == ()


@pytest.mark.parametrize("method", ("Target.targetCreated", "Target.targetInfoChanged"))
@pytest.mark.parametrize("changes", (
    {"targetId": ""}, {"targetId": None}, {"targetId": 7},
    {"browserContextId": ""}, {"browserContextId": None}, {"browserContextId": 7},
    {"browserContextId": False}, {"browserContextId": []},
    {"type": ""}, {"type": None}, {"type": "unknown"}, {"type": "prerender"},
    {"parentId": "target"}, {"parentId": ""}, {"parentId": None},
    {"parentFrameId": "main"}, {"parentFrameId": None},
    {"subtype": "prerender"}, {"subtype": "unknown"}, {"subtype": ""}, {"subtype": None},
    {"openerId": ""}, {"openerId": None}, {"openerId": 7},
    {"openerId": "target", "openerFrameId": None}, {"openerFrameId": "main"},
    {"canAccessOpener": "false"},
))
def test_malformed_or_contained_target_metadata_cannot_earn_page_exclusion(method, changes):
    flow = Flow()
    flow.emit(method, targetInfo=_ordinary_page_info(**changes))
    flow.emit("Target.targetDestroyed", targetId="popup")
    assert flow.ledger.cutoff().coverage_errors


@pytest.mark.parametrize("changes", ({"browserContextId": "foreign"}, {"browserContextId": 7},
                                      {"type": "worker"}, {"subtype": "prerender"}))
def test_observed_root_identity_cannot_be_replaced_by_target_metadata(changes):
    flow = Flow()
    flow.emit("Target.targetInfoChanged", targetInfo=_ordinary_page_info(targetId="target", **changes))
    assert flow.ledger.cutoff().coverage_errors


@pytest.mark.parametrize("failure", ("abort", 404, 503))
def test_popup_metadata_and_separate_completion_cannot_settle_main_request_failure(failure):
    flow = Flow()
    flow.nav("failed")
    if failure == "abort":
        flow.fail("failed")
    else:
        flow.response("failed", failure)
    flow.emit("Target.targetCreated", targetInfo=_ordinary_page_info(url=BASE + "/failed.html"))
    popup = Flow()
    popup.nav("popup-complete")
    popup.complete("popup-complete")
    assert popup.ledger.cutoff().errors == ()
    flow.emit("Target.targetInfoChanged", targetInfo=_ordinary_page_info(
        url=BASE + "/failed.html", title="completed", loaderId="failed-loader", frameId="main", status=200))
    flow.emit("Target.targetDestroyed", targetId="popup")
    result = flow.assert_failed()
    assert result.coverage_errors == ()
    assert len(flow.ledger.failures) == 1


@pytest.mark.parametrize("gap", ("iframe", "worker", "unknown", "swap", "root-loss", "session-loss"))
def test_uncovered_descendants_and_root_loss_stay_sticky_after_popup_closes(gap):
    flow = Flow()
    flow.child()
    flow.nav("aborted")
    flow.fail("aborted")
    flow.emit("Target.targetCreated", targetInfo=_ordinary_page_info(openerId="target", openerFrameId="child"))
    flow.emit("Target.targetDestroyed", targetId="popup")
    if gap in {"iframe", "worker", "unknown"}:
        flow.emit("Target.targetCreated", targetInfo=_ordinary_page_info(targetId="uncovered", type=gap))
        flow.emit("Target.targetDestroyed", targetId="uncovered")
    elif gap == "swap":
        flow.remove(reason="swap")
    elif gap == "root-loss":
        flow.emit("Target.targetDestroyed", targetId="target")
    else:
        flow.emit("Inspector.detached", reason="lost target")
    flow.nav("replacement")
    flow.complete("replacement")
    assert flow.assert_failed().coverage_errors
