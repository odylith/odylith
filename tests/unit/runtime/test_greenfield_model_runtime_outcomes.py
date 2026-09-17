"""Public runtime failures remain distinct from rejected product meaning."""

import json
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals_cli as cli
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture
from tests.unit.runtime.greenfield_model_authoring_fixtures import StructuredAuthoringProvider
from tests.unit.runtime.test_greenfield_model_path_custody import _response, _source


class FailureProvider(StructuredAuthoringProvider):
    def __init__(self, response, failure, clock):
        super().__init__(response)
        self.failure = failure
        self.clock = clock

    def generate_structured(self, *, request):
        response = super().generate_structured(request=request)
        self.last_failure_detail = "PRIVATE_DIAGNOSTIC /private/provider-key"
        if self.failure == "exception_timeout":
            raise TimeoutError(self.last_failure_detail)
        if self.failure in {"timeout", "unavailable"}:
            self.last_failure_code = self.failure
            return None
        if self.failure == "misleading_timeout":
            self.last_failure_code = "invalid_response"
            self.last_failure_detail += " timeout"
            return None
        if self.failure == "stale_timeout":
            self.last_failure_code = "timeout"
            return {"invalid": "candidate"}
        if self.failure == "late":
            self.clock.value += request.timeout_seconds + 0.01
        return response


def _snapshot(root):
    return {
        str(p.relative_to(root)): ("file", p.read_bytes()) if p.is_file() else ("directory", None)
        for p in root.rglob("*")
    }


def _run(tmp_path, monkeypatch, capsys, *, role, failure, command, output_format):
    activate_greenfield_baseline_fixture(tmp_path)
    before = _snapshot(tmp_path)
    clock = SimpleNamespace(value=0.0)
    monkeypatch.setattr(cli, "time", SimpleNamespace(perf_counter=lambda: clock.value))
    author = FailureProvider(_response(_source()), failure if role == "author" else "", clock)
    reviewer = FailureProvider({"admissible": True, "issues": []}, failure if role == "reviewer" else "", clock)
    if failure == "malformed":
        (author if role == "author" else reviewer).response = None
    if failure == "denied":
        reviewer.response = {"admissible": False, "issues": [{"path": "facts", "reason": "Unsupported meaning"}]}
    providers = [author, reviewer]
    setup_roles = []

    def resolve(*_args, **_kwargs):
        setup_roles.append(len(setup_roles))
        if len(setup_roles) == (1 if role == "author" else 2):
            if failure == "absent":
                return None
            if failure == "setup_timeout":
                raise TimeoutError("PRIVATE_DIAGNOSTIC /private/provider-key")
        return providers[len(setup_roles) - 1]

    monkeypatch.setattr(cli.odylith_reasoning, "provider_from_config", resolve)
    code = cli.main([command, "--repo-root", str(tmp_path), "--prompt", _source(), "--format", output_format])
    output = capsys.readouterr()
    assert code == 2
    assert output.err == ""
    assert "PRIVATE_DIAGNOSTIC" not in output.out
    assert "/private/provider-key" not in output.out
    assert "CONFIRM" not in output.out
    assert _snapshot(tmp_path) == before
    no_dispatch = failure in {"absent", "setup_timeout"}
    assert author.calls == (0 if no_dispatch and role == "author" else 1)
    assert reviewer.calls == (0 if role == "author" or no_dispatch else 1)
    return output.out


@pytest.mark.parametrize("command", ["propose", "compile-transaction"])
@pytest.mark.parametrize("output_format", ["text", "json"])
@pytest.mark.parametrize("role", ["author", "reviewer"])
@pytest.mark.parametrize("failure", ["timeout", "exception_timeout", "late", "unavailable", "absent", "setup_timeout"])
def test_public_model_runtime_outcome(tmp_path, monkeypatch, capsys, command, output_format, role, failure):
    output = _run(tmp_path, monkeypatch, capsys, role=role, failure=failure, command=command, output_format=output_format)
    expected = "MODEL_UNAVAILABLE_NO_WRITE" if failure in {"unavailable", "absent"} else "MODEL_TIMEOUT_NO_WRITE"
    if output_format == "json":
        payload = json.loads(output)
        assert payload["mode"] == "error"
        assert payload["outcome"] == {"kind": "environment", "code": expected}
        output = payload["error"]
    assert "no records were created" in output
    assert "try again" in output.casefold()
    assert ("unavailable" if failure in {"unavailable", "absent"} else "time window") in output


@pytest.mark.parametrize("role,failure", [("author", "malformed"), ("reviewer", "malformed"), ("reviewer", "denied")])
def test_semantic_failure_is_not_reported_as_environment(tmp_path, monkeypatch, capsys, role, failure):
    output = _run(tmp_path, monkeypatch, capsys, role=role, failure=failure, command="propose", output_format="json")
    payload = json.loads(output)
    assert payload["mode"] == "error"
    assert "outcome" not in payload


@pytest.mark.parametrize("role", ["author", "reviewer"])
@pytest.mark.parametrize("failure", ["misleading_timeout", "stale_timeout"])
def test_diagnostics_and_stale_codes_do_not_classify_candidate_meaning(tmp_path, monkeypatch, capsys, role, failure):
    output = _run(tmp_path, monkeypatch, capsys, role=role, failure=failure, command="propose", output_format="json")
    assert "outcome" not in json.loads(output)
