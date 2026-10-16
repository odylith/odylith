"""Synthetic hosted package custody; no live GitHub, signer or release build."""
from pathlib import Path
import json
import sys

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import publish_release_assets as publisher


def test_hosted_provenance_captures_real_clean_source_before_signing(monkeypatch, tmp_path):
    head = 'a' * 40
    monkeypatch.setenv('GITHUB_SHA', head)
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    monkeypatch.setattr(publisher, '_git_output', lambda args: '' if args[0] in ('status', 'branch') else head)
    wheel = tmp_path / 'odylith-0.1.15-py3-none-any.whl'
    wheel.write_bytes(b'synthetic wheel byte identity')
    path = tmp_path / 'provenance.json'
    publisher._write_provenance(output_path=path, tag='v0.1.15', repo='odylith/odylith',
        allow_local=False, feature_packs=[], wheel=wheel, runtime_bundles=[])
    payload = json.loads(path.read_text())
    assert payload['source_tree']['head'] == head
    assert payload['source_tree']['dirty'] is False
    assert payload['workflow']['run_id'] == '123'
    assert payload['workflow']['run_attempt'] == '1'

from copy import deepcopy
import hashlib
from types import SimpleNamespace

import hosted_release_custody as hosted
import greenfield_release_qualification as assembly
from tests.unit.install.test_greenfield_release_assembly import canonical_package, _canonical_custody_refs
from greenfield_matrix_release_artifacts import sha256_file


@pytest.fixture
def hosted_transport(canonical_package, monkeypatch, tmp_path):
    """Mock only GitHub transport/external signatures; custody owners execute normally."""
    value = canonical_package
    monkeypatch.setattr(hosted, 'REPO_ROOT', value['repo'])
    for key, item in {'GITHUB_ACTIONS': 'true', 'GITHUB_REPOSITORY': 'odylith/odylith',
        'GITHUB_ACTOR': 'freedom-research', 'GITHUB_REF': 'refs/heads/main',
        'GITHUB_SHA': value['revision'], 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '1',
        'RELEASE_EXPECTED_SHA': value['revision'], 'RELEASE_TAG': 'v0.1.15', 'RELEASE_OPERATION': 'promote'}.items():
        monkeypatch.setenv(key, item)
    monkeypatch.delenv('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY', raising=False)
    state = {'assets': {}, 'release': None, 'calls': [], 'next': 1000, 'publish': 0}
    def upload(release_id, path):
        assert state['release']['id'] == release_id
        assert path.name not in [row['name'] for row in state['assets'].values()]
        data = path.read_bytes();state['next'] += 1
        row = {'name': path.name, 'id': state['next'], 'size': len(data),
            'digest': 'sha256:' + hashlib.sha256(data).hexdigest(), 'state': 'uploaded', 'bytes': data}
        state['assets'][row['id']] = row
        return hosted._row(row)
    def gh(*args, payload=None, destination=None):
        path = args[0];state['calls'].append((args, deepcopy(payload)))
        if '/releases?' in path:
            return [] if state['release'] is None else [deepcopy(state['release'])]
        if path.endswith('/releases') and payload:
            if state['release'] is not None:raise RuntimeError('existing candidate')
            state['release'] = {'id': 99, **payload}
            return deepcopy(state['release'])
        if '/actions/runs/' in path and path.endswith('/logs'):
            import zipfile
            with zipfile.ZipFile(destination,'w') as archive:archive.writestr('release/build.txt','synthetic successful hosted log')
            return None
        if '/actions/runs/' in path and '/jobs?' in path:
            return {'total_count':1,'jobs':[{'run_id':123,'run_attempt':1,'status':'completed','conclusion':'success',
                'steps':[{'name':name,'status':'completed','conclusion':'success'} for name in hosted.BUILD_STEPS.values()]}]}
        if '/actions/runs/' in path:
            return {'id': 123, 'run_attempt': 1, 'head_sha': value['revision'], 'head_branch': 'main',
                'event': 'workflow_dispatch', 'path': '.github/workflows/release.yml',
                'repository': {'full_name': 'odylith/odylith'}, 'actor': {'login': 'freedom-research'},
                'status': 'completed', 'conclusion': 'success'}
        if '/releases/assets/' in path:
            data = state['assets'][int(path.rsplit('/', 1)[1])]['bytes']
            with destination.open('xb') as f:f.write(data)
            return None
        if '/assets?' in path:
            return [{key: item for key, item in row.items() if key != 'bytes'} for row in state['assets'].values()]
        if '/releases/' in path:
            if payload:
                assert payload.get('draft') is False
                state['release'].update(payload);state['publish'] += 1
            return deepcopy(state['release'])
        raise AssertionError(args)
    def sign(path):
        bundle = path.with_name(path.name + '.sigstore.json')
        bundle.write_text('{"synthetic_external_signature":true}\n')
        return bundle
    monkeypatch.setattr(hosted, '_gh', gh)
    monkeypatch.setattr(hosted, '_upload', upload)
    monkeypatch.setattr(hosted, '_sign_asset', sign)
    reservation_path = tmp_path / 'reservation.json'
    reservation = hosted.reserve_candidate(tag='v0.1.15', revision=value['revision'], output=reservation_path)
    record = hosted.stage_candidate(reservation=reservation, dist=value['dist'])
    return {**value, 'state': state, 'reservation': reservation, 'record': record, 'temporary': tmp_path}


