"""Single-target Chromium evidence and context-owned browser observation lifecycle."""

from dataclasses import dataclass, field
import json
from pathlib import Path
import traceback
from urllib.parse import urlparse


@dataclass(frozen=True)
class Observation:
    index: int
    method: str
    payload: str


@dataclass(frozen=True)
class Failure:
    index: int
    request_id: str
    reason: str
    url: str
    canceled: bool = False
    http_status: int | float | None = None


@dataclass(frozen=True)
class Cancellation:
    failure_index: int
    request_id: str
    replacement_id: str
    frame_id: str
    replacement_frame_id: str
    loader_id: str
    replacement_loader_id: str
    commit_index: int
    finish_index: int
    removal_index: int | None


@dataclass(frozen=True)
class LedgerResult:
    errors: tuple[str, ...]
    cancellations: tuple[Cancellation, ...]
    cutoff_index: int
    coverage_errors: tuple[str, ...] = ()


@dataclass
class _Frame:
    parent: str | None
    loader: str | None = None
    removed: int | None = None
    navigations: list[str] = field(default_factory=list)
    transitions: list[int] = field(default_factory=list)


@dataclass
class _Request:
    frame: str
    loader: str
    kind: str
    start: int
    urls: list[str]
    lineage: tuple[tuple[str, str | None], ...]
    status: int | None = None
    http_error: bool = False
    failed: bool = False
    commit: int | None = None
    finish: int | None = None


