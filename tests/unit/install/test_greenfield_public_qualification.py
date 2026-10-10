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


@pytest.fixture
def composition_sources(tmp_path):
    """Synthetic identities only; no real High4 or release observations."""
    primary = [replace(_case(f'p{i}', expectation='transaction_committed'),
        prompt=f'Synthetic source {i}. A reviewer records a result.') for i in range(40)]
    primary = [replace(case, provenance=replace(case.provenance, source_family=f'controlled-domain-{i%4}')) for i, case in enumerate(primary)]
    originals = ('release-accessibility-005-source', 'release-accessibility-007-source',
        'release-agriculture-021-description', 'release-agriculture-037-source')
    primary[:4] = [replace(primary[i], case_id=case_id) for i, case_id in enumerate(originals)]
    genuine = [replace(primary[i], case_id=f'genuine-lifecycle-edit-v3-{i+1:02}', lifecycle_correction='Also retain a signed note.') for i in range(4)]
    high = [replace(primary[i], case_id=f'h{i}', prompt=f'Separate controlled source {i}. A reviewer records a result.',
        lifecycle_correction='Also retain a signed note.', input_style='edited_confirmation') for i in range(4)]
    predecl = _save(tmp_path / 'genuine-source.json', {'cases': [
        {'case_id': case.case_id, 'original_case_id': primary[i].case_id} for i, case in enumerate(genuine)]})
    value = {name: {'input_identities': public._composition_input_identities(cases)}
        for name, cases in (('primary', primary), ('genuine_edit', genuine), ('high', high))}
    value['genuine_edit']['predeclaration'] = predecl
    value['permitted_baseline_overlap'] = [{'primary_case_id': primary[i].case_id, 'genuine_case_id': case.case_id,
        **{key: value['primary']['input_identities'][i][key] for key in ('baseline_request_sha256', 'h0_source_sha256')}}
        for i, case in enumerate(genuine)]
    value['_controlled_cases'] = {'primary': primary, 'high': high, 'genuine_edit': genuine}
    return value


@pytest.mark.parametrize('defect', [None, 'primary39', 'high3', 'genuine3', 'role', 'order', 'not_high', 'not_edit',
    'same_domain', 'unknown_domain', 'empty_domain'])
def test_composition_membership_fixes_denominators_and_exclusion_role(composition_sources, tmp_path, monkeypatch, defect):
    value = deepcopy(composition_sources)
    controlled = value.pop('_controlled_cases')
    for name, role in (('primary', 'scored_primary'), ('high', 'scored_high_edit'), ('genuine_edit', 'exclusion_and_separate_gate_only')):
        cases = controlled[name]
        if name == 'high' and defect == 'same_domain':
            cases = [replace(case, provenance=replace(case.provenance, source_family='controlled-domain-0')) for case in cases]
        elif name == 'high' and defect in {'unknown_domain', 'empty_domain'}:
            label = 'unknown-domain' if defect == 'unknown_domain' else ''
            cases = [replace(cases[0], provenance=replace(cases[0].provenance, source_family=label)), *cases[1:]]
        if defect == {'primary': 'primary39', 'high': 'high3', 'genuine_edit': 'genuine3'}[name]: cases = cases[:-1]
        raw = [{'id': case.case_id, 'name': case.name, 'prompt': case.prompt, 'lifecycle_correction': case.lifecycle_correction,
            'input_style': case.input_style, 'provenance': {'source_family': case.provenance.source_family},
            'required_terms': ['reviewer'], 'leakage_terms': ['reviewer']} for case in cases]
        ref = _save(tmp_path / (name + '-cases.json'), {'cases': raw})
        parsed = load_case_file(Path(ref['path']))
        value[name].update(family_id=name, role=role, case_count=40 if name == 'primary' else 4,
            ordered_case_ids_sha256=digest([case.case_id for case in parsed]), source_cases=ref,
            input_identities=public._composition_input_identities(parsed))
        if name != 'genuine_edit': value[name]['predeclaration'] = _save(tmp_path / (name + '-declaration.json'),
            {'version': PUBLIC_SOURCE_MODE if name == 'primary' else public.PUBLIC_EDIT_SOURCE_MODE})
        else: value[name]['annotation_manifest'] = _save(tmp_path / 'annotation-manifest.json', {'controlled': True})
    if defect == 'role': value['genuine_edit']['role'] = 'scored_high_edit'
    elif defect == 'order': value['high']['ordered_case_ids_sha256'] = '0' * 64
    def source_grade(**kwargs):
        return {case.case_id: {'complexity_band': 'moderate' if defect == 'not_high' else 'high'} for case in kwargs['cases']}, ()
    monkeypatch.setattr(public, 'validate_source_predicate_predeclaration', source_grade)
    monkeypatch.setattr(public, '_composition_genuine_sources', lambda **kwargs: None)
    if defect == 'not_edit':
        original = public.load_case_file
        monkeypatch.setattr(public, 'load_case_file', lambda path: tuple(replace(case, input_style='structured') for case in original(path)))
    if defect is None:
        families = public._composition_membership(value)
        assert {key: len(cases) for key, cases in families.items()} == {'primary': 40, 'high': 4, 'genuine_edit': 4}
        assert len((*families['primary'], *families['high'])) == 44
        assert len({case.provenance.source_family for case in families['high']}) == 4
        assert {case.provenance.source_family for case in families['high']} <= {case.provenance.source_family for case in families['primary']}
    else:
        with pytest.raises(ValueError): public._composition_membership(value)