def _acquire(value, destination):
    destination.mkdir(parents=True)
    return hosted.acquire_candidate(run_id=123, revision=value['revision'], tag='v0.1.15', proof_root=destination)


def test_real_hosted_stage_acquire_seal_composition_and_promotion_roundtrip(hosted_transport, monkeypatch):
    value = hosted_transport
    session = value['temporary'] / 'acquired-locks/release-session.json'
    session.parent.mkdir()
    session.write_text(json.dumps({'head_sha': value['revision'], 'version': '0.1.15'}))
    root = session.parent / 'greenfield-release' / value['revision']
    acquired = _acquire(value, root)
    assert len(acquired['distribution_assets']) == value['record']['asset_count']
    (root / 'package-logs/local-smoke.log').write_text('synthetic local installed-smoke boundary\n')
    kwargs = dict(value['kwargs'], proof_root=root, session_path=session)
    receipt = assembly.prepare_release_package(**kwargs)
    assert receipt['hosted_candidate'] == acquired
    assert assembly.verify_prepared_release_package(**kwargs) == receipt
    # Real package/composition custody. This is not a semantic family/holdout grade.
    current = dict(value, root=root, dist=root / 'dist', receipt=receipt)
    import greenfield_public_qualification as public
    common = public._composition_release_custody(_canonical_custody_refs(current))
    assert common['commit'] == value['revision']
    before = {path.name: path.read_bytes() for path in (root / 'dist').iterdir()}
    qualification = {'status': 'passed', 'implementation_revision': value['revision'],
        'scope': 'synthetic local verifier result; no protected semantic proof'}
    binding = hosted.promotion_binding(prepared=receipt,
        prepared_sha256=sha256_file(root / 'prepared-package.v3.json'), qualification=qualification)
    def forbidden(*args, **kwargs):
        pytest.fail('promotion reached a package/signing/upload producer')
    monkeypatch.setattr(hosted, '_sign_asset', forbidden)
    monkeypatch.setattr(hosted, '_upload', forbidden)
    monkeypatch.setattr(publisher, 'main', forbidden)
    result = hosted.promote_candidate(binding)
    assert result['status'] == 'published_exact_candidate'
    assert value['state']['publish'] == 1
    assert all(path.read_bytes() == before[path.name] for path in (root / 'dist').iterdir())
    assert all(value['state']['assets'][row['id']]['bytes'] == before[row['name']] for row in binding['distribution_assets'])
    with pytest.raises(RuntimeError, match='draft'):
        hosted.promote_candidate(binding)
    assert value['state']['publish'] == 1


@pytest.mark.parametrize('phase', list(hosted.BUILD_STEPS.values()))
@pytest.mark.parametrize('defect', ['failure', 'missing', 'duplicate'])
def test_acquisition_requires_each_actual_successful_hosted_step(hosted_transport, monkeypatch, phase, defect):
    original = hosted._gh
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        if '/jobs?' in args[0]:
            steps = result['jobs'][0]['steps']
            selected = next(step for step in steps if step['name'] == phase)
            if defect == 'failure':
                selected['conclusion'] = 'failure'
            elif defect == 'missing':
                steps.remove(selected)
            else:
                steps.append(deepcopy(selected))
        return result
    monkeypatch.setattr(hosted, '_gh', changed)
    root = hosted_transport['temporary'] / 'failed-step'
    with pytest.raises(RuntimeError, match='successful hosted build step'):
        _acquire(hosted_transport, root)
    assert not (root / 'hosted-acquisition.v1.json').exists()
    assert not (root / 'prepared-package.v3.json').exists()
    assert hosted_transport['state']['publish'] == 0


