"""Traceability must check the real active-plan inventory, including dated folders."""

from pathlib import Path

import pytest

from odylith.runtime.governance import validate_plan_traceability_contract as contract


_ACTIVE = Path('odylith/technical-plans/in-progress')
_VALID = (
    '# Planned delivery\n\n## Traceability\n\n'
    '### Runbooks\n- `docs/runbooks/recovery.md`\n\n'
    '### Developer Docs\n- [Interface](docs/interface.md)\n\n'
    '### Code References\n- [ ] `src/service.py`\n'
)


def _plan(root: Path, relative: str, text: str = _VALID) -> Path:
    for target in ('docs/runbooks/recovery.md', 'docs/interface.md', 'src/service.py'):
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('Source evidence\n')
    path = root / _ACTIVE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.mark.parametrize('relative', ['delivery.md', '2026-09/delivery.md', '2026-09/child/delivery.md'])
def test_valid_active_plan_is_actually_checked(tmp_path, capsys, relative):
    _plan(tmp_path, relative)
    assert contract.main(['--repo-root', str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert 'plan traceability contract passed' in output
    assert 'plans validated: 1' in output


@pytest.mark.parametrize('reference', ['.github/workflows/release.yml', '.config/check.py', './src/service.py'])
def test_code_reference_preserves_relative_path_identity(tmp_path, reference):
    _plan(tmp_path, '2026-09/current.md', _VALID.replace('src/service.py', reference))
    target = tmp_path / reference
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('Current source reference\n')
    assert contract.main(['--repo-root', str(tmp_path)]) == 0


@pytest.mark.parametrize(('text', 'failure'), [
    ('# Missing traceability\n', 'missing required section'),
    (_VALID.replace('src/service.py', 'src/absent.py'), 'path does not exist'),
    (_VALID.replace('docs/runbooks/recovery.md', 'docs/interface.md'), 'wrong bucket'),
    (_VALID.replace('- [ ] `src/service.py`', '- No source reference yet.'), 'at least one file path'),
])
def test_invalid_dated_plan_fails_without_writes(tmp_path, capsys, text, failure):
    _plan(tmp_path, '2026-09/invalid.md', text)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert contract.main(['--repo-root', str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert 'plan traceability contract FAILED' in output
    assert 'plans validated: 1' in output
    assert failure in output
    assert before == {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_mixed_inventory_reports_checked_files_even_when_one_fails(tmp_path, capsys):
    _plan(tmp_path, 'direct.md')
    _plan(tmp_path, '2026-09/invalid.md', '# Missing traceability\n')
    (tmp_path / _ACTIVE / 'directory.md').mkdir()
    archived = tmp_path / 'odylith/technical-plans/done/2026-09/old.md'
    archived.parent.mkdir(parents=True)
    archived.write_text('# Historical record outside active scope\n')
    assert contract.main(['--repo-root', str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert 'plans validated: 2' in output
    assert 'old.md' not in output
    assert 'directory.md' not in output


def test_empty_existing_scope_is_not_applicable_not_a_pass(tmp_path, capsys):
    root = tmp_path / _ACTIVE
    root.mkdir(parents=True)
    (root / '2026-09').mkdir()
    (root / 'not-a-file.md').mkdir()
    assert contract.main(['--repo-root', str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert 'not applicable' in output
    assert 'no active Markdown plan files' in output
    assert str(root) in output
    assert 'plans validated: 0' in output
    assert 'passed' not in output


def test_missing_required_directory_remains_failed(tmp_path, capsys):
    assert contract.main(['--repo-root', str(tmp_path)]) == 2
    output = capsys.readouterr().out
    assert 'missing directory' in output
    assert 'not applicable' not in output
    assert 'passed' not in output


def test_reporting_uses_the_exact_checked_inventory(tmp_path, capsys, monkeypatch):
    selected = _plan(tmp_path, '2026-09/current.md')
    original = contract.validate_plan_traceability_contract
    inventories = []

    def validate_selected(*, repo_root, plan_paths):
        inventories.append(tuple(plan_paths))
        _plan(repo_root, '2026-09/later.md')
        return original(repo_root=repo_root, plan_paths=plan_paths)

    monkeypatch.setattr(contract, 'validate_plan_traceability_contract', validate_selected)
    assert contract.main(['--repo-root', str(tmp_path)]) == 0
    assert inventories == [(selected,)]
    assert 'plans validated: 1' in capsys.readouterr().out
