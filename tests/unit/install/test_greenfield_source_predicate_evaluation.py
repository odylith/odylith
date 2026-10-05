"""Public evaluator contracts use synthetic audit fixtures, never semantic proof."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_evaluation_contract import validate_source_predicate_predeclaration, validate_atomic_annotations
from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_release_artifacts import (
    begin_retained_case_evidence, finalize_retained_case_evidence,
    prepare_retained_evidence_output_dir, record_retained_case_json,
    record_retained_case_text, sha256_file, write_retained_evidence_manifest,
)
from greenfield_matrix_statistics import release_slice_evidence
from greenfield_onboarding_review import validate_independent_reviewer
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from greenfield_relation_fidelity import (
    canonical_evidence_sha256 as digest, observed_semantic_universe, snapshot_relation_evidence,
)
from greenfield_semantic_case_score import (
    PUBLIC_SOURCE_MODE, source_predicate_units, validate_source_predicate_binding_case,
    score_source_predicates, load_source_predicate_evidence,
)
from greenfield_semantic_release_score import evaluate_semantic_release, _score_case
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_source
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import greenfield_complexity_band
from tests.unit.install.test_greenfield_release_source_duty_custody import _legacy_snapshot, _normalized_snapshot, _reseal
from tests.unit.install.test_greenfield_semantic_release_score import (
    _case, _clarification_result, _clarification_annotation, _commit_result, EXACT_RELEASE_FLOORS,
)
from tests.unit.install.test_greenfield_onboarding_review import _review_package


def _save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')
    return {'path': str(path), 'sha256': sha256_file(path)}


def _source_span(case, quote):
    source = case.prompt.encode()
    start = source.index(quote.encode())
    combined = combined_prompt_evidence_source(prompt=case.prompt, edit_evidence='').encode()
    combined_start = combined.index(source) + start
    return {'document': 'prompt', 'start_byte': start, 'end_byte': start + len(quote.encode()),
            'quote': quote, 'quote_sha256': hashlib.sha256(quote.encode()).hexdigest(),
            'operator_evidence_start_byte': combined_start,
            'operator_evidence_end_byte': combined_start + len(quote.encode())}


def _declare(case, source_case_hash):
    source = combined_prompt_evidence_source(prompt=case.prompt, edit_evidence='')
    clarify = case.expectation == 'clarification_required'
    dims = {key: 0 for key in (
        'evidence_bytes', 'documents', 'actors', 'state_objects', 'paths', 'external_systems',
        'internal_systems', 'contradictions', 'ambiguities', 'safety_boundaries',
        'success_metrics', 'evidence_requirements', 'component_responsibilities', 'assumptions', 'non_goals')}
    dims.update(evidence_bytes=len(source.encode()), documents=1, ambiguities=int(clarify))
    row = {'case_id': case.case_id, 'public_split': 'disclosed-public-live-subset',
        'prompt_sha256': hashlib.sha256(case.prompt.encode()).hexdigest(), 'confirmed_intent_sha256': '',
        'operator_evidence_sha256': hashlib.sha256(source.encode()).hexdigest(), 'source_family': 'fixture',
        'input_style': case.input_style, 'evidence_format': 'operator_prompt',
        'expected_outcome': 'clarify' if clarify else 'commit',
        'expected_clarification': {'field': 'first_path', 'question': 'What is the first complete task and visible result?',
            'missing_fact': 'Missing complete first path.', 'source_basis': _source_span(case, case.prompt)} if clarify else None,
        'source_texts': {'prompt': case.prompt, 'confirmed_intent_markdown': ''},
        'atoms': [{'id': 'A1', 'category': 'ambiguities' if clarify else 'constraints',
            'predicate': 'Ask the exact missing first path question.' if clarify else 'Preserve access state.',
            'materiality': 'material', 'evaluation_role': 'scored', 'expected_custody': 'ambiguity' if clarify else 'accepted_fact',
            'expected_polarity': 'required', 'source': _source_span(case, case.prompt)}],
        'first_path_relations': [], 'context_relations': [], 'component_responsibilities': [],
        'obligations': ['Preserve the full source obligation.'], 'complexity_dimensions': dims,
        'complexity_band': greenfield_complexity_band(dims), 'complexity_counting_note': 'Frozen source census.'}
    return {'artifact_kind': 'public source-only semantic predeclaration; not an evaluator annotation schema',
        'public_split': 'disclosed-public-live-subset', 'created_on': '2026-10-04',
        'sources': {'source-cases.json': source_case_hash}, 'case_count': 1,
        'schema_boundary': {'compatible_api_annotations': False},
        'independence': 'Synthetic source-only fixture; not a real semantic review.', 'cases': [row]}


def _bind(case, annotation, snapshot, clarification=None):
    universe = observed_semantic_universe(case=case, snapshot=snapshot) if snapshot else {}
    if clarification:
        universe['/clarification'] = {'id': '/clarification', 'kind': 'clarification',
            'destination_sha256': digest(clarification), 'source_witness_sha256': '', 'normalized_role_sha256': {}, 'custody_state': 'ambiguity'}
    units = source_predicate_units(annotation)
    main = [key for key, value in universe.items() if value['kind'] == 'main_event']
    forward = []
    for key, unit in units.items():
        observed = [main[int(key.rsplit(':', 1)[1]) - 1]] if unit['kind'] == 'first_path_events' else list(universe)
        forward.append({'id': key, 'unit': unit, 'disposition': 'reference_only' if unit['evaluation_role'] == 'reference_only' else 'full',
            'observed': observed, 'semantic_identity': key + ':source-obligation',
            'rationale': 'Synthetic explicit adjudication fixture; no real entailment claim.'})
    source_id = next(key for key, unit in units.items() if unit['evaluation_role'] == 'scored')
    reverse = [{'id': key, 'evidence': value, 'disposition': 'assumption' if value['custody_state'] == 'assumption' else 'source_supported',
        'source_ids': [source_id], 'duplicate_of': None,
        'rationale': 'Synthetic explicit reverse adjudication fixture.'} for key, value in universe.items()]
    binding = {'case_id': case.case_id, 'operator_evidence_sha256': annotation['operator_evidence_sha256'],
        'snapshot_sha256': digest(snapshot) if snapshot else '', 'transaction_hash': '',
        'forward': forward, 'reverse': reverse}
    return binding, _audit(binding), universe


def _audit(binding):
    return {'case_id': binding['case_id'], 'snapshot_sha256': binding['snapshot_sha256'],
        'transaction_hash': binding['transaction_hash'], 'entries': [
            {'direction': direction, 'id': row['id'], 'entry_sha256': digest(row),
             'verdict': 'confirmed', 'rationale': 'Synthetic separate semantic adjudicator verdict.'}
            for direction in ('forward', 'reverse') for row in binding[direction]]}


@pytest.fixture
def bound(tmp_path):
    case, snapshot = _normalized_snapshot(tmp_path)
    case.case_id = 'source-custody'
    annotation = {'operator_evidence_sha256': hashlib.sha256(combined_prompt_evidence_source(prompt=case.prompt, edit_evidence='').encode()).hexdigest(),
        'expected_outcome': 'commit', 'atoms': [
            {'id': key, 'evaluation_role': role, 'predicate': predicate, 'source': {'quote': quote}}
            for key, role, predicate, quote in (
                ('A0', 'reference_only', 'Background does not invent authority.', 'scope'),
                ('A1', 'scored', 'Preserve the entire withdrawal obligation.', 'Withdrawal closes scope and audience access'),
                ('A2', 'scored', 'Preserve separately named scope access.', 'scope'),
                ('A3', 'scored', 'Preserve separately named audience access.', 'audience'))],
        'obligations': ['Keep withdrawal effects and authorized restoration separate.'],
        'first_path_relations': [{'atom_id': 'A1', 'order': 1}, {'atom_id': 'A2', 'order': 2}],
        'context_relations': [{'atom_id': 'A3', 'kind': 'source_authority'}],
        'component_responsibilities': []}
    binding, audit, universe = _bind(case, annotation, snapshot)
    return case, annotation, snapshot, binding, audit, universe


def _validate(bound, binding=None, audit=None, snapshot=None):
    case, annotation, original, original_binding, original_audit, _ = bound
    return validate_source_predicate_binding_case(case=case, annotation=annotation,
        binding=binding or original_binding, audit=audit or original_audit, receipt={}, snapshot=snapshot or original)


def _score(annotation, binding):
    counts = {'atomic_semantic_fidelity': [0, 0], 'relation_fidelity': [0, 0]}
    failed, p0, p1 = [], [], []
    scored = score_source_predicates(case_id='source-custody', annotation=annotation, binding=binding,
        metric_counts=counts, failed_dimensions=failed, p0=p0, p1=p1)
    return counts, failed, p0, scored


def test_many_to_many_custody_uses_fixed_source_denominator(bound):
    assert _validate(bound) == ()
    _, annotation, _, binding, _, universe = bound
    counts, failed, _, scored = _score(annotation, binding)
    assert counts['atomic_semantic_fidelity'] == [3, 3]
    assert len(universe) > 30
    assert counts['relation_fidelity'] == [3, 3]
    assert not failed and len(scored[2]) == 64
    changed = deepcopy(binding)
    changed['forward'][1]['observed'] = changed['forward'][1]['observed'][:2]
    assert _validate(bound, binding=changed, audit=_audit(changed)) == ()
    assert _score(annotation, changed)[0] == counts


@pytest.mark.parametrize('control', ['missing_id', 'duplicate_id', 'unknown_id', 'reverse_missing',
    'reverse_reference', 'wrong_source_unit', 'missing_review', 'forged_review', 'changed_mapping',
    'paragraph_as_role_hash', 'main_support_swap', 'stale_transaction', 'duplicate_cycle'])
def test_invalid_source_binding_or_independent_audit_fails_closed(bound, control):
    *_, original, original_audit, universe = bound
    binding, audit = deepcopy(original), deepcopy(original_audit)
    if control == 'missing_id': binding['forward'].pop()
    elif control == 'duplicate_id': binding['forward'].append(deepcopy(binding['forward'][1]))
    elif control == 'unknown_id': binding['forward'][1]['id'] = 'atom:unknown'
    elif control == 'reverse_missing': binding['reverse'].pop()
    elif control == 'reverse_reference': binding['reverse'][0]['disposition'] = 'reference_only'
    elif control == 'wrong_source_unit': binding['forward'][1]['unit']['source_sha256'] = 'f' * 64
    elif control == 'missing_review': audit['entries'].pop()
    elif control == 'forged_review': audit['entries'][0]['entry_sha256'] = 'f' * 64
    elif control == 'changed_mapping': binding['forward'][1]['rationale'] += ' changed after review'
    elif control == 'paragraph_as_role_hash':
        row = next(row for row in binding['reverse'] if row['evidence']['normalized_role_sha256'])
        row['evidence']['normalized_role_sha256']['action_verb_quote'] = row['evidence']['source_witness_sha256']
    elif control == 'main_support_swap':
        row = next(row for row in binding['forward'] if row['unit']['kind'] == 'first_path_events')
        row['observed'] = [next(key for key, value in universe.items() if value['kind'] == 'supporting_event')]
    elif control == 'stale_transaction': binding['transaction_hash'] = 'f' * 64
    elif control == 'duplicate_cycle':
        one, two = binding['reverse'][:2]
        one.update(disposition='duplicate', duplicate_of=two['id'])
        two.update(disposition='duplicate', duplicate_of=one['id'])
    if control not in {'missing_review', 'forged_review', 'changed_mapping'}: audit = _audit(binding)
    assert _validate(bound, binding=binding, audit=audit)


@pytest.mark.parametrize('identity', ['atom:A1', 'atom:A2', 'atom:A3', 'obligation:1'])
def test_compound_and_separate_constituents_do_not_disappear(bound, identity):
    _, annotation, _, binding, _, _ = bound
    changed = deepcopy(binding)
    next(row for row in changed['forward'] if row['id'] == identity)['disposition'] = 'partial'
    assert _validate(bound, binding=changed, audit=_audit(changed)) == ()
    counts, failed, p0, scored = _score(annotation, changed)
    assert counts['atomic_semantic_fidelity'][1] == 3
    assert 'source_predicate_coverage' in failed and p0 and not scored[2]


@pytest.mark.parametrize('kind', ['semantic_fact', 'supporting_event', 'lifecycle_effect', 'provisional_design', 'context_relations'])
def test_complete_forward_coverage_cannot_mask_reverse_invention(bound, kind):
    _, annotation, _, binding, _, _ = bound
    changed = deepcopy(binding)
    next(row for row in changed['reverse'] if row['evidence']['kind'] == kind)['disposition'] = 'unsupported'
    assert _validate(bound, binding=changed, audit=_audit(changed)) == ()
    counts, failed, p0, scored = _score(annotation, changed)
    assert counts['atomic_semantic_fidelity'] == [3, 3]
    assert 'reverse_semantic_support' in failed and p0 and not scored[2]


def test_extra_non_atomic_semantic_fact_requires_reverse_enumeration(bound):
    snapshot = deepcopy(bound[2])
    snapshot['facts']['unledgered_advisory'] = 'An external operator may publish private identities.'
    _reseal(snapshot)
    assert '/facts/unledgered_advisory' in observed_semantic_universe(case=bound[0], snapshot=snapshot)
    binding = deepcopy(bound[3]); binding['snapshot_sha256'] = digest(snapshot)
    assert 'semantic reverse enumeration is incomplete' in _validate(bound, binding=binding, audit=_audit(binding), snapshot=snapshot)


def test_equivalence_identity_is_audited_and_independent_of_destination_layout(bound):
    _, annotation, _, binding, _, _ = bound
    _, _, _, one = _score(annotation, binding)
    changed = deepcopy(binding)
    changed['forward'][1]['observed'] = changed['forward'][1]['observed'][:1]
    assert _validate(bound, binding=changed, audit=_audit(changed)) == ()
    assert _score(annotation, changed)[3][2] == one[2]
    changed['forward'][1]['semantic_identity'] = 'changed-withdrawal-obligation'
    assert _score(annotation, changed)[3][2] != one[2]


@pytest.fixture
def audited_clarification(tmp_path):
    return _audited_clarification(tmp_path)


def _audited_clarification(tmp_path, *, question=None, source_case=None, snapshot=None, material_custody=None):
    case = source_case or _case('clarify', expectation='clarification_required')
    cases_ref = _save(tmp_path / 'source-cases.json', {'cases': [{'id': case.case_id, 'name': case.name,
        'prompt': case.prompt, 'required_terms': [case.prompt.split()[0]], 'leakage_terms': [case.prompt.split()[0]],
        'expectation': 'clarification_required'}]})
    cases = load_case_file(Path(cases_ref['path']))
    case = cases[0]
    declaration = _declare(case, cases_ref['sha256'])
    source_ref = _save(tmp_path / 'source.json', declaration)
    result = _clarification_result(case)
    if question is not None:
        result.evidence['clarification']['question'] = question
    snapshot = deepcopy(snapshot or {})
    binding, audit_case, _ = _bind(case, declaration['cases'][0], snapshot, result.evidence['clarification'])
    if material_custody is not None:
        snapshot['material_custody'] = material_custody
        binding['snapshot_sha256'] = digest(snapshot)
        audit_case = _audit(binding)
    if snapshot:
        result.evidence['preconfirm_dry_run'] = {'semantic_snapshot': snapshot,
            'semantic_snapshot_sha256': digest(snapshot), 'transaction_hash': ''}
    root = prepare_retained_evidence_output_dir(output_dir=tmp_path / 'retained', temp_parent=tmp_path / 'repos')
    retained_case = begin_retained_case_evidence(evidence_root=root, case_id=case.case_id)
    record_retained_case_text(retained_case, 'commands/clarify.stdout', 'one focused question')
    record_retained_case_json(retained_case, 'semantic/dry-run-receipt.v2.json', {'mode': 'clarification_required'})
    finalize_retained_case_evidence(case=retained_case, repo_root=tmp_path / 'empty-repo', result_payload=result.to_dict())
    manifest = write_retained_evidence_manifest(root=root, expected_case_ids=(case.case_id,))
    output_ref = _save(tmp_path / 'output.json', {'results': [result.to_dict()]})
    binding_ref = _save(tmp_path / 'bindings.json', {'version': PUBLIC_SOURCE_MODE + '.bindings.v1',
        'public_split': 'disclosed-public-live-subset', 'source_predeclaration_sha256': source_ref['sha256'],
        'output_sha256': output_ref['sha256'], 'binder_identity': 'synthetic-test-binder', 'cases': [binding]})
    reviewer = _review_package(base_path=Path(output_ref['path']), retained_manifest_path=manifest,
        case_manifest_path=retained_case.final_root / 'case-evidence-manifest.v1.json')['reviewer']
    review_record = {'version': PUBLIC_SOURCE_MODE + '.review-record.v1',
        'source_predeclaration_sha256': source_ref['sha256'], 'observed_bindings_sha256': binding_ref['sha256'],
        'output_sha256': output_ref['sha256'], 'retained_manifest_sha256': sha256_file(manifest),
        'reviewer_sha256': digest(reviewer), 'review_context_id': reviewer['review_context_id'],
        'reviewed_cases_sha256': digest([audit_case])}
    record_ref = _save(tmp_path / 'review-record.json', review_record)
    audit_ref = _save(tmp_path / 'audit.json', {'version': PUBLIC_SOURCE_MODE + '.audit.v1',
        'source_predeclaration_sha256': source_ref['sha256'], 'observed_bindings_sha256': binding_ref['sha256'],
        'output_sha256': output_ref['sha256'], 'retained_manifest_sha256': sha256_file(manifest),
        'review_record_sha256': record_ref['sha256'], 'reviewer': reviewer, 'cases': [audit_case]})
    config = {'mode': PUBLIC_SOURCE_MODE, 'predeclaration': source_ref, 'source_cases': cases_ref,
        'observed_bindings': binding_ref, 'independent_audit': audit_ref, 'output': output_ref,
        'retained_manifest': {'path': str(manifest), 'sha256': sha256_file(manifest)}, 'review_record': record_ref}
    return case, result, config


def test_saved_independent_audit_custody_is_separate_from_final_release_gate(audited_clarification):
    case, result, config = audited_clarification
    annotations, bindings, issues = load_source_predicate_evidence(configuration=config, cases=(case,), results=(result,))
    assert issues == () and set(annotations) == set(bindings) == {case.case_id}
    report = evaluate_semantic_release(cases=(case,), annotations={}, results=(result,),
        floors=EXACT_RELEASE_FLOORS, source_predicate_evidence=config, _include_model_profiles=False,
        _allow_not_applicable_metrics=True)
    assert report['scoring_status'] == 'scored'
    assert report['metrics']['clarification_identity']['rate'] == 1.0
    assert report['passed'] is False  # One unit fixture cannot satisfy frozen release floors/samples.


@pytest.mark.parametrize('artifact', ['predeclaration', 'source_cases', 'observed_bindings',
    'independent_audit', 'output', 'retained_manifest', 'review_record'])
def test_changed_or_forged_retained_artifact_never_scores(audited_clarification, artifact):
    case, result, config = audited_clarification
    Path(config[artifact]['path']).write_text('{}\n')
    report = evaluate_semantic_release(cases=(case,), annotations={}, results=(result,),
        floors=EXACT_RELEASE_FLOORS, source_predicate_evidence=config)
    assert report['scoring_status'] == 'unscored' and report['sample_count'] == 0
    assert not report['passed'] and 'file hash changed' in str(report['issues'])


@pytest.mark.parametrize('control', ['public_relabel', 'forged_quote', 'duplicate_id', 'missing_id', 'utf8_split'])
def test_source_only_preflight_rejects_unauthorized_changes(audited_clarification, control):
    case, _, config = audited_clarification
    path = Path(config['predeclaration']['path']); value = json.loads(path.read_text())
    if control == 'public_relabel': value['public_split'] = 'final_holdout'
    elif control == 'forged_quote': value['cases'][0]['atoms'][0]['source']['quote_sha256'] = 'f' * 64
    elif control == 'duplicate_id': value['cases'][0]['atoms'].append(deepcopy(value['cases'][0]['atoms'][0]))
    elif control == 'missing_id': value['cases'][0]['atoms'][0]['id'] = ''
    elif control == 'utf8_split': value['cases'][0]['atoms'][0]['source']['end_byte'] = 2
    path.write_text(json.dumps(value))
    _, issues = validate_source_predicate_predeclaration(cases=(case,), path=path, expected_sha256=config['predeclaration']['sha256'])
    assert issues
    native, native_issues = validate_atomic_annotations(cases=(case,), rows=value['cases'])
    assert native_issues  # Public predicates cannot masquerade as native protected truth.


@pytest.mark.parametrize('control', ['missing', 'weak', 'participated', 'same_context', 'unknown_model'])
def test_shared_independent_reviewer_owner_preserves_strict_eligibility(audited_clarification, control):
    *_, config = audited_clarification
    reviewer = json.loads(Path(config['independent_audit']['path']).read_text())['reviewer']
    if control == 'missing': reviewer = None
    elif control == 'weak': reviewer['reasoning_effort'] = 'low'
    elif control == 'participated': reviewer['independence']['execution_participation'] = 'producer'
    elif control == 'same_context': reviewer['review_context_id'] = config['output']['sha256']
    else: reviewer['model'] = 'invented-model'
    issues, awaiting = [], []
    validate_independent_reviewer(reviewer, forbidden_context_ids={config['output']['sha256']}, issues=issues, awaiting=awaiting)
    assert issues or awaiting


def test_source_and_representation_censuses_are_independently_verified():
    case = _case('census', expectation='transaction_committed')
    result = _commit_result(case)
    dimensions = deepcopy(result.evidence['preconfirm_dry_run']['semantic_snapshot']['operating_envelope']['complexity']['dimensions'])
    dimensions['actors'] += 1
    slices, issues = release_slice_evidence(case=case, result=result, annotated_complexity=dimensions,
        source_predicate_complexity=dimensions)
    assert issues == () and slices['complexity_band'] == greenfield_complexity_band(dimensions)
    result.evidence['preconfirm_dry_run']['semantic_snapshot']['operating_envelope']['complexity']['dimensions']['actors'] += 1
    _, issues = release_slice_evidence(case=case, result=result, annotated_complexity=dimensions,
        source_predicate_complexity=dimensions)
    assert 'sealed representation census or operating-envelope custody changed' in issues


def test_utf8_source_citation_must_end_on_a_complete_character(tmp_path):
    case = GreenfieldMatrixCase(name='unicode', case_id='unicode', prompt='A résumé reviewer opens access.', required_terms=('access',))
    declaration = _declare(case, 'a' * 64)
    path = tmp_path / 'source.json'
    ref = _save(path, declaration)
    assert validate_source_predicate_predeclaration(cases=(case,), path=path, expected_sha256=ref['sha256'])[1] == ()
    declaration['cases'][0]['atoms'][0]['source']['end_byte'] = case.prompt.encode().index('é'.encode()) + 1
    ref = _save(path, declaration)
    issues = validate_source_predicate_predeclaration(cases=(case,), path=path, expected_sha256=ref['sha256'])[1]
    assert any('decode' in issue for issue in issues)


@pytest.mark.parametrize('control', ['changed_disposition', 'wrong_reviewer', 'absent_review_record', 'binder_is_reviewer'])
def test_rehashed_audit_still_requires_original_independent_retained_scope(audited_clarification, control):
    case, result, config = audited_clarification
    path = Path(config['independent_audit']['path'])
    audit = json.loads(path.read_text())
    if control == 'changed_disposition': audit['cases'][0]['entries'][0]['verdict'] = 'confirmed-new'
    elif control == 'wrong_reviewer': audit['reviewer']['identity'] = 'new-unretained-reviewer'
    elif control == 'absent_review_record': config.pop('review_record')
    else:
        binding_path = Path(config['observed_bindings']['path'])
        binding = json.loads(binding_path.read_text())
        binding['binder_identity'] = audit['reviewer']['identity']
        config['observed_bindings'] = _save(binding_path, binding)
        audit['observed_bindings_sha256'] = config['observed_bindings']['sha256']
    config['independent_audit'] = _save(path, audit)
    annotations, bindings, issues = load_source_predicate_evidence(configuration=config, cases=(case,), results=(result,))
    assert issues


def test_reviewed_wrong_clarification_cannot_override_exact_frozen_question(tmp_path):
    case, result, config = _audited_clarification(tmp_path, question='Which public database should I invent?')
    assert load_source_predicate_evidence(configuration=config, cases=(case,), results=(result,))[2] == ()
    report = evaluate_semantic_release(cases=(case,), annotations={}, results=(result,), floors=EXACT_RELEASE_FLOORS,
        source_predicate_evidence=config, _include_model_profiles=False)
    assert report['scoring_status'] == 'scored' and report['metrics']['clarification_identity']['rate'] == 0.0
    assert not report['passed']


def test_nonmaterial_source_permission_can_bind_typed_lifecycle_without_relabeling(bound):
    _, annotation, _, binding, _, universe = bound
    annotation = deepcopy(annotation)
    annotation['atoms'][1].update(predicate='Preserve authorized restoration scope.', category='ambiguities',
        materiality='non_material', expected_custody='accepted_fact', expected_polarity='required')
    binding = deepcopy(binding)
    row = next(row for row in binding['forward'] if row['id'] == 'atom:A1')
    row['unit'] = source_predicate_units(annotation)['atom:A1']
    row['observed'] = [next(key for key, value in universe.items() if value['kind'] == 'lifecycle_boundaries')]
    assert validate_source_predicate_binding_case(case=bound[0], annotation=annotation, binding=binding,
        audit=_audit(binding), receipt={}, snapshot=bound[2]) == ()
    assert _score(annotation, binding)[0]['atomic_semantic_fidelity'] == [3, 3]
    assert annotation['atoms'][1]['category'] == 'ambiguities'


def test_unproven_advisory_assumption_cannot_become_accepted_scope(bound):
    case, annotation, snapshot, *_ = bound
    snapshot = deepcopy(snapshot)
    snapshot['facts']['assumptions'] = [{'applies_to': 'general', 'statement': 'Publication edits may be automatic.'}]
    _reseal(snapshot)
    annotation = deepcopy(annotation)
    annotation['atoms'][1]['expected_custody'] = 'accepted_fact'
    binding, audit, universe = _bind(case, annotation, snapshot)
    assumption = next(key for key, row in universe.items() if row['custody_state'] == 'assumption')
    forward = next(row for row in binding['forward'] if row['id'] == 'atom:A1')
    forward['observed'] = [assumption]
    next(row for row in binding['reverse'] if row['id'] == assumption)['disposition'] = 'source_supported'
    issues = validate_source_predicate_binding_case(case=case, annotation=annotation, binding=binding,
        audit=_audit(binding), receipt={}, snapshot=snapshot)
    assert any('advisory custody' in issue for issue in issues)
    assert any('reclassified an advisory assumption' in issue for issue in issues)


@pytest.mark.parametrize('kind', ['semantic_fact', 'atomic_fact', 'material_custody',
    'lifecycle_effect', 'supporting_event', 'provisional_design'])
def test_accepted_reverse_claim_cannot_hide_as_an_assumption_after_reaudit(bound, kind):
    if kind == 'material_custody':
        case, annotation, snapshot, *_ = bound
        snapshot = deepcopy(snapshot)
        snapshot['material_custody'] = {'state_object': {
            'custody_state': 'accepted_fact', 'entailment_relationship': 'direct_product_claim'}}
        original, audit, universe = _bind(case, annotation, snapshot)
        bound = case, annotation, snapshot, original, audit, universe
    _, annotation, _, original, _, _ = bound
    binding = deepcopy(original)
    row = next(row for row in binding['reverse']
        if row['evidence']['kind'] == kind and row['evidence']['custody_state'] == 'accepted_fact')
    row['disposition'] = 'assumption'
    issues = _validate(bound, binding=binding, audit=_audit(binding))
    assert any('non-assumption custody' in issue for issue in issues)
    counts, failed, p0, scored = _score(annotation, binding)
    assert counts['atomic_semantic_fidelity'] == [3, 3]
    assert 'reverse_semantic_support' in failed and p0 and not scored[2]


@pytest.mark.parametrize('accepted_is_duplicate', [True, False])
def test_duplicate_reverse_claim_preserves_actual_custody_after_reaudit(bound, accepted_is_duplicate):
    case, annotation, snapshot, *_ = bound
    snapshot = deepcopy(snapshot)
    snapshot['facts']['assumptions'] = [{'applies_to': 'general', 'statement': 'Publication edits may be automatic.'}]
    _reseal(snapshot)
    binding, _, _ = _bind(case, annotation, snapshot)
    accepted = next(row for row in binding['reverse'] if row['id'] == '/facts/title')
    assumption = next(row for row in binding['reverse'] if row['evidence']['custody_state'] == 'assumption')
    child, parent = (accepted, assumption) if accepted_is_duplicate else (assumption, accepted)
    child.update(disposition='duplicate', duplicate_of=parent['id'])
    issues = validate_source_predicate_binding_case(case=case, annotation=annotation, binding=binding,
        audit=_audit(binding), receipt={}, snapshot=snapshot)
    assert any('duplicate changes actual custody' in issue for issue in issues)
    _, failed, p0, scored = _score(annotation, binding)
    assert 'reverse_semantic_support' in failed and p0 and not scored[2]


def test_genuine_provisional_assumptions_and_duplicates_keep_advisory_custody(bound):
    case, annotation, snapshot, *_ = bound
    snapshot = deepcopy(snapshot)
    snapshot['facts']['assumptions'] = [{'applies_to': 'general', 'statement': 'Publication edits may be automatic.'}]
    _reseal(snapshot)
    binding, _, _ = _bind(case, annotation, snapshot)
    assumptions = [row for row in binding['reverse'] if row['evidence']['custody_state'] == 'assumption']
    assert len(assumptions) >= 2 and all(row['disposition'] == 'assumption' for row in assumptions)
    assumptions[0].update(disposition='duplicate', duplicate_of=assumptions[1]['id'])
    assert validate_source_predicate_binding_case(case=case, annotation=annotation, binding=binding,
        audit=_audit(binding), receipt={}, snapshot=snapshot) == ()
    counts, failed, p0, scored = _score(annotation, binding)
    assert counts['atomic_semantic_fidelity'] == [3, 3]
    assert not failed and not p0 and len(scored[2]) == 64


def test_genuine_material_assumption_retains_actual_advisory_custody(bound):
    case, annotation, snapshot, *_ = bound
    snapshot = deepcopy(snapshot)
    snapshot['material_custody'] = {'proof_boundary': {
        'custody_state': 'assumption', 'entailment_relationship': 'visible_assumption_from'}}
    binding, audit, universe = _bind(case, annotation, snapshot)
    identity = '/material_custody/proof_boundary'
    assert universe[identity]['custody_state'] == 'assumption'
    row = next(row for row in binding['reverse'] if row['id'] == identity)
    assert row['disposition'] == 'assumption'
    assert validate_source_predicate_binding_case(case=case, annotation=annotation, binding=binding,
        audit=audit, receipt={}, snapshot=snapshot) == ()
    _, failed, p0, scored = _score(annotation, binding)
    assert not failed and not p0 and len(scored[2]) == 64
    row['disposition'] = 'source_supported'
    issues = validate_source_predicate_binding_case(case=case, annotation=annotation, binding=binding,
        audit=_audit(binding), receipt={}, snapshot=snapshot)
    assert any('reclassified an advisory assumption' in issue for issue in issues)
    _, failed, p0, scored = _score(annotation, binding)
    assert 'reverse_semantic_support' in failed and p0 and not scored[2]


@pytest.mark.parametrize('public_mode', [False, True])
@pytest.mark.parametrize('receipt_kind', ['compiled_snapshot', 'transaction_hash', 'candidate_hash'])
def test_clarification_stops_before_any_nonempty_compile_receipt(public_mode, receipt_kind):
    case = _case('clarify-stop', expectation='clarification_required')
    result = _clarification_result(case)
    annotation = _declare(case, 'a' * 64)['cases'][0] if public_mode else _clarification_annotation()
    binding = _bind(case, annotation, {}, result.evidence['clarification'])[0] if public_mode else None
    receipt = _commit_result(case).evidence['preconfirm_dry_run'] if receipt_kind == 'compiled_snapshot' else {
        'transaction_hash' if receipt_kind == 'transaction_hash' else 'candidate_sha256': 'b' * 64}
    result.evidence['preconfirm_dry_run'] = receipt
    counts = {key: [0, 0] for key in ('atomic_semantic_fidelity', 'relation_fidelity',
        'clarification_identity', 'unnecessary_question_rate')}
    outcome = _score_case(case=case, case_id=case.case_id, annotation=annotation,
        result=result, metric_counts=counts, source_binding=binding)
    assert not outcome['passed'] and 'clarification_stop_boundary' in outcome['failed_dimensions']
    assert outcome['p0_findings'] and not outcome['normalized_semantic_digest']
    assert counts['clarification_identity'] == [0, 1]
    assert counts['atomic_semantic_fidelity'] == counts['relation_fidelity'] == [0, 0]


def test_actual_evidence_loader_refuses_malformed_material_custody(tmp_path):
    original_case, original_snapshot = _legacy_snapshot()
    source_case = _case('malformed-material', expectation='clarification_required', prompt=original_case.prompt)
    case, result, config = _audited_clarification(tmp_path, source_case=source_case, snapshot=original_snapshot,
        material_custody={'state_object': 'malformed'})
    snapshot = result.evidence['preconfirm_dry_run']['semantic_snapshot']
    assert snapshot_relation_evidence(case=case, snapshot=snapshot).issues == ()
    _, _, issues = load_source_predicate_evidence(configuration=config, cases=(case,), results=(result,))
    assert any('material custody' in issue and 'state_object' in issue for issue in issues)
    report = evaluate_semantic_release(cases=(case,), annotations={}, results=(result,),
        floors=EXACT_RELEASE_FLOORS, source_predicate_evidence=config)
    assert report['scoring_status'] == 'unscored' and report['sample_count'] == 0 and not report['passed']
    assert any('material custody' in issue and 'state_object' in issue for issue in report['issues'])