def test_real_sigstore_subprocess_contract_pins_workflow_and_issuer(monkeypatch, tmp_path):
    from odylith.install import release_assets
    path = tmp_path / 'asset'
    path.write_text('signed bytes')
    bundle = tmp_path / 'asset.sigstore.json'
    bundle.write_text('{"synthetic_bundle":true}')
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.delenv('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY', raising=False)
    monkeypatch.setattr(release_assets.subprocess, 'run', run)
    release_assets.verify_sigstore_asset(repo_root=hosted.REPO_ROOT, asset_path=path,
        bundle_path=bundle, repo='odylith/odylith')
    command, kwargs = calls[0]
    assert command == [sys.executable, '-I', '-m', 'sigstore', 'verify', 'identity', str(path),
        '--bundle', str(bundle), '--cert-identity',
        'https://github.com/odylith/odylith/.github/workflows/release.yml@refs/heads/main',
        '--cert-oidc-issuer', 'https://token.actions.githubusercontent.com']
    assert kwargs['check'] is False
    monkeypatch.setattr(release_assets.subprocess, 'run', lambda *args, **kwargs:
        SimpleNamespace(returncode=1, stdout='', stderr='identity or issuer does not match'))
    with pytest.raises(ValueError, match='identity or issuer does not match'):
        release_assets.verify_sigstore_asset(repo_root=hosted.REPO_ROOT, asset_path=path,
            bundle_path=bundle, repo='odylith/odylith')


@pytest.mark.parametrize('defect', ['signature', 'bypass'])
def test_acquisition_cannot_seal_unverified_signature(hosted_transport, monkeypatch, defect):
    if defect == 'bypass':
        monkeypatch.setenv('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY', '1')
    else:
        def failed(**kwargs):
            raise ValueError('synthetic cryptographic rejection')
        monkeypatch.setattr(hosted, 'verify_sigstore_asset', failed)
    root = hosted_transport['temporary'] / 'unsigned'
    with pytest.raises((ValueError, RuntimeError), match='bypass|cryptographic rejection'):
        _acquire(hosted_transport, root)
    assert not (root / 'hosted-acquisition.v1.json').exists()
    assert hosted_transport['state']['publish'] == 0


@pytest.mark.parametrize('point', ['before_publish', 'after_publish', 'published_bytes'])
def test_promotion_refuses_racing_or_failed_readback_without_replay(hosted_transport, monkeypatch, point):
    value = hosted_transport
    acquisition = _acquire(value, value['temporary'] / 'race-acquired')
    binding = hosted.promotion_binding(prepared={'hosted_candidate': acquisition}, prepared_sha256='a'*64,
        qualification={'status': 'passed', 'implementation_revision': value['revision']})
    original = hosted._gh
    reads = 0
    def changed(*args, **kwargs):
        nonlocal reads
        path = args[0]
        result = original(*args, **kwargs)
        if '/assets?' in path:
            reads += 1
            # First census authenticates downloaded D. The second is the last pre-publish census.
            if (point == 'before_publish' and reads == 2) or (point == 'after_publish' and value['state']['publish']):
                result[0]['digest'] = 'sha256:' + '0'*64
        if point == 'published_bytes' and '/releases/assets/' in path and value['state']['publish']:
            kwargs['destination'].write_bytes(b'changed after publication')
        return result
    monkeypatch.setattr(hosted, '_gh', changed)
    with pytest.raises(RuntimeError, match='candidate changed before|published complete|downloaded release asset'):
        hosted.promote_candidate(binding)
    assert value['state']['publish'] == (0 if point == 'before_publish' else 1)
    assert not any('--clobber' in args for args, _ in value['state']['calls'])