def test_composition_preserves_four_authorized_h0_pairs_and_shared_raw_correction(composition_sources):
    public._composition_source_exclusions(composition_sources)
    assert len(composition_sources['primary']['input_identities']) == 40
    assert len(composition_sources['high']['input_identities']) == 4
    assert len({row['correction_sha256'] for row in composition_sources['genuine_edit']['input_identities']}) == 1


@pytest.mark.parametrize('defect', ['high_request', 'high_h0', 'high_h1', 'high_self', 'undeclared_genuine',
    'edited_duplicate', 'missing_pair', 'wrong_pair_h0'])
def test_composition_refuses_source_or_journey_reuse(composition_sources, defect):
    value = composition_sources
    p, g, h = (value[key]['input_identities'] for key in ('primary', 'genuine_edit', 'high'))
    if defect == 'high_request': h[0]['baseline_request_sha256'] = p[8]['baseline_request_sha256']
    elif defect == 'high_h0': h[0]['h0_source_sha256'] = g[0]['h0_source_sha256']
    elif defect == 'high_h1': h[0]['h1_source_sha256'] = g[0]['h1_source_sha256']
    elif defect == 'high_self': h[1].update({key: h[0][key] for key in h[0] if key != 'case_id'})
    elif defect == 'undeclared_genuine': g[0]['h1_source_sha256'] = p[8]['h0_source_sha256']
    elif defect == 'edited_duplicate': g[1].update({key: g[0][key] for key in ('h0_source_sha256', 'correction_sha256', 'h1_source_sha256')})
    elif defect == 'missing_pair': value['permitted_baseline_overlap'].pop()
    elif defect == 'wrong_pair_h0': value['permitted_baseline_overlap'][0]['h0_source_sha256'] = '0' * 64
    with pytest.raises(ValueError):
        public._composition_source_exclusions(value)


def _phase(case_id, phase, *, tx, invocation):
    return {'case_id': case_id, 'phase': phase, 'outcome': 'commit', 'transaction_hash': tx,
        'native_invocation_id': invocation, 'completion_receipt_sha256': digest(invocation),
        'result_sha256': digest(case_id), 'retained_case_manifest_sha256': digest(case_id + ':package')}


def test_independent_h0_canonical_equality_requires_distinct_actual_delivery(composition_sources):
    pair = composition_sources['permitted_baseline_overlap'][0]
    phases = [('primary', _phase(pair['primary_case_id'], 'initial', tx='same-canonical', invocation='first')),
        ('genuine_edit', _phase(pair['genuine_case_id'], 'initial', tx='same-canonical', invocation='second')),
        ('genuine_edit', _phase(pair['genuine_case_id'], 'edited', tx='edited-canonical', invocation='third'))]
    public._composition_output_exclusions(phases=phases, declaration=composition_sources, outputs=['a', 'b'], manifests=['c', 'd'])


