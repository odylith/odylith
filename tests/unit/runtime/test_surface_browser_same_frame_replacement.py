"""Native-event controls for exact same-frame document replacement."""
import pytest

from tests.unit.runtime.test_surface_browser_request_observer import BASE, Flow


def source_flow(frame):
    flow = Flow()
    if frame == "child":
        flow.child()
    return flow, "original" if frame == "main" else "child-document"


def resource(flow, frame, document, url=BASE + "/asset.js"):
    flow.nav("asset", frame, loader=flow.requests[document]["loaderId"], kind="Script", url=url)


def transition(flow, frame, document, kind):
    if kind == "unmatched":
        flow.emit("Page.frameNavigated", frame={"id": frame, "parentId": flow.parents[frame],
                  "loaderId": flow.requests[document]["loaderId"], "url": BASE + "/alias"})
    else:
        flow.nav("intervening", frame)
        flow.complete("intervening")
        flow.commit(document)


@pytest.mark.parametrize("frame", ("main", "child"))
@pytest.mark.parametrize("order", ("normal", "finish-before-commit", "fragment-before", "history-during"))
@pytest.mark.parametrize("path", ("/legacy.html", "/.odylith/runtime/greenfield/generations/any/repository/page.html", "/original.html"))
def test_exact_same_frame_replacement_can_settle_owned_resource(frame, order, path):
    flow, document = source_flow(frame)
    resource(flow, frame, document)
    if order == "fragment-before":
        flow.emit("Page.navigatedWithinDocument", frameId=frame, url=BASE + "/original.html#fragment")
    flow.nav("replacement", frame, url=BASE + path)
    flow.fail("asset")
    failure = flow.ledger.failures[0]
    raw = flow.ledger.observations
    if order == "history-during":
        flow.emit("Page.navigatedWithinDocument", frameId=frame, url=BASE + "/different-history-path")
    flow.response("replacement")
    if order == "finish-before-commit":
        flow.finish("replacement")
    flow.commit("replacement")
    if order != "finish-before-commit":
        flow.finish("replacement")
    result = flow.ledger.cutoff()
    assert result.errors == result.coverage_errors == ()
    assert len(result.cancellations) == 1
    proof = result.cancellations[0]
    assert (proof.request_id, proof.replacement_id) == ("asset", "replacement")
    assert proof.frame_id == proof.replacement_frame_id == frame
    assert proof.loader_id == flow.requests[document]["loaderId"]
    assert proof.replacement_loader_id != proof.loader_id
    assert proof.removal_index is None
    assert proof.failure_index == failure.index < proof.commit_index
    assert flow.ledger.failures == (failure,)
    assert flow.ledger.observations[:len(raw)] == raw


@pytest.mark.parametrize("frame", ("main", "child"))
@pytest.mark.parametrize("fault", (
    "stop-before-navigation", "no-navigation", "abort-after-commit", "different-frame", "same-loader",
    "missing-response", "missing-commit", "missing-finish", "successor-404", "successor-503",
    "failed-successor", "failed-then-successful", "incomplete-then-successful", "response-then-failure",
    "source-404", "source-503", "source-http-redirect", "source-document-failed", "source-document-http-error",
    "unknown-reason", "not-canceled", "reset", "file", "different-port", "different-host", "different-scheme",
    "source-different-origin", "successor-cross-origin-hop", "successor-error-hop", "same-document-only",
    "unmatched-between", "A-to-B-to-A-between", "unmatched-before-start", "A-to-B-to-A-before-start",
    "swap", "coverage-gap", "remove-before-commit", "cutoff-before-commit",
))
def test_same_frame_resource_requires_exact_continuous_inflight_replacement(frame, fault):
    flow, document = source_flow(frame)
    if fault.endswith("before-start"):
        transition(flow, frame, document, "unmatched" if fault.startswith("unmatched") else "A-to-B-to-A")
    resource(flow, frame, document,
             "file:///tmp/asset.js" if fault == "file" else "http://localhost:9876/asset.js" if fault == "source-different-origin" else BASE + "/asset.js")
    if fault in {"source-404", "source-503"}:
        flow.response("asset", int(fault.split("-")[1]))
    if fault == "source-http-redirect":
        flow.redirect("asset", BASE + "/asset-redirect.js", 503)
    if fault == "source-document-failed":
        flow.fail(document, "net::ERR_FAILED", False)
    if fault == "source-document-http-error":
        flow.response(document, 404)
    if fault in {"stop-before-navigation", "no-navigation"}:
        flow.fail("asset")
    target = frame
    if fault == "different-frame":
        if frame == "main":
            flow.child()
        target = "child" if frame == "main" else "main"
    url = {"different-port": "http://127.0.0.1:9877/new", "different-host": "http://localhost:9876/new",
           "different-scheme": "https://127.0.0.1:9876/new"}.get(fault, BASE + "/new")
    if fault not in {"no-navigation", "same-document-only"}:
        flow.nav("replacement", target, loader=flow.requests[document]["loaderId"] if fault == "same-loader" else None, url=url)
    if fault.endswith("between"):
        transition(flow, frame, document, "unmatched" if fault.startswith("unmatched") else "A-to-B-to-A")
    if fault == "abort-after-commit":
        flow.response("replacement")
        flow.commit("replacement")
    if fault not in {"stop-before-navigation", "no-navigation"}:
        flow.fail("asset", None if fault == "unknown-reason" else "net::ERR_CONNECTION_RESET" if fault == "reset" else "net::ERR_ABORTED", fault != "not-canceled")
    if fault in {"swap", "remove-before-commit"}:
        flow.remove(frame, "swap" if fault == "swap" else "remove")
    if fault == "coverage-gap":
        flow.emit("Inspector.detached", reason="uncovered")
    if fault == "same-document-only":
        flow.emit("Page.navigatedWithinDocument", frameId=frame, url=BASE + "/new#fragment")
    if fault == "cutoff-before-commit":
        flow.ledger.cutoff()
    if fault in {"successor-cross-origin-hop", "successor-error-hop"}:
        flow.redirect("replacement", "http://localhost:9876/hop" if fault == "successor-cross-origin-hop" else BASE + "/hop", 503 if fault == "successor-error-hop" else 302)
        flow.redirect("replacement", BASE + "/back")
    if fault not in {"no-navigation", "same-document-only", "incomplete-then-successful"}:
        if fault != "missing-response":
            flow.response("replacement", int(fault.split("-")[1]) if fault in {"successor-404", "successor-503"} else 200)
        if fault != "missing-commit" and fault != "abort-after-commit":
            flow.commit("replacement")
        if fault != "missing-finish":
            flow.finish("replacement")
        if fault in {"failed-successor", "failed-then-successful", "response-then-failure"}:
            flow.fail("replacement", "net::ERR_EMPTY_RESPONSE", False)
    if fault in {"failed-then-successful", "incomplete-then-successful"}:
        flow.nav("later", frame)
        flow.complete("later")
    flow.assert_failed()
    assert any(failure.request_id == "asset" for failure in flow.ledger.failures)