def test_authenticated_transport_uses_fixed_github_host_and_exclusive_download(monkeypatch, tmp_path):
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        if kwargs['stdout'] != __import__('subprocess').PIPE:
            kwargs['stdout'].write(b'authenticated bytes')
        return SimpleNamespace(stdout=b'{"id":99}')
    monkeypatch.setenv('GH_HOST', 'attacker.invalid')
    monkeypatch.setenv('GH_REPO', 'attacker/project')
    monkeypatch.setattr(hosted.subprocess, 'run', run)
    assert hosted._gh(hosted._api('releases/99')) == {'id': 99}
    path = tmp_path / 'download'
    hosted._gh(hosted._api('releases/assets/100'), '-H', 'Accept: application/octet-stream', destination=path)
    assert path.read_bytes() == b'authenticated bytes'
    with pytest.raises(FileExistsError):
        hosted._gh(hosted._api('releases/assets/100'), destination=path)
    assert len(calls) == 2
    for command, kwargs in calls:
        assert command[:4] == ['gh', 'api', '--hostname', 'github.com']
        assert command[4].startswith('repos/odylith/odylith/')
        assert kwargs['env']['GH_HOST'] == 'github.com'
        assert kwargs['env']['GH_REPO'] == 'odylith/odylith'
        assert kwargs['check'] is True and kwargs['timeout'] == 180


@pytest.mark.parametrize('key,value', [('GITHUB_REPOSITORY', 'other/repo'), ('GITHUB_ACTOR', 'other'),
    ('GITHUB_REF', 'refs/heads/other'), ('GITHUB_ACTIONS', 'false')])