@pytest.mark.parametrize('defect', ['output', 'manifest', 'result', 'case_package', 'receipt', 'invocation', 'high_transaction', 'edited_transaction'])
def test_composition_refuses_duplicate_observation_credit(composition_sources, defect):
    first = _phase('p0', 'initial', tx='initial', invocation='first')
    second = _phase('h0', 'initial', tx='different', invocation='second')
    outputs, manifests = ['a', 'b'], ['c', 'd']
    if defect == 'output': outputs[1] = outputs[0]
    elif defect == 'manifest': manifests[1] = manifests[0]
    else:
        key = {'result': 'result_sha256', 'case_package': 'retained_case_manifest_sha256', 'receipt': 'completion_receipt_sha256',
            'invocation': 'native_invocation_id', 'high_transaction': 'transaction_hash', 'edited_transaction': 'transaction_hash'}[defect]
        second[key] = first[key]
        if defect == 'edited_transaction': second.update(case_id='g0', phase='edited')
    with pytest.raises(ValueError):
        public._composition_output_exclusions(phases=[('primary', first), ('genuine_edit' if defect == 'edited_transaction' else 'high', second)],
            declaration=composition_sources, outputs=outputs, manifests=manifests)


@pytest.fixture
def composition_execution(tmp_path, monkeypatch):
    """Actual file association with synthetic native grading; never qualification."""
    version = public.PUBLIC_COMPOSITION_MODE
    source_root = tmp_path / 'source-export'
    source_root.mkdir()
    cases_ref = _save(tmp_path / 'invoked-cases.json', {'cases': [{'id': 'clarify', 'name': 'controlled clarification',
        'prompt': 'A review workspace needs an unspecified final decision.', 'required_terms': ['review'],
        'leakage_terms': ['review'], 'expectation': 'clarification_required'}]})
    case = load_case_file(Path(cases_ref['path']))[0]
    predecl = _save(tmp_path / 'source-declaration.json', _declare(case, cases_ref['sha256']))
    imports = {}
    for i, name in enumerate(('odylith.runtime.domain_intelligence.greenfield_model_profile_contract',
            'odylith.runtime.domain_intelligence.greenfield_host_transport', 'greenfield_preconfirm_matrix')):
        path = source_root / f'owner-{i}.py'
        path.write_text(f'# controlled owner {i}; never imported\n')
        imports[name] = {'path': str(path), 'sha256': sha256_file(path)}
    profile = {'actual_import_paths': {key: imports['odylith.runtime.domain_intelligence.' + module]['path']
        for key, module in (('profile', 'greenfield_model_profile_contract'), ('transport', 'greenfield_host_transport'))},
        **{key + '_owner_sha256': imports['odylith.runtime.domain_intelligence.' + module]['sha256']
        for key, module in (('profile', 'greenfield_model_profile_contract'), ('transport', 'greenfield_host_transport'))}}
    runner = source_root / 'runner.py'
    runner.write_text('# controlled runner; never executed\n')
    runner_ref = {'path': str(runner), 'sha256': sha256_file(runner)}
    native = source_root / 'driver'
    native.write_text('controlled executable; never executed\n')
    activation = {'file_pins': {str(runner): runner_ref['sha256'], cases_ref['path']: cases_ref['sha256']}}
    custody = {name: _save(tmp_path / (name + '.json'), profile if name == 'profile' else activation if name == 'activation' else {'controlled': name})
        for name in public._RELEASE_CUSTODY_REFS}
    native_profile = _profile_evidence()
    native_request = native_profile['stage_observation']['authority_gate_request']
    common = {key: digest(key) for key in public._OBSERVATION_FIELDS - {'runtime_executable', 'runtime_executable_sha256', 'actual_import_pins'}}
    common.update(source_export_root=str(source_root), distribution_root=str(tmp_path / 'distribution'), activation_sha256=custody['activation']['sha256'])
    common.update(profile_id=native_profile['profile_id'], trusted_executable_sha256=native_request['executable_sha256'],
        **{key: native_request[key] for key in ('model', 'reasoning_effort', 'argv_shape_sha256')})
    observed = {**common, 'runtime_executable': str(native), 'runtime_executable_sha256': sha256_file(native), 'actual_import_pins': imports}
    family = {'family_id': 'controlled-primary', 'source_cases': cases_ref, 'predeclaration': predecl}
    declaration = {'release_custody': custody}
    declaration_ref = _save(tmp_path / 'composition.json', declaration)
    row = _saved_result(case, profile=native_profile)
    row.evidence['case'].update(source_file=cases_ref['path'])
    command = 'Which final decision must the reviewer record?\n'
    row.evidence['model_profile']['stage_observation']['proposal_stdout_sha256'] = __import__('hashlib').sha256(command.encode()).hexdigest()
    root = prepare_retained_evidence_output_dir(output_dir=tmp_path / 'retained', temp_parent=tmp_path / 'repos')
    retained = begin_retained_case_evidence(evidence_root=root, case_id=case.case_id)
    record_retained_case_text(retained, 'commands/propose.stdout', command)
    record_retained_case_json(retained, 'semantic/dry-run-receipt.v2.json', {'mode': 'clarification_required'})
    case_path = finalize_retained_case_evidence(case=retained, repo_root=tmp_path / 'empty', result_payload=row.to_dict())
    manifest = write_retained_evidence_manifest(root=root, expected_case_ids=(case.case_id,))
    manifest_ref = {'path': str(manifest), 'sha256': sha256_file(manifest)}
    output_ref = _save(tmp_path / 'output.json', {'results': [row.to_dict()]})
    argv = [str(native), '-B', str(runner)]
    request = {'version': version + '.execution-request.v1', 'family_id': family['family_id'],
        'declaration_sha256': declaration_ref['sha256'], 'release_custody_sha256': digest(custody),
        'source_cases_sha256': cases_ref['sha256'], 'predeclaration_sha256': predecl['sha256'],
        'runner_sha256': runner_ref['sha256'], 'argv': argv, 'cwd': str(source_root), 'observed_before': observed}
    request_ref = _save(tmp_path / 'request.json', request)
    phases = public._composition_case_phases(case=case, row=row, case_path=case_path,
        package=json.loads(case_path.read_text()), request_sha256=request_ref['sha256'])
    log = tmp_path / 'execution.log'
    log.write_text('controlled fixture; no invocation\n')
    log_ref = {'path': str(log), 'sha256': sha256_file(log)}
    dispatch = {'status': 'CLEAR_READ_ONLY_FAMILY_DISPATCH', 'activation': custody['activation'],
        'identity': {'head': common['commit'], 'tree': common['tree'], 'archive_sha256': common['archive_sha256']},
        'composition': {'declaration_sha256': declaration_ref['sha256'], 'family_id': family['family_id'],
            'runner': runner_ref, 'argv_sha256': digest(argv), 'source_cases': cases_ref, 'predeclaration_sha256': predecl['sha256']}}
    dispatch_ref = _save(tmp_path / 'dispatch.json', dispatch)
    result = {'version': version + '.execution-result.v1', 'family_id': family['family_id'], 'declaration_sha256': declaration_ref['sha256'],
        'request_sha256': request_ref['sha256'], 'exit_code': 0, 'output_sha256': output_ref['sha256'],
        'retained_manifest_sha256': manifest_ref['sha256'], 'log_sha256': log_ref['sha256'],
        'observed_after': observed, 'case_phases_sha256': digest(phases)}
    result_ref = _save(tmp_path / 'result.json', result)
    binding = {'version': version + '.execution-binding.v1', 'declaration_sha256': declaration_ref['sha256'],
        'family_id': family['family_id'], **{name + '_sha256': ref['sha256'] for name, ref in custody.items()},
        'dispatch_attestation_sha256': dispatch_ref['sha256'], 'source_cases_sha256': cases_ref['sha256'],
        'predeclaration_sha256': predecl['sha256'], 'output_sha256': output_ref['sha256'],
        'retained_manifest_sha256': manifest_ref['sha256'], 'runner_sha256': runner_ref['sha256'],
        'execution_request': request_ref, 'execution_result': result_ref, 'execution_log': log_ref,
        'observed_before': observed, 'observed_after': observed, 'case_phases': phases}
    binding_ref = _save(tmp_path / 'binding.json', binding)
    calls = []
    def native_grade(**kwargs):
        calls.append(kwargs)
        return {}, ()  # Isolate association; existing native semantic custody owner is not regraded here.
    import greenfield_matrix_statistics
    monkeypatch.setattr(greenfield_matrix_statistics, 'release_slice_evidence', native_grade)
    return {'arguments': {'ref': binding_ref, 'declaration_ref': declaration_ref, 'declaration': declaration,
        'family': family, 'output_ref': output_ref, 'manifest_ref': manifest_ref, 'dispatch_ref': dispatch_ref,
        'rows': (row,), 'common': common}, 'binding': binding, 'request': request, 'result': result,
        'dispatch': dispatch, 'phases': phases, 'case_path': case_path, 'calls': calls}


