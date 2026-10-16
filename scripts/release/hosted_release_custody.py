"""Own one canonical signed draft, its complete acquisition, and exact promotion."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / 'src'))

from greenfield_distribution_provenance import _json_object, _package_bindings, verify_distribution_provenance, _unique_json_pairs
from greenfield_matrix_release_artifacts import sha256_file, _safe_file_without_symlinks, _path_without_symlink_segments
from odylith.install.release_assets import verify_sigstore_asset

AUTHORITATIVE_RELEASE_REPO = 'odylith/odylith'
AUTHORITATIVE_RELEASE_ACTOR = 'freedom-research'
WORKFLOW_PATH = '.github/workflows/release.yml'
WORKFLOW_REF = 'refs/heads/main'
OIDC_ISSUER = 'https://token.actions.githubusercontent.com'
LOCAL_VERSION = 'odylith.hosted-release-acquisition.v1'
PROMOTION_VERSION = 'odylith.hosted-release-promotion.v1'
BUILD_STEPS = {'wheel': 'Build one wheel', 'assets': 'Generate and sign candidate assets once', 'smoke': 'Verify signed installed candidate'}
CANDIDATE_FIELDS = {'version', 'repository', 'tag', 'implementation_revision', 'source_tree', 'release_id', 'build_run_id', 'build_run_attempt', 'distribution_assets', 'workflow_evidence'}
ROW_FIELDS = {'name', 'id', 'size', 'sha256'}
PROMOTION_FIELDS = {'version', 'tag', 'implementation_revision', 'release_id', 'build_run_id', 'build_run_attempt', 'distribution_assets', 'prepared_package_sha256', 'qualification_sha256'}


def _repo_signer_identity(repo):
    return f'https://github.com/{repo}/{WORKFLOW_PATH}@{WORKFLOW_REF}'


def _identity(tag, revision):
    if not isinstance(tag, str) or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+', tag):
        raise RuntimeError('canonical candidate requires a stable release tag')
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise RuntimeError('canonical candidate requires exact H')


def _number(value):
    if type(value) is not int or value <= 0:
        raise RuntimeError('hosted custody requires a positive integer ID')
    return value


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise RuntimeError('hosted custody requires exact SHA256')
    return value


def _require_canonical_release_context(*, repo: str) -> None:
    if repo != AUTHORITATIVE_RELEASE_REPO:
        raise ValueError(
            f"release assets may only be published for the canonical repo `{AUTHORITATIVE_RELEASE_REPO}`, got `{repo}`"
        )
    if os.getenv("GITHUB_ACTIONS", "").strip().lower() != "true":
        raise ValueError("release asset publishing is only allowed from the canonical GitHub Actions workflow")
    github_repo = str(os.getenv("GITHUB_REPOSITORY") or "").strip()
    if github_repo != AUTHORITATIVE_RELEASE_REPO:
        raise ValueError(
            f"release asset publishing requires GITHUB_REPOSITORY={AUTHORITATIVE_RELEASE_REPO}, got `{github_repo or '<empty>'}`"
        )
    github_actor = str(os.getenv("GITHUB_ACTOR") or "").strip()
    if github_actor != AUTHORITATIVE_RELEASE_ACTOR:
        raise ValueError(
            f"release asset publishing requires GITHUB_ACTOR={AUTHORITATIVE_RELEASE_ACTOR}, got `{github_actor or '<empty>'}`"
        )
    github_ref = str(os.getenv("GITHUB_REF") or "").strip()
    if github_ref != WORKFLOW_REF:
        raise ValueError(
            f"release asset publishing requires GITHUB_REF={WORKFLOW_REF}, got `{github_ref or '<empty>'}`"
        )


def _gh(*args, payload=None, destination=None):
    # Only fixed GitHub API paths are accepted; no caller URL or inherited host.
    environment = dict(os.environ, GH_HOST='github.com', GH_REPO=AUTHORITATIVE_RELEASE_REPO)
    command = ['gh', 'api', '--hostname', 'github.com', *args]
    data = None if payload is None else json.dumps(payload).encode()
    if payload is not None:
        command += ['--input', '-']
    if destination is not None:
        with Path(destination).open('xb') as stream:
            subprocess.run(command, input=data, stdout=stream, env=environment, check=True, timeout=180)
        return None
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE, env=environment, check=True, timeout=180)
    return json.loads(result.stdout, object_pairs_hook=_unique_json_pairs)


def _api(path):
    return 'repos/' + AUTHORITATIVE_RELEASE_REPO + '/' + path


def _release(release_id, tag, revision, *, draft):
    _identity(tag, revision)
    value = _gh(_api('releases/' + str(_number(release_id))))
    if (value.get('id') != release_id or value.get('tag_name') != tag or value.get('draft') is not draft
            or value.get('target_commitish') != revision):
        raise RuntimeError('hosted release identity, target or draft state changed')
    return value


def _run(run_id, attempt, revision, *, complete=True):
    value = _gh(_api(f'actions/runs/{_number(run_id)}/attempts/{_number(attempt)}'))
    if (value.get('id') != run_id or value.get('run_attempt') != attempt or value.get('head_sha') != revision
            or value.get('head_branch') != 'main' or value.get('event') != 'workflow_dispatch'
            or value.get('path') != WORKFLOW_PATH
            or value.get('repository', {}).get('full_name') != AUTHORITATIVE_RELEASE_REPO
            or value.get('actor', {}).get('login') != AUTHORITATIVE_RELEASE_ACTOR
            or (complete and (value.get('status') != 'completed' or value.get('conclusion') != 'success'))):
        raise RuntimeError('candidate build run identity or successful attempt changed')
    return value


def _asset_rows(release_id):
    rows, page = [], 1
    while True:
        values = _gh(_api(f'releases/{_number(release_id)}/assets?per_page=100&page={page}'))
        if not isinstance(values, list):
            raise RuntimeError('release asset census is not a list')
        rows.extend(values)
        if len(values) < 100:
            break
        page += 1
    names, ids = set(), set()
    for row in rows:
        name = row.get('name')
        if (not isinstance(name, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.+-]*', name)
                or name in names or _number(row.get('id')) in ids
                or row.get('state') != 'uploaded' or type(row.get('size')) is not int or row['size'] <= 0):
            raise RuntimeError('release has unsafe, duplicate, partial or empty assets')
        names.add(name); ids.add(row['id'])
    return {row['name']: row for row in rows}


def _row(row):
    value = {'name': row['name'], 'id': row['id'], 'size': row['size'], 'sha256': str(row.get('digest', '')).removeprefix('sha256:')}
    _digest(value['sha256'])
    return value


def _rows(rows):
    if not isinstance(rows, list) or not rows:
        raise RuntimeError('candidate asset census is missing')
    names, ids = set(), set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != ROW_FIELDS
                or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.+-]*', row.get('name', ''))
                or row['name'] in names or _number(row['id']) in ids
                or type(row['size']) is not int or row['size'] <= 0):
            raise RuntimeError('candidate asset census is unsafe or repeated')
        _digest(row['sha256']); names.add(row['name']); ids.add(row['id'])
    return {row['name']: row for row in rows}


def _download(row, path):
    _rows([row])
    _gh(_api('releases/assets/' + str(row['id'])), '-H', 'Accept: application/octet-stream', destination=path)
    if Path(path).stat().st_size != row['size'] or sha256_file(Path(path)) != row['sha256']:
        raise RuntimeError('downloaded release asset differs from its stable ID and digest')


def _sign_asset(path):
    bundle = path.with_name(path.name + '.sigstore.json')
    if bundle.exists():
        raise FileExistsError(bundle)
    subprocess.run([sys.executable, '-m', 'sigstore', 'sign', '--bundle', str(bundle), str(path)], check=True)
    return bundle


def _write_placeholder_sigstore_bundle(path):
    bundle = path.with_name(path.name + '.sigstore.json')
    with bundle.open('x') as stream:
        stream.write('{}\n')
    return bundle


def _verify_signature(path, bundle):
    if os.environ.get('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY', '').strip() not in ('', '0'):
        raise RuntimeError('hosted package verification cannot bypass Sigstore')
    _safe_file_without_symlinks(path, label='signed release asset')
    _safe_file_without_symlinks(bundle, label='release signature')
    if not _json_object(bundle, label='Sigstore bundle'):
        raise RuntimeError('hosted package contains a placeholder signature')
    verify_sigstore_asset(repo_root=REPO_ROOT, asset_path=path, bundle_path=bundle, repo=AUTHORITATIVE_RELEASE_REPO)


def _distribution(dist, revision, version, source):
    files = {p.name: sha256_file(_safe_file_without_symlinks(p, label='candidate asset')) for p in sorted(dist.iterdir())}
    provenance = verify_distribution_provenance(provenance_path=dist / 'build-provenance.v1.json', implementation_revision=revision)
    data = _json_object(Path(provenance['path']), label='candidate provenance')
    if (data.get('repo') != AUTHORITATIVE_RELEASE_REPO or data.get('actor') != AUTHORITATIVE_RELEASE_ACTOR
            or data.get('tag') != 'v' + version or data.get('release_version') != version
            or data.get('workflow', {}).get('path') != WORKFLOW_PATH or data['workflow'].get('ref') != WORKFLOW_REF):
        raise RuntimeError('candidate provenance is outside canonical authority')
    _package_bindings(dist, files, source, data['artifacts']['wheel']['name'], version)
    for name in sorted(files):
        if name.endswith('.sigstore.json'):
            _verify_signature(dist / name.removesuffix('.sigstore.json'), dist / name)
    return files, data


def _upload(release_id, path):
    # gh's release upload resolves by tag; this fixed-ID API upload cannot clobber.
    environment = dict(os.environ, GH_HOST='github.com', GH_REPO=AUTHORITATIVE_RELEASE_REPO)
    endpoint = f'https://uploads.github.com/repos/{AUTHORITATIVE_RELEASE_REPO}/releases/{_number(release_id)}/assets?name={path.name}'
    result = subprocess.run(['gh', 'api', '--hostname', 'github.com', '--method', 'POST', endpoint,
        '-H', 'Content-Type: application/octet-stream', '--input', str(path)], check=True, stdout=subprocess.PIPE, env=environment, timeout=180)
    row = _row(json.loads(result.stdout, object_pairs_hook=_unique_json_pairs))
    if row['name'] != path.name or row['size'] != path.stat().st_size or row['sha256'] != sha256_file(path):
        raise RuntimeError('uploaded asset readback differs from candidate bytes')
    return row


def reserve_candidate(*, tag, revision, output):
    _require_canonical_release_context(repo=AUTHORITATIVE_RELEASE_REPO)
    _identity(tag, revision)
    from greenfield_release_qualification import _require_build_source
    _require_build_source(REPO_ROOT, revision)
    if os.environ.get('GITHUB_SHA') != revision:
        raise RuntimeError('candidate workflow is not H')
    if output.exists() or output.is_symlink():
        raise FileExistsError('candidate reservation already exists')
    page = 1
    while True:
        releases = _gh(_api(f'releases?per_page=100&page={page}'))
        if not isinstance(releases, list):
            raise RuntimeError('candidate release census is not a list')
        if any(release.get('tag_name') == tag for release in releases):
            raise RuntimeError('existing candidate or release must be preserved without replay')
        if len(releases) < 100:
            break
        page += 1
    run_id, attempt = _number(int(os.environ['GITHUB_RUN_ID'])), _number(int(os.environ['GITHUB_RUN_ATTEMPT']))
    value = _gh(_api('releases'), '--method', 'POST', payload={'tag_name': tag, 'target_commitish': revision,
        'name': tag, 'body': f'Unqualified candidate {run_id}.{attempt}', 'draft': True, 'prerelease': False})
    reservation = {'tag': tag, 'implementation_revision': revision, 'release_id': _number(value['id']), 'build_run_id': run_id, 'build_run_attempt': attempt}
    _release(value['id'], tag, revision, draft=True)
    with output.open('x') as stream:
        json.dump(reservation, stream, sort_keys=True); stream.write('\n')
    return reservation


def _checkout_source(revision):
    from greenfield_release_qualification import _require_build_source, _source_git
    _require_build_source(REPO_ROOT, revision)
    names = _source_git(REPO_ROOT, 'ls-tree', '-rz', '--name-only', revision).decode().split('\0')
    return _source_git(REPO_ROOT, 'rev-parse', revision + '^{tree}').decode().strip(), {
        'path': str(REPO_ROOT), 'files': {name: sha256_file(REPO_ROOT / name) for name in names if name}}


def stage_candidate(*, reservation, dist):
    _require_canonical_release_context(repo=AUTHORITATIVE_RELEASE_REPO)
    revision, tag = reservation['implementation_revision'], reservation['tag']
    _, source = _checkout_source(revision)
    if (os.environ.get('GITHUB_SHA') != revision or str(reservation['build_run_id']) != os.environ.get('GITHUB_RUN_ID')
            or str(reservation['build_run_attempt']) != os.environ.get('GITHUB_RUN_ATTEMPT')):
        raise RuntimeError('candidate reservation belongs to another builder')
    _release(reservation['release_id'], tag, revision, draft=True)
    if _asset_rows(reservation['release_id']):
        raise RuntimeError('candidate has already uploaded assets; preserve without replay')
    _, provenance = _distribution(dist, revision, tag.removeprefix('v'), source)
    _builder_provenance(provenance, reservation['build_run_id'], reservation['build_run_attempt'])
    assets = [_upload(reservation['release_id'], path) for path in sorted(dist.iterdir())]
    if {name: _row(row) for name, row in _asset_rows(reservation['release_id']).items()} != _rows(assets):
        raise RuntimeError('staged complete D census differs from built bytes')
    return {'status': 'signed_draft_staged_not_qualified', **reservation, 'asset_count': len(assets)}


def _builder_provenance(provenance, run_id, attempt):
    if (str(provenance['workflow'].get('run_id')) != str(run_id)
            or str(provenance['workflow'].get('run_attempt')) != str(attempt)):
        raise RuntimeError('signed provenance belongs to another build run/attempt')


def _remote_candidate(*, run_id, revision, tag, dist, release_id=None, attempt=None, draft=True):
    _identity(tag, revision)
    if attempt is None:
        run = _gh(_api(f'actions/runs/{_number(run_id)}'))
        attempt = _number(run.get('run_attempt'))
    _run(run_id, attempt, revision)
    if release_id is None:
        release_id = _number(_gh(_api('releases/tags/' + tag))['id'])
    _release(release_id, tag, revision, draft=draft)
    remote = _asset_rows(release_id)
    rows = [_row(row) for _, row in sorted(remote.items())]
    _rows(rows)
    for row in rows:
        _download(row, dist / row['name'])
    tree, source = _checkout_source(revision)
    _, provenance = _distribution(dist, revision, tag.removeprefix('v'), source)
    _builder_provenance(provenance, run_id, attempt)
    return {'version': LOCAL_VERSION, 'repository': AUTHORITATIVE_RELEASE_REPO, 'tag': tag,
        'implementation_revision': revision, 'source_tree': tree, 'release_id': release_id,
        'build_run_id': run_id, 'build_run_attempt': attempt, 'distribution_assets': rows}


def _workflow_steps(payload, run_id, attempt):
    if (not isinstance(payload, dict) or payload.get('total_count') != 1 or len(payload.get('jobs', [])) != 1):
        raise RuntimeError('candidate requires its exact one hosted build job')
    job = payload['jobs'][0]
    if (job.get('run_id') != run_id or job.get('run_attempt') != attempt
            or job.get('status') != 'completed' or job.get('conclusion') != 'success'):
        raise RuntimeError('candidate hosted job belongs to another or failed build')
    for name in BUILD_STEPS.values():
        steps = [step for step in job.get('steps', []) if step.get('name') == name]
        if len(steps) != 1 or steps[0].get('status') != 'completed' or steps[0].get('conclusion') != 'success':
            raise RuntimeError('candidate lacks its actual successful hosted build step')


def _verify_workflow_evidence(evidence, record, logs):
    if not isinstance(evidence, dict) or set(evidence) != {'archive_sha256', 'steps_sha256'}:
        raise RuntimeError('candidate workflow evidence is not closed')
    archive = _safe_file_without_symlinks(logs / 'hosted-workflow.zip', label='hosted workflow log archive')
    steps = _safe_file_without_symlinks(logs / 'hosted-steps.json', label='hosted step evidence')
    if sha256_file(archive) != evidence['archive_sha256'] or sha256_file(steps) != evidence['steps_sha256']:
        raise RuntimeError('actual hosted workflow evidence changed')
    _workflow_steps(_json_object(steps, label='hosted build steps'), record['build_run_id'], record['build_run_attempt'])
    with zipfile.ZipFile(archive) as contents:
        names = contents.namelist()
        if (not names or len(names) != len(set(names)) or any(PurePosixPath(name).is_absolute()
                or '..' in PurePosixPath(name).parts or name.rstrip('/') != PurePosixPath(name).as_posix().rstrip('/') for name in names)):
            raise RuntimeError('hosted workflow log archive has unsafe or duplicate entries')
        if contents.testzip() is not None:
            raise RuntimeError('hosted workflow log archive is corrupt')


def _acquire_workflow_evidence(run_id, attempt, logs):
    payload = _gh(_api(f'actions/runs/{_number(run_id)}/attempts/{_number(attempt)}/jobs?per_page=100'))
    _workflow_steps(payload, run_id, attempt)
    path = logs / 'hosted-steps.json'
    with path.open('x') as stream:
        json.dump(payload, stream, sort_keys=True, indent=2); stream.write('\n')
    archive = logs / 'hosted-workflow.zip'
    _gh(_api(f'actions/runs/{run_id}/attempts/{attempt}/logs'), destination=archive)
    evidence = {'archive_sha256': sha256_file(archive), 'steps_sha256': sha256_file(path)}
    _verify_workflow_evidence(evidence, {'build_run_id': run_id, 'build_run_attempt': attempt}, logs)
    return evidence


def acquire_candidate(*, run_id, revision, tag, proof_root):
    if os.environ.get('ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY', '').strip() not in ('', '0'):
        raise RuntimeError('candidate acquisition cannot bypass Sigstore')
    _identity(tag, revision); _number(run_id)
    proof_root = _path_without_symlink_segments(proof_root, label='candidate proof root')
    if not proof_root.is_absolute() or not proof_root.is_dir() or proof_root != proof_root.resolve():
        raise RuntimeError('candidate acquisition requires its safe absolute proof root')
    dist, logs = proof_root / 'dist', proof_root / 'package-logs'
    if dist.exists() or logs.exists():
        raise FileExistsError('candidate acquisition destination already exists')
    dist.mkdir(); logs.mkdir()
    binding = _remote_candidate(run_id=run_id, revision=revision, tag=tag, dist=dist)
    binding['workflow_evidence'] = _acquire_workflow_evidence(run_id, binding['build_run_attempt'], logs)
    with (proof_root / 'hosted-acquisition.v1.json').open('x') as stream:
        json.dump(binding, stream, sort_keys=True, indent=2); stream.write('\n')
    return binding


def verify_local_candidate(*, proof_root, revision, version, source):
    binding = _json_object(proof_root / 'hosted-acquisition.v1.json', label='hosted acquisition')
    if (set(binding) != CANDIDATE_FIELDS or binding.get('version') != LOCAL_VERSION
            or binding.get('repository') != AUTHORITATIVE_RELEASE_REPO or binding.get('tag') != 'v' + version
            or binding.get('implementation_revision') != revision
            or not re.fullmatch('[0-9a-f]{40}', binding.get('source_tree', ''))):
        raise RuntimeError('prepared package lacks closed current hosted acquisition')
    _number(binding['release_id']); _number(binding['build_run_id']); _number(binding['build_run_attempt'])
    files, provenance = _distribution(proof_root / 'dist', revision, version, source)
    expected = _rows(binding['distribution_assets'])
    if set(files) != set(expected) or any(files[name] != row['sha256'] or (proof_root / 'dist' / name).stat().st_size != row['size'] for name, row in expected.items()):
        raise RuntimeError('prepared D differs from complete signed hosted candidate')
    _builder_provenance(provenance, binding['build_run_id'], binding['build_run_attempt'])
    _verify_workflow_evidence(binding['workflow_evidence'], binding, proof_root / 'package-logs')
    return binding


def promotion_binding(*, prepared, prepared_sha256, qualification):
    candidate = prepared['hosted_candidate']
    if qualification.get('status') != 'passed' or qualification.get('implementation_revision') != candidate['implementation_revision']:
        raise RuntimeError('promotion requires the existing exact local qualification')
    return {'version': PROMOTION_VERSION, **{key: candidate[key] for key in ('tag', 'implementation_revision', 'release_id', 'build_run_id', 'build_run_attempt', 'distribution_assets')},
        'prepared_package_sha256': _digest(prepared_sha256),
        'qualification_sha256': hashlib.sha256(json.dumps(qualification, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()}


def promote_candidate(binding):
    _require_canonical_release_context(repo=AUTHORITATIVE_RELEASE_REPO)
    if not isinstance(binding, dict) or set(binding) != PROMOTION_FIELDS or binding.get('version') != PROMOTION_VERSION:
        raise RuntimeError('promotion requires its closed authenticated maintainer statement')
    revision, tag = binding['implementation_revision'], binding['tag']
    _identity(tag, revision); _digest(binding['prepared_package_sha256']); _digest(binding['qualification_sha256'])
    if (os.environ.get('GITHUB_SHA') != revision or os.environ.get('RELEASE_EXPECTED_SHA') != revision
            or os.environ.get('RELEASE_TAG') != tag or os.environ.get('RELEASE_OPERATION') != 'promote'):
        raise RuntimeError('promotion workflow inputs are not the exact H/tag operation')
    with tempfile.TemporaryDirectory(prefix='odylith-promotion-') as temporary:
        directory = Path(temporary).resolve(); dist = directory / 'dist'; dist.mkdir()
        observed = _remote_candidate(run_id=binding['build_run_id'], attempt=binding['build_run_attempt'],
            revision=revision, tag=tag, release_id=binding['release_id'], dist=dist)
        if binding['distribution_assets'] != observed['distribution_assets']:
            raise RuntimeError('qualified promotion tuple differs from signed candidate')
        _workflow_steps(_gh(_api(f"actions/runs/{binding['build_run_id']}/attempts/{binding['build_run_attempt']}/jobs?per_page=100")), binding['build_run_id'], binding['build_run_attempt'])
        expected_rows = _rows(binding['distribution_assets'])
        if {name: _row(row) for name, row in _asset_rows(binding['release_id']).items()} != expected_rows:
            raise RuntimeError('candidate changed before publication')
        _release(binding['release_id'], tag, revision, draft=True)
        _gh(_api('releases/' + str(binding['release_id'])), '--method', 'PATCH', payload={'draft': False, 'body': 'Odylith release ' + tag})
        _release(binding['release_id'], tag, revision, draft=False)
        if {name: _row(row) for name, row in _asset_rows(binding['release_id']).items()} != expected_rows:
            raise RuntimeError('published complete candidate census changed')
        for row in expected_rows.values():
            _download(row, directory / ('published-' + row['name']))
    return {'version': PROMOTION_VERSION, 'status': 'published_exact_candidate', 'binding': binding,
        'authority': 'canonical maintainer local-qualification statement; remote exact byte verification'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('reserve', 'stage', 'acquire', 'promote'))
    parser.add_argument('--tag'); parser.add_argument('--revision'); parser.add_argument('--output', type=Path)
    parser.add_argument('--reservation', type=Path); parser.add_argument('--dist-dir', type=Path)
    parser.add_argument('--proof-root', type=Path)
    parser.add_argument('--build-run-id', type=int)
    args = parser.parse_args(argv)
    if args.operation == 'reserve':
        result = reserve_candidate(tag=args.tag, revision=args.revision, output=args.output)
    elif args.operation == 'stage':
        result = stage_candidate(reservation=_json_object(args.reservation, label='candidate reservation'), dist=args.dist_dir)
    elif args.operation == 'acquire':
        result = acquire_candidate(run_id=args.build_run_id, revision=args.revision, tag=args.tag, proof_root=args.proof_root)
    else:
        # Dispatch supplies JSON data, never executable shell fragments or file URLs.
        result = promote_candidate(json.loads(os.environ['ODYLITH_PROMOTION_BINDING'], object_pairs_hook=_unique_json_pairs))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