def test_candidate_authority_refuses_noncanonical_context(hosted_transport, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    before = len(hosted_transport['state']['calls'])
    with pytest.raises(ValueError):
        hosted.reserve_candidate(tag='v0.1.15', revision=hosted_transport['revision'],
            output=hosted_transport['temporary'] / 'unauthorized.json')
    assert len(hosted_transport['state']['calls']) == before


@pytest.mark.parametrize('tag,revision,run_id', [('v1;touch pwn', 'a'*40, 123), ('v0.1.15', 'HEAD', 123),
    ('v0.1.15', 'a'*40, True), ('v0.1.15', 'a'*40, 0)])
def test_acquisition_rejects_unsafe_identity_before_transport(hosted_transport, tag, revision, run_id):
    root = hosted_transport['temporary'] / 'unsafe'
    root.mkdir()
    before = len(hosted_transport['state']['calls'])
    with pytest.raises(RuntimeError):
        hosted.acquire_candidate(tag=tag, revision=revision, run_id=run_id, proof_root=root)
    assert len(hosted_transport['state']['calls']) == before
    assert not list(root.iterdir())


@pytest.mark.parametrize('defect', ['extra', 'missing', 'id', 'size', 'digest', 'bytes', 'partial', 'unsafe', 'duplicate'])
def test_acquisition_refuses_changed_complete_remote_census(hosted_transport, defect):
    value = hosted_transport;assets = value['state']['assets']
    row = next(row for row in assets.values() if row['name'] == 'install.sh')
    if defect == 'extra':
        assets[9999] = dict(row, id=9999, name='unexpected.bin')
    elif defect == 'missing':del assets[row['id']]
    elif defect == 'id':row['id'] += 5000
    elif defect == 'size':row['size'] += 1
    elif defect == 'digest':row['digest'] = 'sha256:' + '0' * 64
    elif defect == 'bytes':row['bytes'] += b'changed'
    elif defect == 'partial':row['state'] = 'starter'
    elif defect == 'unsafe':row['name'] = '../escape'
    else:assets[9999] = dict(row, id=9999)
    with pytest.raises((RuntimeError, KeyError)):
        _acquire(value, value['temporary'] / 'refused')
    assert value['state']['publish'] == 0


@pytest.mark.parametrize('field,value', [('head_sha', 'b'*40), ('run_attempt', 2), ('head_branch', 'other'),
    ('event', 'push'), ('path', '.github/workflows/other.yml'), ('conclusion', 'failure'), ('status', 'in_progress')])
def test_acquisition_requires_exact_successful_builder(hosted_transport, monkeypatch, field, value):
    original = hosted._gh
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        if '/actions/runs/' in args[0] and '/jobs?' not in args[0] and not args[0].endswith('/logs'):result[field] = value
        return result
    monkeypatch.setattr(hosted, '_gh', changed)
    with pytest.raises(RuntimeError, match='build run|build attempt'):
        _acquire(hosted_transport, hosted_transport['temporary'] / 'refused')
    assert hosted_transport['state']['publish'] == 0


@pytest.mark.parametrize('field', ['prepared_package_sha256', 'qualification_sha256', 'release_id', 'build_run_id', 'build_run_attempt', 'distribution_assets'])
def test_promotion_refuses_changed_tuple_without_mutation(hosted_transport, field):
    value = hosted_transport
    acquisition = _acquire(value, value['temporary'] / 'negatively-acquired')
    binding = hosted.promotion_binding(prepared={'hosted_candidate': acquisition}, prepared_sha256='a'*64,
        qualification={'status':'passed', 'implementation_revision':value['revision']})
    if field in ('prepared_package_sha256', 'qualification_sha256'):binding[field] = 'not-a-digest'
    elif field in ('release_id', 'build_run_id', 'build_run_attempt'):binding[field] += 1
    elif field == 'distribution_assets':binding[field][0]['sha256'] = '0'*64
    with pytest.raises((RuntimeError, KeyError)):
        hosted.promote_candidate(binding)
    assert value['state']['publish'] == 0


def test_crypto_contract_reuses_exact_canonical_verifier_and_refuses_bypass(monkeypatch, tmp_path):
    path = tmp_path / 'asset';path.write_text('payload')
    bundle = tmp_path / 'asset.sigstore.json';bundle.write_text('{"fixture":"signed"}')
    calls=[]
    monkeypatch.setattr(hosted, 'verify_sigstore_asset', lambda **kwargs: calls.append(kwargs))
    hosted._verify_signature(path,bundle)
    assert calls == [{'repo_root':hosted.REPO_ROOT,'asset_path':path,'bundle_path':bundle,'repo':'odylith/odylith'}]
    monkeypatch.setenv('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY','1')
    with pytest.raises(RuntimeError,match='bypass'):hosted._verify_signature(path,bundle)
    assert len(calls)==1
    monkeypatch.delenv('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY')
    bundle.write_text('{}\n')
    with pytest.raises(RuntimeError,match='placeholder'):hosted._verify_signature(path,bundle)
    assert len(calls)==1


def test_candidate_reservation_refuses_existing_before_second_build(hosted_transport):
    value=hosted_transport
    with pytest.raises(RuntimeError,match='existing candidate'):
        hosted.reserve_candidate(tag='v0.1.15',revision=value['revision'],output=value['temporary']/'second.json')
    assert value['state']['publish']==0
    with pytest.raises(RuntimeError,match='already uploaded'):
        hosted.stage_candidate(reservation=value['reservation'],dist=value['dist'])


def test_promotion_entrypoint_requires_local_verdict_then_reauthenticates_v3(canonical_package, monkeypatch, capsys):
    value = canonical_package
    prepared = assembly.prepare_release_package(**value['kwargs'])
    path = value['root'] / 'prepared-package.v3.json'
    args = ['--sidecar', str(value['root'] / 'synthetic-sidecar.json'),
        '--final-holdout-ledger', str(value['root'] / 'synthetic-ledger.json'),
        '--distribution-provenance', str(value['root'] / 'build-provenance.v1.json'),
        '--implementation-revision', value['revision'], '--promotion-binding']
    def reject(**kwargs):
        raise RuntimeError('local qualification rejected')
    monkeypatch.setattr(assembly, 'verify_release_qualification', reject)
    with pytest.raises(RuntimeError, match='local qualification rejected'):
        assembly.main(args)
    assert capsys.readouterr().out == ''
    # Isolate the existing semantic verdict boundary; actual v3 revalidation remains unmocked.
    verdict = {'status': 'passed', 'implementation_revision': value['revision'], 'scope': 'synthetic verdict only'}
    monkeypatch.setattr(assembly, 'verify_release_qualification', lambda **kwargs: verdict)
    assert assembly.main(args) == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted == hosted.promotion_binding(prepared=prepared, prepared_sha256=sha256_file(path), qualification=verdict)
    (value['dist'] / 'install.sh').write_text('changed after qualification')
    with pytest.raises(RuntimeError):
        assembly.main(args)
    assert capsys.readouterr().out == ''


def test_workflow_promotion_has_no_generation_and_data_is_not_shell_code():
    text=(Path(__file__).resolve().parents[3]/'.github/workflows/release.yml').read_text()
    assert 'options: [candidate, promote]' in text
    assert '    defaults:\n      run:\n        shell: bash\n' in text
    for block in text.split('      - name: ')[1:]:
        if any(token in block for token in ('hatch build --target','publish_release_assets.py','hosted_release_custody.py reserve','hosted_release_custody.py stage','local_release_smoke.py')):
            assert "if: inputs.operation == 'candidate'" in block
    promotion=text.split('- name: Promote exact')[1]
    assert "if: inputs.operation == 'promote'" in promotion
    assert 'hosted_release_custody.py promote' in promotion
    assert not any(token in '\n'.join(line for line in promotion.splitlines() if 'run:' in line) for token in ('hatch build','publish_release_assets','sigstore','--clobber'))
    assert '|| true' not in text
    assert 'cancel-in-progress: false' in text
    assert text.count('hatch build --target wheel') == 1
    assert text.count('publish_release_assets.py') == 1
    run_lines=[line for line in text.splitlines() if 'run:' in line]
    assert all('${{ inputs.' not in line for line in run_lines)


@pytest.mark.parametrize('phase', list(hosted.BUILD_STEPS.values()))
def test_actual_candidate_pipeline_preserves_failed_producer_status(tmp_path, phase):
    import os
    import subprocess
    workflow = (Path(__file__).resolve().parents[3] / '.github/workflows/release.yml').read_text()
    assert '    defaults:\n      run:\n        shell: bash\n' in workflow
    block = workflow.split('      - name: ' + phase + '\n', 1)[1].split('      - name:', 1)[0]
    command = next(line.split('run: ', 1)[1] for line in block.splitlines() if 'run: ' in line)
    binary = tmp_path / 'bin'
    binary.mkdir()
    hatch = binary / 'hatch'
    hatch.write_text('#!/bin/sh\nprintf "synthetic producer failure\\n"\nexit 23\n')
    hatch.chmod(0o755)
    (tmp_path / 'odylith-candidate-logs').mkdir()
    marker = tmp_path / 'staged'
    environment = dict(os.environ, PATH=str(binary) + ':' + os.environ['PATH'], RUNNER_TEMP=str(tmp_path),
        RELEASE_TAG='v0.1.15', RELEASE_REPO='odylith/odylith', MARKER=str(marker), ODYLITH_RELEASE_REPO='odylith/odylith')
    # GitHub's explicit bash template is bash --noprofile --norc -eo pipefail.
    result = subprocess.run(['bash', '--noprofile', '--norc', '-e', '-o', 'pipefail', '-c',
        command + '\ntouch "$MARKER"'], env=environment, capture_output=True, text=True)
    assert result.returncode == 23, result.stderr
    assert 'synthetic producer failure' in result.stdout
    assert not marker.exists()


@pytest.mark.parametrize('defect', ['existing_assets', 'dirty_source', 'wrong_head', 'unsafe_tag', 'local_mode'])
def test_candidate_publisher_refuses_before_any_generation_or_signing(hosted_transport, monkeypatch, tmp_path, defect):
    dist = tmp_path / 'publisher-input'
    dist.mkdir()
    (dist / 'odylith-0.1.15-py3-none-any.whl').write_bytes(b'synthetic wheel input')
    source = {'head': hosted_transport['revision'], 'dirty': False}
    arguments = ['--candidate', '--tag', 'v0.1.15', '--dist-dir', str(dist)]
    if defect == 'existing_assets':
        (dist / 'unexpected').write_text('preserve')
    elif defect == 'dirty_source':
        source['dirty'] = True
    elif defect == 'wrong_head':
        source['head'] = 'b' * 40
    elif defect == 'unsafe_tag':
        arguments[2] = 'v0.1.15;touch injected'
    else:
        arguments += ['--allow-local']
    monkeypatch.setattr(publisher, '_local_source_tree', lambda **kwargs: source)
    def forbidden(*args, **kwargs):
        pytest.fail('invalid candidate reached generation/signing')
    monkeypatch.setattr(publisher, '_build_managed_runtime_feature_packs', forbidden)
    monkeypatch.setattr(publisher, '_build_managed_runtime_bundles', forbidden)
    monkeypatch.setattr(publisher, '_sign_asset', forbidden)
    before = {path.name: path.read_bytes() for path in dist.iterdir()}
    with pytest.raises((ValueError, RuntimeError), match='fresh one-wheel|clean H|stable release tag|local placeholder'):
        publisher.main(arguments)
    assert {path.name: path.read_bytes() for path in dist.iterdir()} == before