def test_execution_association_accepts_clarification_without_inventing_receipt(composition_execution):
    value = composition_execution
    assert public._composition_execution(**value['arguments']) == value['phases']
    assert value['phases'][0]['outcome'] == 'clarify'
    assert value['phases'][0]['transaction_hash'] is value['phases'][0]['completion_receipt_sha256'] is None
    assert value['calls'][0]['annotated_complexity'] == value['calls'][0]['source_predicate_complexity']
    assert value['calls'][0]['allow_unsealed_clarification'] is True


@pytest.mark.parametrize('defect', ['before_after', 'wrong_package', 'driver_bytes', 'import_bytes', 'cwd', 'argv',
    'future_request_dispatch', 'static_preflight', 'request_hash', 'failed_result', 'phase_receipt', 'command_bytes', 'dropped_manifest', 'native_executable'])
def test_execution_refuses_static_or_wrong_actual_custody(composition_execution, defect):
    value = composition_execution
    binding, request, result, dispatch = (deepcopy(value[key]) for key in ('binding', 'request', 'result', 'dispatch'))
    arguments = dict(value['arguments'])
    if defect == 'before_after': binding['observed_after']['wheel_sha256'] = '1' * 64
    elif defect == 'wrong_package': arguments['common'] = {**arguments['common'], 'tree': '1' * 64}
    elif defect == 'driver_bytes': Path(binding['observed_before']['runtime_executable']).write_text('changed bytes')
    elif defect == 'import_bytes': Path(next(iter(binding['observed_before']['actual_import_pins'].values()))['path']).write_text('changed bytes')
    elif defect == 'cwd': request['cwd'] = str(Path(request['cwd']).parent)
    elif defect == 'argv': request['argv'].append('--different-source')
    elif defect == 'future_request_dispatch': dispatch['composition']['execution_request_sha256'] = binding['execution_request']['sha256']
    elif defect == 'static_preflight': binding.pop('execution_result')
    elif defect == 'request_hash': result['request_sha256'] = '2' * 64
    elif defect == 'failed_result': result['exit_code'] = 2
    elif defect == 'phase_receipt': binding['case_phases'][0]['completion_receipt_sha256'] = '3' * 64
    elif defect == 'command_bytes': (value['case_path'].parent / 'commands/propose.stdout').write_text('different actual question')
    elif defect == 'dropped_manifest': arguments['manifest_ref'] = arguments['output_ref']
    elif defect == 'native_executable':
        native_row = replace(arguments['rows'][0], evidence=deepcopy(arguments['rows'][0].evidence))
        native_row.evidence['model_profile']['stage_observation']['authority_gate_request']['executable_sha256'] = '4' * 64
        arguments['rows'] = (native_row,)
    if defect in {'cwd', 'argv'}:
        binding['execution_request'] = _save(Path(binding['execution_request']['path']), request)
        result['request_sha256'] = binding['execution_request']['sha256']
    if defect == 'future_request_dispatch':
        arguments['dispatch_ref'] = _save(Path(arguments['dispatch_ref']['path']), dispatch)
        binding['dispatch_attestation_sha256'] = arguments['dispatch_ref']['sha256']
    if 'execution_result' in binding:
        result['case_phases_sha256'] = digest(binding['case_phases'])
        binding['execution_result'] = _save(Path(binding['execution_result']['path']), result)
    arguments['ref'] = _save(Path(arguments['ref']['path']), binding)
    with pytest.raises((ValueError, OSError)) as caught:
        public._composition_execution(**arguments)
    if defect == 'native_executable': assert 'native call differs' in str(caught.value)