def _origin(url: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlparse(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.username is None and parsed.password is None:
            return parsed.scheme, parsed.hostname, parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
    except ValueError:
        pass
    return None


class RequestLedger:
    def __init__(self, target_id: str, browser_context_id: str):
        self.target_id, self.browser_context_id = target_id, browser_context_id
        self._events: list[Observation] = []
        self._failures: list[Failure] = []
        self._frames: dict[str, _Frame] = {}
        self._requests: dict[str, _Request] = {}
        self._gaps: list[str] = []
        self._result: LedgerResult | None = None
        if not all(isinstance(value, str) and value for value in (target_id, browser_context_id)):
            self.coverage_lost("missing native target/context identity")

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._events)

    @property
    def failures(self) -> tuple[Failure, ...]:
        return tuple(self._failures)

    def coverage_lost(self, reason: str) -> None:
        self.ingest("Observer.coverageLost", {"reason": reason})

    def seed_frame_tree(self, tree: dict) -> None:
        self.ingest("Observer.frameTree", tree)

    def _seed(self, tree: dict, parent: str | None = None) -> None:
        identifier = tree["frame"]["id"]
        if not identifier or identifier in self._frames or tree["frame"].get("parentId", parent) != parent:
            raise ValueError("duplicate or missing frame")
        self._frames[identifier] = _Frame(parent)
        for child in tree.get("childFrames", ()):
            self._seed(child, identifier)

    def _lineage(self, identifier: str) -> tuple[tuple[str, str | None], ...]:
        lineage = []
        while identifier is not None:
            if identifier in {entry[0] for entry in lineage}:
                raise ValueError("cyclic frame ownership")
            frame = self._frames[identifier]
            if frame.removed is not None:
                raise ValueError("removed frame ownership")
            lineage.append((identifier, frame.loader))
            identifier = frame.parent
        return tuple(lineage)

    def _audit_failure(self, method: str, data: dict, index: int) -> None:
        identifier = str(data.get("requestId", ""))
        request = self._requests.get(identifier)
        url = request.urls[-1] if request else ""
        if method == "Network.loadingFailed":
            reason = data.get("errorText")
            self._failures.append(Failure(index, identifier, reason if isinstance(reason, str) else "<unknown failure>", url, data.get("canceled") is True))
        response = data.get("response") if method == "Network.responseReceived" else data.get("redirectResponse") if method == "Network.requestWillBeSent" else None
        if isinstance(response, dict) and isinstance(response.get("status"), (int, float)) and response["status"] >= 400:
            response_url = response.get("url", url)
            self._failures.append(Failure(index, identifier, f"HTTP {response['status']}", response_url if isinstance(response_url, str) else "<unknown URL>", http_status=response["status"]))

    def ingest(self, method: str, params: dict) -> None:
        payload = json.dumps(params, sort_keys=True)
        data = json.loads(payload)
        index = len(self._events) + 1
        self._events.append(Observation(index, method, payload))
        if not isinstance(data, dict):
            if self._result is None:
                self._gaps.append(f"malformed event payload: {method}")
            return
        self._audit_failure(method, data, index)
        if self._result is not None:
            return  # Cleanup stays in the audit, never in the frozen observation interval.
        try:
            if method == "Observer.coverageLost":
                self._gaps.append(data["reason"])
            elif method == "Observer.frameTree":
                self._seed(data)
            elif method == "Page.frameAttached":
                identifier, parent = data["frameId"], data["parentFrameId"]
                self._lineage(parent)
                if identifier in self._frames:
                    raise ValueError("duplicate frame attachment")
                self._frames[identifier] = _Frame(parent)
            elif method == "Page.frameDetached":
                frame = self._frames[data["frameId"]]
                if frame.removed is not None:
                    raise ValueError("repeated frame detachment")
                if frame.parent is None or data.get("reason") != "remove":
                    self._gaps.append("frame swap or unknown detachment")
                frame.removed = index
            elif method == "Page.frameNavigated":
                self._commit(data["frame"], index)
            elif method == "Page.navigatedWithinDocument":
                self._lineage(data["frameId"])
            elif method == "Network.requestWillBeSent":
                self._start(data, index)
            elif method in {"Network.responseReceived", "Network.loadingFinished", "Network.loadingFailed"}:
                self._network(method, data, index)
            elif method in {"Target.targetCreated", "Target.targetInfoChanged"}:
                self._target_info(data["targetInfo"])
            elif method == "Target.targetDestroyed" and data["targetId"] == self.target_id:
                self._gaps.append("observed target destroyed")
            elif method == "Inspector.detached":
                self._gaps.append("CDP session detached")
        except (KeyError, ValueError, TypeError, AttributeError):
            self._gaps.append(f"malformed or unknown ownership: {method}")

    def _target_info(self, info: dict) -> None:
        identifier, context, kind = (info[key] for key in ("targetId", "browserContextId", "type"))
        if not all(isinstance(value, str) and value for value in (identifier, context, kind)):
            raise ValueError("missing native target/context identity")
        if identifier == self.target_id and (context != self.browser_context_id or kind != "page"):
            raise ValueError("observed target identity changed")
        if context != self.browser_context_id:
            return
        if kind != "page" or any(key in info for key in ("parentId", "parentFrameId", "subtype")):
            raise ValueError("uncovered target in observed context")
        for key in ("openerId", "openerFrameId"):
            if key in info and not (isinstance(info[key], str) and info[key]):
                raise ValueError("malformed opener identity")
        if "openerFrameId" in info and "openerId" not in info:
            raise ValueError("opener frame without opener target")
        if "canAccessOpener" in info and not isinstance(info["canAccessOpener"], bool):
            raise ValueError("malformed opener access")
        # A distinct ordinary page is outside this page's descendant-frame scope.
        # Opener metadata is not containment and supplies no transport evidence.

    def _start(self, data: dict, index: int) -> None:
        identifier, frame_id, loader, kind = (data[key] for key in ("requestId", "frameId", "loaderId", "type"))
        if not all(isinstance(value, str) and value for value in (identifier, frame_id, loader, kind)):
            raise ValueError("missing native identity")
        url = data["request"]["url"]
        if not isinstance(url, str):
            raise ValueError("missing URL")
        request = self._requests.get(identifier)
        if request is not None:
            if (request.frame, request.loader, request.kind) != (frame_id, loader, kind) or "redirectResponse" not in data or request.failed or request.finish is not None:
                raise ValueError("invalid repeated request identity")
            status = data["redirectResponse"]["status"]
            if not isinstance(status, (int, float)):
                raise ValueError("invalid redirect status")
            request.http_error |= status >= 400
            request.urls.append(url)
            request.status = None
            return
        lineage = self._lineage(frame_id)
        request = _Request(frame_id, loader, kind, index, [url], lineage)
        self._requests[identifier] = request
        if "redirectResponse" in data:
            raise ValueError("redirect without original request")
        if kind == "Document":
            self._frames[frame_id].navigations.append(identifier)
        elif self._frames[frame_id].loader != loader:
            raise ValueError("resource without observed committed loader")

    def _network(self, method: str, data: dict, index: int) -> None:
        request = self._requests[data["requestId"]]
        if method == "Network.responseReceived":
            if (data["frameId"], data["loaderId"]) != (request.frame, request.loader):
                raise ValueError("response ownership mismatch")
            status = data["response"]["status"]
            if not isinstance(status, (int, float)):
                raise ValueError("invalid response status")
            request.status = status
            request.http_error |= status >= 400
        elif method == "Network.loadingFailed":
            request.failed = True
        else:
            request.finish = index

    def _commit(self, data: dict, index: int) -> None:
        identifier, loader = data["id"], data["loaderId"]
        frame = self._frames[identifier]
        self._lineage(identifier)
        if not isinstance(loader, str) or not loader or data.get("parentId") != frame.parent:
            raise ValueError("invalid committed frame identity")
        candidates = [request for request in self._requests.values() if request.frame == identifier and request.loader == loader and request.kind == "Document"]
        if len(candidates) > 1:
            raise ValueError("ambiguous loader identity")
        if candidates and candidates[0].commit is None and frame.loader != loader:
            candidates[0].commit = index
        frame.loader = loader
        frame.transitions.append(index)  # Native unmatched commits are barriers, not synthetic success.

    def _document(self, frame_id: str, loader: str | None) -> _Request | None:
        return next((request for request in self._requests.values() if request.frame == frame_id and request.loader == loader and request.kind == "Document" and request.commit is not None), None)

    def _next_navigation(self, frame_id: str, previous: _Request) -> tuple[str, _Request] | None:
        identifiers = self._frames[frame_id].navigations
        for position, identifier in enumerate(identifiers[:-1]):
            if self._requests[identifier] is previous:
                successor = identifiers[position + 1]
                return successor, self._requests[successor]
        return None

    @staticmethod
    def _same_origin(request: _Request, origin: tuple[str, str, int]) -> bool:
        return all(_origin(url) == origin for url in request.urls)

    def _ready(self, request: _Request, origin: tuple[str, str, int]) -> bool:
        return (request.commit is not None and request.finish is not None
                and request.status is not None and 200 <= request.status < 300
                and not request.failed and not request.http_error and self._same_origin(request, origin))

    def _qualify(self, failure: Failure) -> Cancellation | None:
        source = self._requests.get(failure.request_id)
        origin = _origin(failure.url)
        if source is None or origin is None or failure.reason != "net::ERR_ABORTED" or not failure.canceled or source.http_error or not self._same_origin(source, origin):
            return None
        # Seeded topology cannot lend document or origin authority to a resource.
        for frame_id, loader in source.lineage:
            if frame_id == source.frame and source.kind == "Document" and loader is None:
                continue
            document = self._document(frame_id, loader)
            if document is None or document.commit >= source.start or document.http_error or document.failed or not self._same_origin(document, origin):
                return None
        candidates = []
        if source.kind == "Document":
            if source.commit is not None:
                return None
            next_navigation = self._next_navigation(source.frame, source)
            if next_navigation is not None:
                identifier, successor = next_navigation
                if successor.loader != source.loader and self._ready(successor, origin):
                    transitions = self._frames[source.frame].transitions
                    if not any(source.start < event < successor.commit for event in transitions):
                        candidates.append((identifier, successor, None))
        else:
            removal = self._frames[source.frame].removed
            for position, (frame_id, loader) in enumerate(source.lineage[1:], start=1):
                document = self._document(frame_id, loader)
                next_navigation = self._next_navigation(frame_id, document)
                if next_navigation is None:
                    continue
                identifier, successor = next_navigation
                if removal is not None and self._ready(successor, origin):
                    in_flight = successor.start < failure.index < successor.commit
                    departing = successor.start < removal < successor.commit
                    barrier = any(document.commit < event < successor.commit for event in self._frames[frame_id].transitions)
                    # Final loader equality cannot prove continuity across A-to-B-to-A commits.
                    interrupted = any(source.start < event < removal
                                      for lower_id, _ in source.lineage[:position]
                                      for event in self._frames[lower_id].transitions)
                    if in_flight and departing and not barrier and not interrupted:
                        candidates.append((identifier, successor, removal))
        if not candidates:
            return None
        identifier, successor, removal = candidates[0]
        return Cancellation(failure.index, failure.request_id, identifier, source.frame, successor.frame,
                            source.loader, successor.loader, successor.commit, successor.finish, removal)

    def cutoff(self) -> LedgerResult:
        if self._result is None:
            cancellations, errors = [], []
            for failure in self._failures:
                cancellation = None if self._gaps else self._qualify(failure)
                if cancellation is None:
                    errors.append(f"{failure.request_id} {failure.url} {failure.reason}".strip())
                else:
                    cancellations.append(cancellation)
            errors.extend(f"coverage failure: {reason}" for reason in self._gaps)
            self._result = LedgerResult(tuple(errors), tuple(cancellations), len(self._events), tuple(self._gaps))
        return self._result


class NativeRequestObserver:
    """Public synchronous CDP adapter; PageObservation owns its finalization."""

    EVENTS = ("Page.frameAttached", "Page.frameDetached", "Page.frameNavigated", "Page.navigatedWithinDocument",
              "Network.requestWillBeSent", "Network.responseReceived", "Network.loadingFinished", "Network.loadingFailed",
              "Target.targetCreated", "Target.targetInfoChanged", "Target.targetDestroyed", "Inspector.detached")

    def __init__(self, page):
        self.session = page.context.new_cdp_session(page)
        try:
            info = self.session.send("Target.getTargetInfo")["targetInfo"]
            if info["type"] != "page":
                raise ValueError("only a page target is covered")
            self.ledger = RequestLedger(info["targetId"], info["browserContextId"])
            for event in self.EVENTS:
                self.session.on(event, lambda params, event=event: self.ledger.ingest(event, params))
            page.on("close", lambda _: self.ledger.coverage_lost("page closed"))
            page.on("crash", lambda _: self.ledger.coverage_lost("page crashed"))
            self.session.send("Page.enable")
            self.ledger.seed_frame_tree(self.session.send("Page.getFrameTree")["frameTree"])
            self.session.send("Network.enable")
            self.session.send("Target.setDiscoverTargets", {"discover": True})
        except Exception as setup_error:
            try:
                self.session.detach()
            except Exception as detach_error:
                raise ExceptionGroup("CDP initialization and detach failed", [setup_error, detach_error]) from setup_error
            raise

    def cutoff(self) -> LedgerResult:
        return self.ledger.cutoff()

    def close(self) -> None:
        if self.ledger._result is None:
            self.ledger.coverage_lost("adapter closed before cutoff")
            self.ledger.cutoff()
        try:
            self.session.detach()
        except Exception:
            self.ledger.coverage_lost("explicit CDP detach failed")
            raise


@dataclass(frozen=True)
class HttpError:
    status: int
    url: str


@dataclass(frozen=True)
class ObservationSnapshot:
    console_errors: tuple[str, ...]
    page_errors: tuple[str, ...]
    http_errors: tuple[HttpError, ...]
    native_result: LedgerResult | None
    native_failures: tuple[Failure, ...]
    observations: tuple[Observation, ...]
    failures: tuple[Failure, ...]
    complete: bool
    lifecycle_errors: tuple[str, ...]

    @property
    def errors(self) -> tuple[str, ...]:
        groups = (("console errors", self.console_errors), ("page errors", self.page_errors),
                  ("http error responses", self.http_errors),
                  ("request failures", self.native_result.errors if self.native_result else ("native cutoff unavailable",)),
                  ("lifecycle errors", self.lifecycle_errors))
        errors = tuple(f"{label}: {values}" for label, values in groups if values)
        return errors if self.complete else errors + ("incomplete observation",)


class ObservationFailure(AssertionError):
    def __init__(self, snapshot: ObservationSnapshot):
        self.snapshot = snapshot
        super().__init__("\n".join(snapshot.errors))


class PageObservation:
    """Own exactly one page; explicit finish is the only complete observation boundary."""

    def __init__(self, context):
        self.context, self._page, self._native = context, None, None
        self._console, self._page_errors, self._http = [], [], []
        self._snapshot: ObservationSnapshot | None = None
        self._finishing = False

    @property
    def snapshot(self) -> ObservationSnapshot | None:
        return self._snapshot

    @property
    def page(self):
        return self._page

    def __enter__(self):
        if self.page is not None:
            raise RuntimeError("page observation cannot be entered twice")
        self._page = self.context.new_page()
        try:
            self.page.on("console", self._on_console)
            self.page.on("pageerror", lambda error: self._page_errors.append(str(error)))
            self.page.on("response", self._on_response)
            self._native = NativeRequestObserver(self.page)
        except BaseException as setup_error:
            try:
                self.page.close()
            except BaseException as close_error:
                raise BaseExceptionGroup("observation setup and page cleanup failed", [setup_error, close_error]) from None
            raise
        return self.page, self

    def _on_console(self, message):
        if message.type == "error":
            self._console.append(message.text)

    def _on_response(self, response):
        url = str(getattr(response, "url", "") or "")
        try:
            parsed = urlparse(url)
            local = parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        except ValueError:
            local = False
        if local:
            status = int(getattr(response, "status", 0) or 0)
            if status >= 400:
                self._http.append(HttpError(status, url))

    def finish(self, *, screenshot_path: Path | None = None) -> ObservationSnapshot:
        return self._finish(complete=True, screenshot_path=screenshot_path)

    def _finish(self, *, complete: bool, screenshot_path: Path | None = None) -> ObservationSnapshot:
        if self._snapshot is not None:
            return self._snapshot
        if self._native is None or self._finishing:
            raise RuntimeError("observation is not active or finalization is already in progress")
        self._finishing = True
        lifecycle_errors, native_result = [], None
        try:
            native_result = self._native.cutoff()
        except BaseException:
            lifecycle_errors.append("native cutoff: " + traceback.format_exc())
        console, page_errors, http = tuple(self._console), tuple(self._page_errors), tuple(self._http)
        failures = self._native.ledger.failures
        qualified = {proof.failure_index for proof in native_result.cancellations} if native_result else set()
        unresolved = tuple(failure for failure in failures if failure.index not in qualified)
        if screenshot_path is not None and (console or page_errors or http or native_result is None or native_result.errors or not complete):
            try:
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(screenshot_path), full_page=True)
            except BaseException:
                lifecycle_errors.append("failure screenshot: " + traceback.format_exc())
        # A failed ledger cutoff cannot be retried as a prerequisite for releasing its session.
        detach = self._native.close if native_result is not None else self._native.session.detach
        for label, action in (("native detach", detach), ("page close", self.page.close)):
            try:
                if label != "page close" or not self.page.is_closed():
                    action()
            except BaseException:
                lifecycle_errors.append(label + ": " + traceback.format_exc())
        self._snapshot = ObservationSnapshot(console, page_errors, http, native_result, unresolved,
            self._native.ledger.observations, self._native.ledger.failures,
            complete and not lifecycle_errors, tuple(lifecycle_errors))
        return self._snapshot

    def __exit__(self, error_type, error, tb):
        snapshot = self._snapshot or self._finish(complete=False)
        if not snapshot.complete or snapshot.lifecycle_errors:
            if isinstance(error, ObservationFailure) and error.snapshot is snapshot:
                return False
            failure = ObservationFailure(snapshot)
            if error is not None:
                raise BaseExceptionGroup("page body and observation finalization failed", [error, failure]) from None
            raise failure
        return False


def assert_clean_page(page, observation: PageObservation, *, screenshot_path: Path | None = None) -> None:
    if page is not observation.page:
        raise AssertionError("observation belongs to a different page")
    snapshot = observation.finish(screenshot_path=screenshot_path)
    if snapshot.errors:
        raise ObservationFailure(snapshot)
