"""Detached bridge contracts; synthetic grades are never public qualification."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
import sys
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_public_qualification as public
from greenfield_evaluation_contract import published_structural_floors, _frozen_floor_issues
from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import (
    begin_retained_case_evidence, finalize_retained_case_evidence,
    prepare_retained_evidence_output_dir, record_retained_case_json,
    record_retained_case_text, sha256_file, write_retained_evidence_manifest,
)
from greenfield_matrix_types import GreenfieldArtifactCounts, GreenfieldMatrixResult, GreenfieldQualityVerdict
from greenfield_model_profile_proof import model_profile_release_proof, unavailable_provider_proof_issues
from greenfield_model_profiles import RESCUE_PROFILE_ID, UNAVAILABLE_PROVIDER_PROFILE
from greenfield_onboarding_quality_scorecard import build_onboarding_quality_scorecard
from greenfield_onboarding_review import build_onboarding_review_sidecar, finalize_onboarding_review
from greenfield_relation_fidelity import canonical_evidence_sha256 as digest
from greenfield_semantic_case_score import PUBLIC_SOURCE_MODE, load_source_predicate_evidence
from greenfield_semantic_release_score import evaluate_semantic_release as actual_semantic_score
from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import WHOLE_JOURNEY_ELAPSED_SCOPE
from tests.unit.install.test_greenfield_matrix_clarification_profile_proof import (
    _authored_profile_evidence, _profile_evidence, _result,
)
from tests.unit.install.test_greenfield_onboarding_review import (
    CASE_ID, TRANSACTION_HASH, _base_result, _published_case, _review_package,
)
from tests.unit.install.test_greenfield_release_source_duty_custody import _current_snapshot
from tests.unit.install.test_greenfield_source_predicate_evaluation import _save, _declare, _bind, _audit
from tests.unit.install.test_greenfield_semantic_release_score import _case


def _saved_result(case, *, profile, snapshot=None, receipt=None, scores=None):
    prototype = _result(profile_evidence=profile, expectation=case.expectation)
    prototype.evidence['case'].update(id=case.case_id)
    quality = GreenfieldQualityVerdict(True, (), {}, scores or {}, 10, (), prototype.quality.score_basis)
    result = GreenfieldMatrixResult(name=case.name, status='passed', create_seconds=1.0,
        proposal_seconds=profile['stage_observation']['elapsed_seconds'],
        counts=GreenfieldArtifactCounts(), quality=quality, evidence=prototype.evidence)
    if snapshot is not None:
        result.evidence['preconfirm_dry_run'] = {**receipt,
            'semantic_snapshot': deepcopy(snapshot), 'semantic_snapshot_sha256': digest(snapshot)}
    return result


def _scorecard(base, results, profile):
    return build_onboarding_quality_scorecard(results=results, browser_proof=base['browser_surface_proof'],
        platform_leakage_proof=base['platform_domain_leakage_proof'], metamorphic_output=base['metamorphic_output'],
        model_profile_proof=profile, unavailable_provider_proof=base['unavailable_provider_proof'],
        commit_recovery_proof=base['commit_recovery_proof'])


@pytest.fixture
def saved_public(tmp_path, monkeypatch):
    original, snapshot = _current_snapshot(tmp_path)
    case_rows = [{'id': CASE_ID, 'name': 'public commit', 'prompt': original.prompt,
        'required_terms': ['Harbor'], 'leakage_terms': ['Harbor'], 'expectation': 'transaction_committed'},
        {'id': 'public-clarify', 'name': 'public clarify', 'prompt': 'A complete task is materially ambiguous.',
         'required_terms': ['task'], 'leakage_terms': ['task'], 'expectation': 'clarification_required'}]
    cases_ref = _save(tmp_path / 'source-cases.json', {'cases': case_rows})
    cases = load_case_file(Path(cases_ref['path']))
    declaration = _declare(cases[0], cases_ref['sha256'])
    declaration['cases'].extend(_declare(cases[1], cases_ref['sha256'])['cases'])
    declaration['case_count'] = 2
    source_ref = _save(tmp_path / 'source.json', declaration)
    repo = tmp_path / 'repos' / 'commit'
    receipt = _published_case(repo=repo, staged_root=tmp_path / 'stage', transaction_hash=TRANSACTION_HASH)
    root = prepare_retained_evidence_output_dir(output_dir=tmp_path / 'retained', temp_parent=tmp_path / 'repos')
    placeholder_ref = _save(tmp_path / 'unused.json', {})
    scores = _base_result(retained_manifest_path=Path(placeholder_ref['path']),
        transaction_hash=TRANSACTION_HASH)['results'][0]['quality']['scores']
    commit = _saved_result(cases[0], profile=_authored_profile_evidence(), snapshot=snapshot,
        receipt=receipt, scores=scores)
    commit.evidence['case'].update(prompt_sha256=declaration['cases'][0]['prompt_sha256'],
        provenance={'source_artifact_sha256': cases_ref['sha256']})
    commit = replace(commit, commit_manifest_summary={
        'product_create_transaction': {'transaction_hash': TRANSACTION_HASH}})
    clarify = _saved_result(cases[1], profile=_profile_evidence())
    clarify.evidence['clarification']['question'] = declaration['cases'][1]['expected_clarification']['question']
    control_case = _case('public-control', expectation='clarification_required')
    control = _saved_result(control_case, profile=_profile_evidence(RESCUE_PROFILE_ID))
    manifests = []
    for case, result in zip(cases, (commit, clarify)):
        retained_case = begin_retained_case_evidence(evidence_root=root, case_id=case.case_id)
        record_retained_case_text(retained_case, 'commands/propose.stdout', 'synthetic fixture output')
        record_retained_case_json(retained_case, 'semantic/dry-run-receipt.v2.json',
            result.evidence.get('preconfirm_dry_run', {'mode': 'clarification_required'}))
        if case.expectation == 'transaction_committed':
            record_retained_case_text(retained_case, 'browser/project-desktop.png', 'synthetic pixels')
        manifests.append(finalize_retained_case_evidence(case=retained_case, repo_root=repo,
            result_payload=result.to_dict()))
    retained = write_retained_evidence_manifest(root=root, expected_case_ids=tuple(case.case_id for case in cases))
    base = _base_result(retained_manifest_path=retained, transaction_hash=TRANSACTION_HASH)
    base.update(status='failed', results=[commit.to_dict(), clarify.to_dict()],
        semantic_release={'status': 'not_requested', 'passed': True})
    base['unavailable_provider_proof'] = {
        'version': 'odylith.greenfield.post-receipt-provider-isolation-proof.v2', 'status': 'passed',
        'profile_id': UNAVAILABLE_PROVIDER_PROFILE, 'semantic_authority': 'active_host_single_authority',
        'runtime_provider_mode': 'disabled', 'post_receipt_provider_invocations': 0,
        'proposal_seconds': 10.0, 'whole_journey_seconds': 40.0, 'returncode': 0, 'failure_detail': '',
        'no_write': {'before_record_count': 0, 'after_record_count': 1,
            'changed_records': ['.odylith/runtime/greenfield/pending/synthetic-transaction.json'],
            'staged_transaction_present': True, 'write_audit_active': True, 'write_attempts': [],
            'subprocess_attempts': [], 'write_audit_error': ''}, 'issues': []}
    base['campaign']['completed_case_count'] = 2
    base['lower_capability_control_proof'].update(results=[control.to_dict()], case_count=1)
    results = (commit, clarify, control)
    base['model_profile_proof'] = model_profile_release_proof(results, require_complete=True)
    base['onboarding_quality_scorecard'] = _scorecard(base, results, base['model_profile_proof'])
    base_ref = _save(tmp_path / 'base.json', base)
    review = _review_package(base_path=Path(base_ref['path']), retained_manifest_path=retained,
        case_manifest_path=manifests[0])
    review['cases'][0]['source'].update(prompt_sha256=declaration['cases'][0]['prompt_sha256'],
        confirmed_intent_sha256='', source_artifact_sha256=cases_ref['sha256'])
    review_ref = _save(tmp_path / 'onboarding-review.json', review)
    bindings, audits = [], []
    for case, result, annotation in zip(cases, (commit, clarify), declaration['cases']):
        saved_snapshot = result.evidence.get('preconfirm_dry_run', {}).get('semantic_snapshot', {})
        binding, _, _ = _bind(case, annotation, saved_snapshot, result.evidence.get('clarification'))
        binding['transaction_hash'] = result.evidence.get('preconfirm_dry_run', {}).get('transaction_hash', '')
        bindings.append(binding); audits.append(_audit(binding))
    binding_ref = _save(tmp_path / 'bindings.json', {'version': PUBLIC_SOURCE_MODE + '.bindings.v1',
        'public_split': 'disclosed-public-live-subset', 'source_predeclaration_sha256': source_ref['sha256'],
        'output_sha256': base_ref['sha256'], 'binder_identity': 'synthetic-test-binder', 'cases': bindings})
    record_ref = _save(tmp_path / 'semantic-review-record.json', {'version': PUBLIC_SOURCE_MODE + '.review-record.v1',
        'source_predeclaration_sha256': source_ref['sha256'], 'observed_bindings_sha256': binding_ref['sha256'],
        'output_sha256': base_ref['sha256'], 'retained_manifest_sha256': sha256_file(retained),
        'reviewer_sha256': digest(review['reviewer']), 'review_context_id': review['reviewer']['review_context_id'],
        'reviewed_cases_sha256': digest(audits)})
    audit_ref = _save(tmp_path / 'semantic-audit.json', {'version': PUBLIC_SOURCE_MODE + '.audit.v1',
        'source_predeclaration_sha256': source_ref['sha256'], 'observed_bindings_sha256': binding_ref['sha256'],
        'output_sha256': base_ref['sha256'], 'retained_manifest_sha256': sha256_file(retained),
        'review_record_sha256': record_ref['sha256'], 'reviewer': review['reviewer'], 'cases': audits})
    config = {'mode': PUBLIC_SOURCE_MODE, 'predeclaration': source_ref, 'source_cases': cases_ref,
        'observed_bindings': binding_ref, 'independent_audit': audit_ref, 'output': base_ref,
        'retained_manifest': {'path': str(retained), 'sha256': sha256_file(retained)}, 'review_record': record_ref}
    bound = _bound_evidence(tmp_path, base, config, review['reviewer'])
    def contract_grade(**kwargs):
        # Isolate bridge readiness from grading. Real R2 custody still runs, and
        # actual scoring is separately tested to refuse this undersized fixture.
        assert kwargs['floors'] == published_structural_floors()
        assert kwargs['release_required_slices'] == public.release_slice_contract()
        _, _, issues = load_source_predicate_evidence(configuration=kwargs['source_predicate_evidence'],
            cases=kwargs['cases'], results=kwargs['results'])
        return {'status': 'failed' if issues else 'passed', 'passed': not issues,
            'issues': list(issues), 'synthetic_contract_grade': True}
    monkeypatch.setattr(public, 'evaluate_semantic_release', contract_grade)
    return {'base': base, 'base_ref': base_ref, 'retained': retained, 'review_ref': review_ref,
        'review': review, 'config': config, 'bound': bound, 'results': results, 'cases': cases}


def _bound_evidence(tmp_path, base, config, reviewer):
    identities = {name: config[ref]['sha256'] for name, ref in (
        ('source_predeclaration_sha256', 'predeclaration'), ('source_cases_sha256', 'source_cases'),
        ('output_sha256', 'output'), ('retained_manifest_sha256', 'retained_manifest'))}
    cases = [{'case_id': row['evidence']['case']['id'], 'result_sha256': digest(row),
        'stage_sha256': digest(row['evidence']['model_profile']['stage_observation']),
        'elapsed_seconds': row['evidence']['model_profile']['stage_observation']['whole_journey_seconds']}
        for row in (*base['results'], *base['lower_capability_control_proof']['results'])]
    measurement_ref = _save(tmp_path / 'timing-measurements.json', {
        'version': public.PUBLIC_MEASURED_BOUND_VERSION + '.measurements.v1',
        'public_split': 'disclosed-public-live-subset', **identities,
        'elapsed_scope': WHOLE_JOURNEY_ELAPSED_SCOPE, 'cases': cases})
    decision_ref = _save(tmp_path / 'timing-decision.json', {
        'version': public.PUBLIC_MEASURED_BOUND_VERSION + '.decision.v1', 'status': 'approved',
        'qualification_scope': public.PUBLIC_MEASURED_BOUND_SCOPE, 'consumer_timing_custody': 'unproved',
        **identities, 'measurements_sha256': measurement_ref['sha256'], 'finite_bound_seconds': 660.0,
        'elapsed_scope': WHOLE_JOURNEY_ELAPSED_SCOPE, 'reviewer': reviewer,
        'rationale': 'Synthetic finite-decision fixture; no actual public timing qualification.'})
    record_ref = _save(tmp_path / 'timing-review-record.json', {
        'version': public.PUBLIC_MEASURED_BOUND_VERSION + '.review-record.v1', **identities,
        'measurements_sha256': measurement_ref['sha256'], 'decision_sha256': decision_ref['sha256'],
        'reviewer_sha256': digest(reviewer), 'review_context_id': reviewer['review_context_id'],
        'measurement_cases_sha256': digest(cases), 'verdict': 'approved'})
    return {'measurements': measurement_ref, 'decision': decision_ref, 'review_record': record_ref}


def _finalize(saved, output):
    return finalize_onboarding_review(base_result_path=Path(saved['base_ref']['path']),
        retained_manifest_path=saved['retained'], review_path=Path(saved['review_ref']['path']),
        output_path=output, public_source_evidence=saved['config'], whole_journey_bound_evidence=saved['bound'])


def _replace_saved_base(saved, base, *, recompute_scorecard=False):
    """Restamp synthetic review refs so controls reach the actual failed gate."""
    rows = (*public.typed_saved_matrix_results(base['results']),
        *public.typed_saved_matrix_results(base['lower_capability_control_proof']['results']))
    if recompute_scorecard:
        base['onboarding_quality_scorecard'] = _scorecard(base, rows, base['model_profile_proof'])
    saved['base'] = base
    saved['base_ref'] = _save(Path(saved['base_ref']['path']), base)
    saved['config']['output'] = saved['base_ref']
    for key in ('observed_bindings', 'review_record', 'independent_audit'):
        ref = saved['config'][key]
        value = json.loads(Path(ref['path']).read_text())
        value['output_sha256'] = saved['base_ref']['sha256']
        if key != 'observed_bindings':
            value['observed_bindings_sha256'] = saved['config']['observed_bindings']['sha256']
        if key == 'independent_audit':
            value['review_record_sha256'] = saved['config']['review_record']['sha256']
        saved['config'][key] = _save(Path(ref['path']), value)
    saved['review']['base_result_sha256'] = saved['base_ref']['sha256']
    saved['review_ref'] = _save(Path(saved['review_ref']['path']), saved['review'])
    saved['bound'] = _bound_evidence(Path(saved['base_ref']['path']).parent,
        base, saved['config'], saved['review']['reviewer'])
    saved['results'] = rows


def test_owned_missing_reports_advance_only_through_detached_contract_evidence(saved_public, tmp_path):
    saved = saved_public
    original_bytes = {ref['path']: Path(ref['path']).read_bytes() for ref in (
        *[ref for ref in saved['config'].values() if isinstance(ref, dict)], *saved['bound'].values(), saved['review_ref'])}
    result = _finalize(saved, tmp_path / 'sidecar.json')
    assert result['status'] == 'passed', result
    assert result['public_qualification']['original_failure_authenticated'] is True
    assert result['public_qualification']['consumer_timing_custody'] == 'unproved'
    assert result['public_qualification']['published_floors'] == published_structural_floors()
    assert all(Path(path).read_bytes() == raw for path, raw in original_bytes.items())
    assert json.loads(Path(saved['base_ref']['path']).read_text())['status'] == 'failed'
    assert all(row.evidence['model_profile']['stage_observation']['whole_journey_bound_status']
        == 'diagnostic_unqualified' for row in saved['results'])
    with pytest.raises(FileExistsError): _finalize(saved, tmp_path / 'sidecar.json')
    with pytest.raises(RuntimeError, match='detached'): _finalize(saved, Path(saved['bound']['decision']['path']))


def test_actual_public_scorer_cannot_qualify_undersized_contract_fixture(saved_public, tmp_path, monkeypatch):
    monkeypatch.setattr(public, 'evaluate_semantic_release', actual_semantic_score)
    result = _finalize(saved_public, tmp_path / 'unqualified.json')
    assert result['status'] == 'failed'
    assert result['public_qualification']['semantic_release']['passed'] is False


@pytest.mark.parametrize('name', ['measurements', 'decision', 'review_record'])
def test_missing_or_changed_bound_ref_never_qualifies(saved_public, name):
    bound = deepcopy(saved_public['bound']); Path(bound[name]['path']).write_text('{}\n')
    proof = model_profile_release_proof(saved_public['results'], require_complete=True,
        whole_journey_bound_evidence=bound, public_source_evidence=saved_public['config'])
    assert proof['status'] == 'failed' and proof['whole_journey_release_bound_seconds'] is None


@pytest.mark.parametrize('control', ['bare_number', 'missing_record', 'rejected', 'consumer_relabel',
    'too_large', 'not_finite', 'below_observation', 'changed_scope', 'forged_reviewer', 'missing_case', 'missing_control'])
def test_rehashed_bound_cannot_hide_missing_or_forged_independent_scope(saved_public, control):
    bound = deepcopy(saved_public['bound'])
    if control == 'bare_number': bound = 660.0
    elif control == 'missing_record': bound.pop('review_record')
    elif control in {'missing_case', 'missing_control'}:
        value = json.loads(Path(bound['measurements']['path']).read_text())
        value['cases'].pop(0 if control == 'missing_case' else -1)
        bound['measurements'] = _save(Path(bound['measurements']['path']), value)
    else:
        value = json.loads(Path(bound['decision']['path']).read_text())
        if control == 'rejected': value['status'] = 'rejected'
        elif control == 'consumer_relabel': value['consumer_timing_custody'] = 'proved'
        elif control == 'too_large': value['finite_bound_seconds'] = 661
        elif control == 'not_finite': value['finite_bound_seconds'] = float('inf')
        elif control == 'below_observation': value['finite_bound_seconds'] = 1
        elif control == 'changed_scope': value['elapsed_scope'] = 'before_observer_return'
        elif control == 'forged_reviewer': value['reviewer']['independence']['execution_participation'] = 'producer'
        bound['decision'] = _save(Path(bound['decision']['path']), value)
    proof = model_profile_release_proof(saved_public['results'], require_complete=True,
        whole_journey_bound_evidence=bound, public_source_evidence=saved_public['config'])
    assert proof['status'] == 'failed' and proof['whole_journey_bound_status'] == 'unqualified'


@pytest.mark.parametrize('key', ['predeclaration', 'source_cases', 'observed_bindings',
    'independent_audit', 'output', 'retained_manifest', 'review_record'])
def test_missing_or_changed_semantic_ref_stays_failed(saved_public, tmp_path, key):
    Path(saved_public['config'][key]['path']).write_text('{}\n')
    sidecar = _finalize(saved_public, tmp_path / 'failed.json')
    assert sidecar['status'] == 'failed'


@pytest.mark.parametrize('control', ['browser', 'recovery', 'statistics', 'nonterminal',
    'quality', 'unexplained_profile', 'scorecard', 'semantic_failure', 'missing_field'])
def test_unrelated_or_unexplained_base_failures_are_never_promoted(saved_public, tmp_path, control):
    base = deepcopy(saved_public['base'])
    if control == 'browser': base['browser_surface_proof']['status'] = 'failed'
    elif control == 'recovery': base['commit_recovery_proof']['status'] = 'failed'
    elif control == 'statistics': base['campaign']['outcome_statistics']['status'] = 'failed'
    elif control == 'nonterminal': base['campaign']['proof_tier'] = 'discovery'
    elif control == 'quality': base['results'][0]['quality']['passed'] = False
    elif control == 'unexplained_profile': base['model_profile_proof']['issues'].append('unrelated failure')
    elif control == 'scorecard': base['onboarding_quality_scorecard']['status'] = 'awaiting-independent-review'
    elif control == 'semantic_failure': base['semantic_release'] = {'status': 'failed', 'passed': False}
    elif control == 'missing_field': base.pop('unavailable_provider_proof')
    _replace_saved_base(saved_public, base, recompute_scorecard=control in {'browser', 'recovery'})
    sidecar = _finalize(saved_public, tmp_path / 'failed.json')
    assert sidecar['status'] == 'failed'
    qualification = sidecar['public_qualification']
    if control in {'statistics', 'nonterminal'}:
        assert qualification['status'] == 'passed', qualification
        issue = 'outcome statistics did not pass' if control == 'statistics' else 'not terminal release proof'
        assert issue in str(sidecar['automated_release_gates']['issues'])
    else:
        assert not qualification.get('original_failure_authenticated', False)
        assert 'bytes changed' not in str(qualification['issues'])


def test_published_floors_are_exact_and_owned(saved_public, tmp_path, monkeypatch):
    floors = published_structural_floors()
    assert _frozen_floor_issues(floors) == ()
    floors['atomic_semantic_fidelity'] = 0.9
    monkeypatch.setattr(public, 'published_structural_floors', lambda: floors)
    sidecar = _finalize(saved_public, tmp_path / 'failed.json')
    assert sidecar['status'] == 'failed' and 'published contract' in str(sidecar['public_qualification']['issues'])


@pytest.mark.parametrize('control', ['write_attempt', 'changed_record', 'disabled_mode'])
def test_restamped_unavailable_passed_label_cannot_hide_failed_real_control(saved_public, tmp_path, control):
    base = deepcopy(saved_public['base'])
    unavailable = base['unavailable_provider_proof']
    if control == 'write_attempt': unavailable['no_write']['write_attempts'].append('write governed record')
    elif control == 'changed_record': unavailable['no_write']['changed_records'].append('odylith/radar/source/fake.json')
    else: unavailable['runtime_provider_mode'] = 'active'
    _replace_saved_base(saved_public, base)
    result = _finalize(saved_public, tmp_path / 'failed.json')
    assert result['status'] == 'failed'
    assert 'unavailable-provider control' in str(result['public_qualification']['issues'])
    assert 'bytes changed' not in str(result['public_qualification']['issues'])


def test_saved_result_roundtrip_refuses_field_loss(saved_public):
    rows = deepcopy(saved_public['base']['results'])
    rows[0]['commit_manifest_summary'] = None
    with pytest.raises(ValueError, match='roundtrip'):
        public.typed_saved_matrix_results(rows)


def test_malformed_timing_stage_fails_normally(saved_public):
    base = deepcopy(saved_public['base'])
    base['results'][0]['evidence']['model_profile']['stage_observation'] = 'malformed'
    saved_public['config']['output'] = _save(Path(saved_public['base_ref']['path']), base)
    rows = (*public.typed_saved_matrix_results(base['results']),
        *public.typed_saved_matrix_results(base['lower_capability_control_proof']['results']))
    bound, report, issues = public.validate_measured_public_bound(results=rows,
        source_evidence=saved_public['config'], bound_evidence=saved_public['bound'])
    assert bound is None and report['status'] == 'failed'
    assert 'stage observation must be an object' in str(issues)


def test_restamped_declared_control_count_cannot_hide_missing_observation(saved_public):
    base = deepcopy(saved_public['base'])
    base['lower_capability_control_proof']['case_count'] = 2
    _replace_saved_base(saved_public, base)
    bound, report, issues = public.validate_measured_public_bound(results=saved_public['results'],
        source_evidence=saved_public['config'], bound_evidence=saved_public['bound'])
    assert bound is None and report['status'] == 'failed'
    assert 'every declared control observation' in str(issues)


@pytest.mark.parametrize(('field', 'value'), [
    ('write_audit_active', 'false'), ('staged_transaction_present', 'false'),
    ('write_attempts', {}), ('returncode', False),
    ('before_record_count', '0'), ('after_record_count', False),
    ('subprocess_attempts', {}), ('changed_records', {}),
    ('write_audit_error', {}), ('proposal_seconds', True),
])
def test_coherently_restamped_unavailable_shapes_never_receive_credit(saved_public, tmp_path, field, value):
    base = deepcopy(saved_public['base'])
    proof = base['unavailable_provider_proof']
    target = proof if field in {'returncode', 'proposal_seconds'} else proof['no_write']
    target[field] = value
    _replace_saved_base(saved_public, base)
    result = _finalize(saved_public, tmp_path / 'malformed.json')
    assert result['status'] == 'failed', result
    issues = str(result['public_qualification']['issues'])
    assert 'saved unavailable-provider control did not pass' in issues
    assert 'bytes changed' not in issues


def _unavailable_arguments(saved):
    proof = saved['base']['unavailable_provider_proof']
    return {**{name: proof[name] for name in ('returncode', 'proposal_seconds')},
        'detail': proof['failure_detail'], **proof['no_write']}


@pytest.mark.parametrize(('field', 'value'), [
    ('returncode', False), ('returncode', 0.0), ('returncode', '0'),
    ('proposal_seconds', True), ('proposal_seconds', '10.0'), ('proposal_seconds', float('inf')),
    ('write_audit_active', 'false'), ('staged_transaction_present', 'false'),
    ('before_record_count', False), ('before_record_count', -1),
    ('after_record_count', '1'), ('after_record_count', -1),
    ('write_attempts', {}), ('subprocess_attempts', {}), ('changed_records', {}),
    ('subprocess_attempts', [1]), ('changed_records', [None]),
    ('write_audit_error', {}), ('detail', []),
])
def test_canonical_unavailable_owner_refuses_malformed_saved_values(saved_public, field, value):
    arguments = _unavailable_arguments(saved_public)
    arguments[field] = value
    assert unavailable_provider_proof_issues(**arguments)


def test_canonical_unavailable_owner_preserves_false_and_pending_distinctions(saved_public):
    arguments = _unavailable_arguments(saved_public)
    assert unavailable_provider_proof_issues(**arguments) == ()
    assert unavailable_provider_proof_issues(**{**arguments, 'write_audit_active': False}) == (
        'post-receipt provider isolation did not activate the write audit',)
    assert unavailable_provider_proof_issues(**{**arguments, 'staged_transaction_present': False}) == (
        'post-receipt provider isolation did not stage a transaction',)