def test_commit_phase_refuses_missing_actual_delivery(composition_execution):
    value = composition_execution
    case = load_case_file(Path(value['arguments']['family']['source_cases']['path']))[0]
    with pytest.raises(ValueError, match='actual bounded delivery custody'):
        public._composition_case_phases(case=replace(case, expectation='transaction_committed'), row=value['arguments']['rows'][0],
            case_path=value['case_path'], package=json.loads(value['case_path'].read_text()), request_sha256='0' * 64)


@pytest.fixture
def genuine_batches(saved_public, tmp_path):
    """Closed batch/review wiring only; original synthetic native rows stay synthetic."""
    version = public.PUBLIC_COMPOSITION_MODE
    rows = []
    for i in range(4):
        row = deepcopy(saved_public['base']['results'][0])
        row['evidence']['case']['id'] = f'genuine-lifecycle-edit-v3-{i+1:02}'
        rows.append(row)
    family = {'family_id': 'controlled-genuine', 'input_identities': [{'case_id': row['evidence']['case']['id']} for row in rows],
        **{name: _save(tmp_path / ('genuine-' + name + '.json'), {'controlled': name})
            for name in ('source_cases', 'predeclaration', 'annotation_manifest')}}
    declaration = {'release_custody': {'controlled': 'not-native-package'}}
    declaration_ref = _save(tmp_path / 'composition-declaration.json', declaration)
    refs = {'output': [], 'retained_manifest': [], 'dispatch_attestation': [], 'execution_binding': []}
    for i, selected in enumerate((rows[:1], rows[1:])):
        refs['output'].append(_save(tmp_path / f'batch-{i}-output.json', {'results': selected}))
        for name in ('retained_manifest', 'dispatch_attestation', 'execution_binding'):
            refs[name].append(_save(tmp_path / f'batch-{i}-{name}.json', {'original-batch': i, 'kind': name}))
    final = {name: _save(tmp_path / ('wrapper-' + name + '.json'), {'version': version + '.' + suffix + '.v1',
        'family_id': family['family_id'], 'batches': refs[name]}) for name, suffix in
        (('output', 'batch-outputs'), ('retained_manifest', 'batch-manifests'), ('dispatch_attestation', 'batch-dispatches'))}
    final['execution_binding'] = _save(tmp_path / 'wrapper-binding.json', {'version': version + '.execution-binding-batches.v1',
        'declaration_sha256': declaration_ref['sha256'], 'family_id': family['family_id'],
        'output_sha256': final['output']['sha256'], 'retained_manifest_sha256': final['retained_manifest']['sha256'], 'batches': refs['execution_binding']})
    identities = {'declaration_sha256': declaration_ref['sha256'], 'release_custody_sha256': digest(declaration['release_custody']),
        **{name + '_sha256': family[name]['sha256'] for name in ('source_cases', 'predeclaration', 'annotation_manifest')},
        **{name + '_sha256': final[name]['sha256'] for name in ('output', 'retained_manifest')}}
    review = {'version': version + '.genuine-review-record.v1', **identities, 'reviewer': saved_public['review']['reviewer'],
        'cases': [{'case_id': row['evidence']['case']['id'], 'verdict': 'passed', 'result_sha256': digest(row),
            'rationale': 'Controlled association verdict; not actual native qualification.'} for row in rows]}
    final['independent_review_record'] = _save(tmp_path / 'genuine-review.json', review)
    gate = {'version': version + '.genuine-gate.v1', 'status': 'passed', **identities,
        'qualified_case_ids': [row['evidence']['case']['id'] for row in rows],
        'independent_review_record_sha256': final['independent_review_record']['sha256']}
    final['gate_report'] = _save(tmp_path / 'genuine-gate.json', gate)
    return {'arguments': {'final': final, 'family': family, 'declaration_ref': declaration_ref, 'declaration': declaration},
        'review': review, 'gate': gate, 'refs': refs}


def test_genuine_batch_reader_preserves_original_one_plus_three_and_independent_four_verdicts(genuine_batches):
    value = genuine_batches
    batches = public._composition_genuine_batches(**value['arguments'])
    assert [len(batch[-1]) for batch in batches] == [1, 3]
    assert [batch[0] for batch in batches] == value['refs']['output']
    assert [row.evidence['case']['id'] for batch in batches for row in batch[-1]] == value['gate']['qualified_case_ids']


@pytest.mark.parametrize('defect', ['missing_dispatch', 'two_plus_two', 'failed_row', 'missing_verdict', 'failed_verdict',
    'stale_result', 'execution_reviewer', 'stale_package'])
def test_genuine_batch_reader_refuses_incomplete_or_regraded_gate(genuine_batches, defect):
    value = genuine_batches
    arguments = deepcopy(value['arguments'])
    final, review, gate = arguments['final'], deepcopy(value['review']), deepcopy(value['gate'])
    if defect == 'missing_dispatch': final.pop('dispatch_attestation')
    elif defect in {'two_plus_two', 'failed_row'}:
        path = Path(value['refs']['output'][0]['path'])
        output = json.loads(path.read_text())
        if defect == 'two_plus_two': output['results'].append(deepcopy(output['results'][0]))
        else: output['results'][0]['status'] = 'failed'
        changed = _save(path, output)
        wrapper_path = Path(final['output']['path'])
        wrapper = json.loads(wrapper_path.read_text())
        wrapper['batches'][0] = changed
        final['output'] = _save(wrapper_path, wrapper)
        envelope_path = Path(final['execution_binding']['path'])
        envelope = json.loads(envelope_path.read_text())
        envelope['output_sha256'] = final['output']['sha256']
        final['execution_binding'] = _save(envelope_path, envelope)
    else:
        if defect == 'missing_verdict': review['cases'].pop()
        elif defect == 'failed_verdict': review['cases'][1]['verdict'] = 'failed'
        elif defect == 'stale_result': review['cases'][1]['result_sha256'] = '1' * 64
        elif defect == 'execution_reviewer': review['reviewer']['independence']['execution_participation'] = 'runner'
        elif defect == 'stale_package': review['release_custody_sha256'] = '2' * 64
        final['independent_review_record'] = _save(Path(final['independent_review_record']['path']), review)
        gate['independent_review_record_sha256'] = final['independent_review_record']['sha256']
        final['gate_report'] = _save(Path(final['gate_report']['path']), gate)
    with pytest.raises(ValueError):
        public._composition_genuine_batches(**arguments)


def test_nested_profile_source_selection_keeps_both_families_and_exact_manifest_owner(tmp_path, monkeypatch):
    import greenfield_semantic_release_score as score
    from greenfield_semantic_case_score import PUBLIC_EDIT_SOURCE_MODE
    configuration = {'mode': public.PUBLIC_COMPOSITION_MODE}
    families = {}
    for name, count, mode in (('primary', 40, PUBLIC_SOURCE_MODE), ('high', 4, PUBLIC_EDIT_SOURCE_MODE)):
        ref = _save(tmp_path / (name + '-cases.json'), {'cases': [{'id': f'{name}-{i}', 'name': f'controlled {name} {i}',
            'prompt': f'Controlled record {i} needs a decision.', 'required_terms': ['record'], 'leakage_terms': ['record']}
            for i in range(count)]})
        families[name] = load_case_file(Path(ref['path']))
        configuration[name] = {'mode': mode, 'source_cases': ref, 'retained_manifest': {'path': str(tmp_path / (name + '-manifest.json'))}}
    calls = []
    def source_custody(**kwargs):
        calls.append(kwargs)
        return ({case.case_id: {'controlled': True} for case in kwargs['cases']},
            {case.case_id: {'bound': True} for case in kwargs['cases']}, ())
    monkeypatch.setattr(score, 'load_source_predicate_evidence', source_custody)
    selected = (families['high'][2],)
    annotations, bindings, manifests, issues = score._source_release_inputs(configuration=configuration, cases=selected, results=())
    assert issues == () and set(annotations) == set(bindings) == {selected[0].case_id}
    assert [call['configuration']['mode'] for call in calls] == [PUBLIC_SOURCE_MODE, PUBLIC_EDIT_SOURCE_MODE]
    assert [len(call['cases']) for call in calls] == [0, 1]
    assert len(manifests) == 44
    assert manifests[selected[0].case_id] == Path(configuration['high']['retained_manifest']['path'])
    configuration['high']['mode'] = PUBLIC_SOURCE_MODE
    assert score._source_release_inputs(configuration=configuration, cases=selected, results=())[-1]
