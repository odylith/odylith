"""Real cancellation and pending-seal custody for the supported product journey."""
from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from odylith.runtime.domain_intelligence import greenfield_process as process
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as pending
from tests.unit.runtime.test_greenfield_create_transaction import _transaction

ROOT = Path(__file__).resolve().parents[3]


def _env():
    return {**os.environ, "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT/'src'), str(ROOT/'scripts/release')))}


def _run_script(tmp_path, source, *, timeout=5):
    script = tmp_path/'runner.py'
    script.write_text(source)
    return subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=_env(),
                          capture_output=True, text=True, timeout=timeout)


@pytest.mark.parametrize("phase", ["contract", "source-check", "retention", "diagnostic-retention", "observer"])
def test_native_block_is_cancelled_without_later_phase_or_success_preview(tmp_path, phase):
    script = '''import hashlib, json
from pathlib import Path
from odylith.runtime.domain_intelligence import greenfield_host_flow as host
from odylith.runtime.domain_intelligence import greenfield_process as process
from odylith.runtime.domain_intelligence import greenfield_whole_journey_budget as budget
from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
process.JOURNEY_CANCELLATION_GRACE_SECONDS = 0.2
host.PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS = 0.15
budget.PROVISIONAL_WHOLE_JOURNEY_TIMEOUT_SECONDS = 0.15
phase = PHASE
flow, host_run, installed, calls, proposals, repo = _flow(Path.cwd(), contract={"version":"contract"}, candidate={}, gate_decision="clarify" if phase=="observer" else "admit")
def recorded_host(*args, **kwargs):
    Path("hosts").open("a").write("host\\n")
    return host_run(*args, **kwargs)
host._invoke_host = recorded_host
original = flow.invoke_installed
def block(*args):
    Path("blocked").write_text(phase)
    hashlib.pbkdf2_hmac("sha256", b"secret", b"salt", 500_000_000)
def invoke(command, timeout):
    Path("commands").open("a").write(" ".join(command)+"\\n")
    if phase=="contract" or (phase=="source-check" and "source-ledger-check" in command):
        block()
    return original(command, timeout)
changes = {"invoke_installed":invoke}
if phase=="retention": changes["retain_authority_gate_bytes"] = block
if phase=="diagnostic-retention": changes["retain_diagnostic_bytes"] = block
if phase=="observer": changes["observe"] = block
flow = host.HostCandidateFlow(**{**flow.__dict__, **changes})
host.run_host_candidate_flow(flow)
Path("preview").write_text("success")
'''.replace('PHASE', repr(phase))
    started = time.monotonic()
    result = _run_script(tmp_path, script)
    assert result.returncode == -signal.SIGKILL, result.stderr
    assert time.monotonic()-started < 2
    assert (tmp_path/'blocked').read_text() == phase
    assert not (tmp_path/'preview').exists()
    if phase == "diagnostic-retention":
        assert not (tmp_path/'commands').exists()  # Input retention precedes the first command.
        assert not (tmp_path/'hosts').exists()
    else:
        assert 'propose' not in (tmp_path/'commands').read_text()


def test_guardian_stops_active_child_and_grandchild_before_stalled_runner(tmp_path):
    source = '''import hashlib, json, os, subprocess, sys, time
from pathlib import Path
from odylith.runtime.domain_intelligence import greenfield_process as p
p.JOURNEY_CANCELLATION_GRACE_SECONDS=0.2
child = "import subprocess,sys,time,json,os; c=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); print(json.dumps([os.getpid(),c.pid]),flush=True); time.sleep(30)"
with p.supervise_greenfield_journey(seconds=0.3):
    def stalled(pid, pgid):
        time.sleep(0.1)
        Path("leader").write_text(str(pid))
        hashlib.pbkdf2_hmac("sha256",b"s",b"s",500_000_000)
    p.run_command_with_group_timeout(cwd=Path.cwd(),env=os.environ,command=[sys.executable,"-c",child],timeout=30,on_started=stalled)
'''
    result = _run_script(tmp_path, source)
    assert result.returncode == -signal.SIGKILL
    leader = int((tmp_path/'leader').read_text())
    # Process topology may contain a briefly adopted zombie; no live group may
    # continue executing after the finite cancellation grace.
    state = subprocess.run(['ps', '-axo', 'pid=,pgid=,stat='], capture_output=True, text=True, check=True)
    assert not [row for row in state.stdout.splitlines() if int(row.split()[1]) == leader and not row.split()[2].startswith('Z')]


def _compile_transaction_fixture(tmp_path):
    from odylith.runtime.domain_intelligence.greenfield_create_transaction import write_compiled_product_create_transaction_file
    return write_compiled_product_create_transaction_file(
        tmp_path / "fixture-transaction.json", _transaction(repo_root=tmp_path),
    )


def _stage_under_parent(tmp_path, *, transaction_hash=None, completion_receipt=None):
    source = '''from pathlib import Path
from odylith.runtime.domain_intelligence.greenfield_create_transaction import load_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store as store
root=Path.cwd()
transaction_path=root/"fixture-transaction.json"
tx=load_compiled_product_create_transaction_file(transaction_path)
path=store.stage_pending_transaction(repo_root=root,transaction=tx,completion_receipt=RECEIPT)
(root/"hash").write_text(tx.transaction_hash)
print(path)
'''
    source = source.replace('RECEIPT', repr(str(completion_receipt) if completion_receipt else None))
    if transaction_hash is not None:
        source = source.replace('transaction_path=root/"fixture-transaction.json"',
            'transaction_path=store.resolve_pending_transaction(repo_root=root, transaction_hash='
            + repr(transaction_hash)+',completion_receipt='+repr(str(completion_receipt) if completion_receipt else None)+')')
    script = tmp_path/'stage.py';script.write_text(source)
    return process.run_command_with_group_timeout(cwd=tmp_path, env=_env(),
        command=[sys.executable,str(script)],timeout=5)


def test_new_pending_seal_is_hidden_until_guarded_completion(tmp_path):
    _compile_transaction_fixture(tmp_path)
    receipt = {}
    with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
        result = _stage_under_parent(tmp_path)
        assert result.returncode == 0, result.stderr
        digest = (tmp_path/'hash').read_text()
        path = pending.pending_transaction_path(tmp_path,digest)
        assert (path.parent/'.bounded-journey.v1.json').is_file()
        with pytest.raises(ValueError,match='has not released'):
            pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest)
    delivery = pending.write_completion_receipt_delivery(repo_root=tmp_path,receipt=receipt)
    assert pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest,completion_receipt=delivery) == path


def test_cancelled_journey_cannot_leave_a_confirmable_new_seal(tmp_path):
    _compile_transaction_fixture(tmp_path)
    source = '''import hashlib
from pathlib import Path
from odylith.runtime.domain_intelligence import greenfield_process as process
from tests.unit.install.test_greenfield_bounded_product_transport import _stage_under_parent
process.JOURNEY_CANCELLATION_GRACE_SECONDS=0.2
with process.supervise_greenfield_journey(seconds=2.0):
    result=_stage_under_parent(Path.cwd())
    assert result.returncode==0,result.stderr
    Path("blocked").write_text("native cancellation after pending stage")
    hashlib.pbkdf2_hmac("sha256",b"s",b"s",500_000_000)
Path("preview").write_text("success")
'''
    result = _run_script(tmp_path, source)
    assert result.returncode == -signal.SIGKILL, result.stderr
    assert (tmp_path/'blocked').read_text() == 'native cancellation after pending stage'
    assert not (tmp_path/'preview').exists()
    digest = (tmp_path/'hash').read_text()
    path = pending.pending_transaction_path(tmp_path,digest)
    assert (path.parent/'.bounded-journey.v1.json').is_file()
    assert not (path.parent/'.bounded-completion.v1.json').exists()
    assert not (tmp_path/pending.GREENFIELD_RUNTIME_ROOT/'completion-receipts').exists()
    with pytest.raises(ValueError,match='has not released'):
        pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest)


def test_preexisting_seal_is_preserved_on_parent_failure(tmp_path):
    tx = _transaction(repo_root=tmp_path)
    path = pending.stage_pending_transaction(repo_root=tmp_path,transaction=tx)
    before = {p.name:p.read_bytes() for p in path.parent.iterdir()}
    with pytest.raises(RuntimeError,match='cancel'):
        with process.supervise_greenfield_journey(seconds=5):
            result = _stage_under_parent(tmp_path,transaction_hash=tx.transaction_hash)
            assert result.returncode == 0, result.stderr
            raise RuntimeError('cancel')
    assert {p.name:p.read_bytes() for p in path.parent.iterdir()} == before
    assert pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=tx.transaction_hash) == path


def test_caller_alarm_state_is_preserved_on_success_and_failure():
    original_handler = signal.getsignal(signal.SIGALRM)
    original_timer = signal.getitimer(signal.ITIMER_REAL)
    handler = lambda *_args: None
    try:
        signal.signal(signal.SIGALRM,handler)
        signal.setitimer(signal.ITIMER_REAL,10)
        for fail in (False,True):
            try:
                with process.supervise_greenfield_journey(seconds=5):
                    if fail: raise RuntimeError('failure')
            except RuntimeError:
                pass
            assert signal.getsignal(signal.SIGALRM) is handler
            assert 0 < signal.getitimer(signal.ITIMER_REAL)[0] <= 10
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,original_handler)
        signal.setitimer(signal.ITIMER_REAL,*original_timer)


def test_detached_manual_marker_or_dead_parent_does_not_stage(tmp_path, monkeypatch):
    read_fd,write_fd=os.pipe()
    os.close(read_fd)
    monkeypatch.setenv('ODYLITH_GREENFIELD_JOURNEY_CHANNEL_FD',str(write_fd))
    try:
        with pytest.raises(OSError):
            process.register_bounded_pending_transaction(tmp_path/'seal')
    finally:
        os.close(write_fd)


def test_commit_only_entry_cannot_bypass_quarantined_pending_resolver(tmp_path):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    with process.supervise_greenfield_journey(seconds=5):
        result = _stage_under_parent(tmp_path)
        assert result.returncode == 0, result.stderr
        digest = (tmp_path/'hash').read_text()
        original = pending.pending_transaction_path(tmp_path,digest)
        outside = tmp_path/'copied.json'
        outside.write_bytes(original.read_bytes())
        outside.with_name(outside.name+'.compiler-receipt.v1.json').write_bytes(
            original.with_name(original.name+'.compiler-receipt.v1.json').read_bytes())
        for path in (original,outside):
            with pytest.raises(ValueError, match='has not released'):
                commit_greenfield_create_transaction(repo_root=tmp_path,
                    transaction_file=path,transaction_hash=digest,confirm=True)


def test_kernel_birth_identity_rejects_a_reused_or_unrelated_pid(monkeypatch):
    called=[]
    monkeypatch.setattr(process,'_process_birth',lambda pid:'new-owner')
    monkeypatch.setattr(process,'_descendant_groups',lambda pid:called.append(pid) or {pid})
    assert process._owned_journey_groups({12345:'previous-owner'}) == set()
    assert called == []


def test_supported_prepare_cli_stops_at_one_real_authority_question(tmp_path):
    import shutil
    executable = tmp_path/'bin/codex';executable.parent.mkdir()
    executable.write_text(f'#!{sys.executable}\nimport sys,json\nfrom pathlib import Path\nsys.stdin.read()\nPath({str(tmp_path/"host-calls")!r}).open("a").write("gate\\n")\nprint(json.dumps({{"decision":"clarify","required_fields":["first_path"],"owner_quote":"","task_quote":"","result_quote":"","question":"Who performs the first task, and what result should they see?"}}))\n')
    executable.chmod(0o755)
    consumer=tmp_path/'consumer';consumer.mkdir()
    env={**_env(),'PATH':str(executable.parent)+os.pathsep+os.environ['PATH']}
    env.pop('ODYLITH_REASONING_CODEX_BIN',None)
    result=subprocess.run([sys.executable,'-m','odylith.cli','greenfield','prepare',
        '--repo-root',str(consumer),'--prompt','Build a project to help teams coordinate.','--format','json'],
        cwd=consumer,env=env,capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr+'\n'+result.stdout
    payload=json.loads(result.stdout)
    assert payload['mode']=='clarification_required'
    assert payload['clarification']['question'].startswith('Who performs')
    stage=payload['bounded_journey']
    assert stage['host_invocations']==1
    assert stage['candidate_host_invocations']==stage['proposal_command_invocations']==0
    assert stage['whole_journey_route']=='odylith-greenfield-prepare.v1'
    assert stage['whole_journey_bound_status']=='diagnostic_unqualified'
    assert (tmp_path/'host-calls').read_text()=='gate\n'
    assert not (consumer/'.odylith/runtime/greenfield/pending').exists()


def test_preexisting_equal_hash_quarantine_cannot_be_adopted_or_released(tmp_path):
    tx = _transaction(repo_root=tmp_path)
    path = pending.stage_pending_transaction(repo_root=tmp_path,transaction=tx)
    marker = path.parent/'.bounded-journey.v1.json'
    marker.write_text('{"journey_id":"another-owner"}')
    before = {p.name:p.read_bytes() for p in path.parent.iterdir()}
    with pytest.raises(ValueError,match='has not released'):
        with process.supervise_greenfield_journey(seconds=5):
            pending.stage_pending_transaction(repo_root=tmp_path,transaction=tx)
    assert {p.name:p.read_bytes() for p in path.parent.iterdir()} == before


def test_native_stall_at_authoritative_settlement_keeps_new_seal_quarantined(tmp_path):
    _compile_transaction_fixture(tmp_path)
    source = '''import hashlib
from pathlib import Path
from odylith.runtime.domain_intelligence import greenfield_process as process
from tests.unit.install.test_greenfield_bounded_product_transport import _stage_under_parent
process.JOURNEY_CANCELLATION_GRACE_SECONDS=0.2
def settled():
    Path("settled").write_text("blocked before release")
    hashlib.pbkdf2_hmac("sha256",b"s",b"s",500_000_000)
with process.supervise_greenfield_journey(seconds=2.0,on_settled=settled):
    result=_stage_under_parent(Path.cwd())
    assert result.returncode==0,result.stderr
Path("preview").write_text("success")
'''
    result = _run_script(tmp_path,source)
    assert result.returncode == -signal.SIGKILL,result.stderr
    assert (tmp_path/'settled').read_text() == 'blocked before release'
    assert not (tmp_path/'preview').exists()
    digest=(tmp_path/'hash').read_text()
    path = pending.pending_transaction_path(tmp_path,digest)
    assert (path.parent/'.bounded-journey.v1.json').is_file()
    assert not (path.parent/'.bounded-completion.v1.json').exists()
    assert not (tmp_path/pending.GREENFIELD_RUNTIME_ROOT/'completion-receipts').exists()
    with pytest.raises(ValueError,match='has not released'):
        pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest)


@pytest.mark.parametrize('boundary', (315.0,660.0))
def test_final_budget_rejection_precedes_release_of_actual_pending_seal(tmp_path,monkeypatch,boundary):
    from odylith.runtime.domain_intelligence import greenfield_host_flow as host
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow,_completed
    flow,host_run,*_rest=_flow(tmp_path,contract={'version':'contract'},candidate={'result':{'status':'authored'}})
    _compile_transaction_fixture(flow.repo_root)
    clock=[0.0]
    monkeypatch.setattr(host.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(host,'_invoke_host',host_run)
    real_supervise=process.supervise_greenfield_journey
    @contextlib.contextmanager
    def late_settlement(**kwargs):
        callback=kwargs['on_settled']
        def late():
            clock[0]=boundary
            callback()
        with real_supervise(**{**kwargs,'on_settled':late}) as custody:
            yield custody
    monkeypatch.setattr(host,'supervise_greenfield_journey',late_settlement)
    def propose(candidate,gate,ledger,timeout):
        result=_stage_under_parent(flow.repo_root)
        assert result.returncode==0,result.stderr
        digest=(flow.repo_root/'hash').read_text()
        assert (pending.pending_transaction_directory(flow.repo_root,digest)/'.bounded-journey.v1.json').exists()
        return _completed([],stdout=json.dumps({'mode':'product_create_transaction'}))
    flow=host.HostCandidateFlow(**{**flow.__dict__,'invoke_propose':propose})
    with pytest.raises(host.HostCandidateFlowError,match='settlement'):
        host.run_host_candidate_flow(flow)
    digest=(flow.repo_root/'hash').read_text()
    with pytest.raises(ValueError):
        pending.resolve_pending_transaction(repo_root=flow.repo_root,transaction_hash=digest)


def test_copied_transaction_stays_denied_after_aborted_bytes_are_removed(tmp_path):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    with pytest.raises(RuntimeError, match='abort'):
        with process.supervise_greenfield_journey(seconds=5):
            result = _stage_under_parent(tmp_path)
            assert result.returncode == 0, result.stderr
            digest = (tmp_path/'hash').read_text()
            path = pending.pending_transaction_path(tmp_path,digest)
            copy = tmp_path/'copied.json'
            copy.write_bytes(path.read_bytes())
            copy.with_name(copy.name+'.compiler-receipt.v1.json').write_bytes(
                path.with_name(path.name+'.compiler-receipt.v1.json').read_bytes())
            raise RuntimeError('abort')
    assert not path.exists()
    assert (path.parent/'.bounded-journey.v1.json').exists()
    with pytest.raises(ValueError, match='has not released'):
        commit_greenfield_create_transaction(repo_root=tmp_path,transaction_file=copy,
                                            transaction_hash=digest,confirm=True)


def test_ordinary_same_group_grandchild_is_stopped_after_leader_exit(tmp_path):
    source = 'import subprocess,sys;p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);print(p.pid,flush=True)'
    with process.supervise_greenfield_journey(seconds=5):
        result = process.run_command_with_group_timeout(cwd=tmp_path,env=_env(),
            command=[sys.executable,'-c',source],timeout=2)
        assert result.returncode == 0,result.stderr
        child = int(result.stdout)
    state = subprocess.run(['ps','-p',str(child),'-o','stat='],capture_output=True,text=True).stdout.strip()
    assert not state or state.startswith('Z')


class _GuardianChannel:
    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []
    def recv(self, _size):
        return json.dumps(self.messages.pop(0)).encode()
    def send(self, payload):
        self.sent.append(json.loads(payload))
        return len(payload)


@pytest.mark.parametrize('failure', ('late_io','second_marker'))
def test_publication_late_or_partial_error_preserves_all_canonical_denials(tmp_path,monkeypatch,failure):
    paths = []
    for name in ('first','second'):
        root = tmp_path/name
        root.mkdir()
        tx = _transaction(repo_root=root)
        path = pending.stage_pending_transaction(repo_root=root,transaction=tx)
        (path.parent/'.bounded-journey.v1.json').write_text('{"journey_id":"owned"}')
        paths.append((root,tx.transaction_hash,path))
    clock = [0.0]
    channel = _GuardianChannel([*({'kind':'pending','path':str(p.parent)} for _,_,p in paths),
                                {'kind':'settle'},{'kind':'release'}])
    def select(read,_write,_error,_timeout):
        if channel.messages and channel.messages[0]['kind']=='release' and clock[0]<0.05:
            clock[0]=0.05
            return [],[],[]
        return read,[],[]
    real_finish = process._finish_journey_pending
    def finish(path,**kwargs):
        if kwargs['release'] and failure=='second_marker' and path==paths[1][2].parent:
            return False
        result = real_finish(path,**kwargs)
        if kwargs['release'] and failure=='late_io':
            clock[0]=1.2
        return result
    monkeypatch.setattr(process,'_REAL_MONOTONIC',lambda:clock[0])
    monkeypatch.setattr(process.select,'select',select)
    monkeypatch.setattr(process,'_owned_journey_groups',lambda _roots:set())
    monkeypatch.setattr(process,'_finish_journey_pending',finish)
    process._journey_guardian(channel,parent=os.getpid(),expires=1.0,journey_id='owned',grace=.2)
    assert channel.sent[-1]['completed'] is False
    for root,digest,path in paths:
        assert not path.exists()
        with pytest.raises(ValueError,match='has not released'):
            pending.resolve_pending_transaction(repo_root=root,transaction_hash=digest)


def test_post_certification_callback_error_preserves_delivered_authority(tmp_path):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    receipt = {}
    def failed_delivery(_finished):
        raise OSError("controlled post-certification delivery failure")
    with pytest.raises(process.JourneyDeliveryError,match="delivery is unknown"):
        with process.supervise_greenfield_journey(seconds=5,on_published=failed_delivery,
                                                  completion_receipt_sink=receipt):
            result = _stage_under_parent(tmp_path)
            assert result.returncode == 0,result.stderr
            digest = (tmp_path/'hash').read_text()
    delivery = pending.write_completion_receipt_delivery(repo_root=tmp_path,receipt=receipt)
    path = pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest,completion_receipt=delivery)
    assert commit_greenfield_create_transaction(repo_root=tmp_path,transaction_file=path,
        transaction_hash=digest,confirm=True,completion_receipt=delivery)['mode'] == 'applied'


def test_failed_marker_reset_cannot_admit_copied_bytes(tmp_path,monkeypatch):
    tx = _transaction(repo_root=tmp_path)
    path = pending.stage_pending_transaction(repo_root=tmp_path,transaction=tx)
    marker = path.parent/'.bounded-journey.v1.json'
    marker.write_text(json.dumps({'journey_id':'owned','released':True,
                                  'guardian_pid':99999999,'guardian_birth':'completed'}))
    original = Path.write_text
    def fail_reset(self,*args,**kwargs):
        if self == marker:
            raise OSError('controlled marker reset failure')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail_reset)
    assert process._finish_journey_pending(path.parent,journey_id='owned',release=False) is False
    assert not path.exists()
    with pytest.raises(ValueError,match='has not released'):
        pending.require_pending_transaction_released(tmp_path/'copy.json',repo_root=tmp_path,
                                                     transaction_hash=tx.transaction_hash)


def test_publication_sample_is_included_in_both_elapsed_intervals():
    from odylith.runtime.domain_intelligence.greenfield_whole_journey_budget import JourneyObservationFinalizer
    observation = {'whole_journey_seconds':1.0,'proposal_phase_elapsed_seconds':.5,
                   'operational_timeout_seconds':315.0}
    finalizer = JourneyObservationFinalizer(observation,0,lambda:2,lambda:10)
    assert finalizer.settled() == 313.5
    finalizer.published(12)
    assert observation['whole_journey_seconds'] == 4.0
    assert observation['proposal_phase_elapsed_seconds'] == observation['elapsed_seconds'] == 3.5


def test_multiple_new_seals_stop_before_any_successful_completion_record(tmp_path):
    roots = [tmp_path/name for name in ('first','second')]
    for root in roots:
        root.mkdir()
        _compile_transaction_fixture(root)
    paths = []
    receipt = {}
    with pytest.raises(process.JourneyCancelled,match='settlement'):
        with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
            for root in roots:
                result = _stage_under_parent(root)
                assert result.returncode == 0,result.stderr
                paths.append((root,(root/'hash').read_text()))
            (tmp_path/'settlement-ready').write_text('two staged seals')
    assert len(paths) == 2 and receipt == {}
    assert (tmp_path/'settlement-ready').read_text() == 'two staged seals'
    for root,digest in paths:
        path = pending.pending_transaction_path(root,digest)
        assert (path.parent/'.bounded-journey.v1.json').is_file()
        assert not (path.parent/'.bounded-completion.v1.json').exists()
        assert not (root/pending.GREENFIELD_RUNTIME_ROOT/'completion-receipts').exists()
        with pytest.raises(ValueError,match='has not released'):
            pending.resolve_pending_transaction(repo_root=root,transaction_hash=digest)


def test_parent_timeout_of_blocked_guardian_publication_keeps_tentative_state_denied(tmp_path,monkeypatch):
    _compile_transaction_fixture(tmp_path)
    original = subprocess.Popen
    code = '''import hashlib,socket,sys
from pathlib import Path
from odylith.runtime.domain_intelligence import greenfield_process as p
original=p._finish_journey_pending
def finish(path,**kwargs):
    result=original(path,**kwargs)
    if kwargs["release"]:
        (path/"publication-blocked").write_text("native guardian publication")
        hashlib.pbkdf2_hmac("sha256",b"s",b"s",500_000_000)
    return result
p._finish_journey_pending=finish
p._journey_guardian(socket.socket(fileno=int(sys.argv[2])),parent=int(sys.argv[3]),expires=float(sys.argv[4]),journey_id=sys.argv[5],grace=float(sys.argv[6]),registration=socket.socket(fileno=int(sys.argv[7])))
'''
    def launch(command,*args,**kwargs):
        if '--guardian' in command:
            command = [command[0],'-c',code,*command[3:]]
        return original(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'Popen',launch)
    receipt = {}
    with pytest.raises(process.JourneyDeliveryError,match="delivery is unknown"):
        with process.supervise_greenfield_journey(seconds=2,completion_receipt_sink=receipt):
            result = _stage_under_parent(tmp_path)
            assert result.returncode == 0,result.stderr
            digest = (tmp_path/'hash').read_text()
    path = pending.pending_transaction_path(tmp_path,digest)
    assert (path.parent/'publication-blocked').read_text() == 'native guardian publication'
    assert receipt == {}
    assert not (path.parent/'.bounded-completion.v1.json').exists()
    assert not (tmp_path/pending.GREENFIELD_RUNTIME_ROOT/'completion-receipts').exists()
    with pytest.raises(ValueError,match='has not released'):
        pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest)


@pytest.mark.parametrize('output_format', ['json', 'text'])
@pytest.mark.parametrize('verdict', ['no', 'uncertain', 'missing'])
def test_prepare_refusal_exposes_stage_reason_without_confirmation(
    tmp_path, monkeypatch, capsys, output_format, verdict,
):
    from odylith.runtime.domain_intelligence import greenfield_prepare_cli as prepare
    detail = '{"mode":"error","error":"controlled source inventory refusal"}'
    observation = {'stage':'source-ledger-check','source_completeness_verdict':verdict,
                   'source_completeness_omission_count':1 if verdict != 'missing' else -1,
                   'detail':detail,'candidate_host_invocations':0,'proposal_command_invocations':0}

    def refuse(_args):
        raise prepare.HostCandidateFlowError('installed source ledger decision check returned nonzero',
                                             observation=observation)

    monkeypatch.setattr(prepare,'prepare_request',refuse)
    result = prepare.main(['--repo-root',str(tmp_path),'--prompt','A controlled project request',
                           '--format',output_format])
    text = capsys.readouterr().out
    assert result == 2 and list(tmp_path.iterdir()) == []
    assert 'source inventory verification' in text
    if output_format == 'json':
        payload = json.loads(text)
        assert payload['mode'] == 'error' and payload['bounded_journey'] == observation
        assert not {'confirmation','completion_receipt','product_create_transaction'} & payload.keys()
    else:
        assert detail not in text and 'Checker detail' not in text
        assert '"mode"' not in text and '"error"' not in text
    assert ('reported an incomplete source inventory' in text if verdict == 'no' else
            'could not confirm source inventory completeness' in text if verdict == 'uncertain' else
            'did not report source completeness' in text)


def test_completed_bounded_seal_remains_confirmable_after_custodian_retirement(tmp_path):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    receipt = {}
    with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
        result = _stage_under_parent(tmp_path)
        assert result.returncode == 0,result.stderr
        digest = (tmp_path/'hash').read_text()
    delivery = pending.write_completion_receipt_delivery(repo_root=tmp_path,receipt=receipt)
    path = pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest,completion_receipt=delivery)
    result = commit_greenfield_create_transaction(repo_root=tmp_path,transaction_file=path,
                                                 transaction_hash=digest,confirm=True,completion_receipt=delivery)
    assert result['mode'] == 'applied'


@pytest.mark.parametrize('failure', ('record_error','record_late'))
def test_completion_record_failure_denies_even_when_both_pending_rollbacks_fail(tmp_path,monkeypatch,failure):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    original = subprocess.Popen
    code = '''import json,socket,sys
from pathlib import Path
from odylith.runtime.domain_intelligence import greenfield_process as p
unlink=Path.unlink
write=Path.write_text
def failed_unlink(self,*args,**kwargs):
    if self.name.startswith("product-create-transaction.v1.json") or self.name==".bounded-completion.v1.json":
        raise OSError("controlled sealed-byte and completion-record rollback failure")
    return unlink(self,*args,**kwargs)
def failed_reset(self,*args,**kwargs):
    if self.name==".bounded-journey.v1.json":
        raise OSError("controlled deny-marker reset failure")
    return write(self,*args,**kwargs)
Path.unlink=failed_unlink
Path.write_text=failed_reset
complete=p._write_journey_completion
def finish(path,**kwargs):
    complete(path,**kwargs)
    if FAILURE=="record_error":
        raise OSError("controlled completion write failure after visible bytes")
    p._REAL_MONOTONIC=lambda:kwargs["deadline"]+1
p._write_journey_completion=finish
p._journey_guardian(socket.socket(fileno=int(sys.argv[2])),parent=int(sys.argv[3]),expires=float(sys.argv[4]),journey_id=sys.argv[5],grace=float(sys.argv[6]),registration=socket.socket(fileno=int(sys.argv[7])))
'''.replace('FAILURE',repr(failure))
    def launch(command,*args,**kwargs):
        if '--guardian' in command:
            command = [command[0],'-c',code,*command[3:]]
        return original(command,*args,**kwargs)
    monkeypatch.setattr(subprocess,'Popen',launch)
    receipt = {}
    with pytest.raises(process.JourneyCancelled,match='not released'):
        with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
            result = _stage_under_parent(tmp_path)
            assert result.returncode == 0,result.stderr
            digest = (tmp_path/'hash').read_text()
            path = pending.pending_transaction_path(tmp_path,digest)
            copy = tmp_path/'copy.json'
            copy.write_bytes(path.read_bytes())
            copy.with_name(copy.name+'.compiler-receipt.v1.json').write_bytes(
                path.with_name(path.name+'.compiler-receipt.v1.json').read_bytes())
    assert path.exists()
    assert receipt == {}
    assert 'nonce' not in json.loads((path.parent/'.bounded-journey.v1.json').read_text())
    assert json.loads((path.parent/'.bounded-completion.v1.json').read_text())['status'] == 'completion_attempt'
    with pytest.raises(ValueError,match='has not released'):
        commit_greenfield_create_transaction(repo_root=tmp_path,transaction_file=copy,
                                            transaction_hash=digest,confirm=True)


@pytest.mark.parametrize('change', ('missing','nonce','journey_id','transaction_hash','extra'))
def test_explicit_completion_receipt_is_required_and_bound_at_actual_create(tmp_path,change):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    receipt = {}
    with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
        result = _stage_under_parent(tmp_path)
        assert result.returncode == 0,result.stderr
        digest = (tmp_path/'hash').read_text()
    path = pending.pending_transaction_path(tmp_path,digest)
    if change == 'missing':
        delivery = None
    else:
        altered = dict(receipt)
        altered[change] = '0'*64
        delivery = tmp_path/'altered-receipt.json'
        delivery.write_text(json.dumps(altered))
    with pytest.raises(ValueError,match='has not released'):
        commit_greenfield_create_transaction(repo_root=tmp_path,transaction_file=path,
            transaction_hash=digest,confirm=True,completion_receipt=delivery)
    assert not (tmp_path/'odylith/radar/source').exists()


def test_original_bounded_receipt_is_preserved_for_equal_hash_and_edit_lookup(tmp_path):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.domain_intelligence.greenfield_cli import terminal_decision_offer
    receipt = {}
    with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
        assert _stage_under_parent(tmp_path).returncode == 0
    digest = (tmp_path/'hash').read_text()
    delivery = pending.write_completion_receipt_delivery(repo_root=tmp_path,receipt=receipt)
    path = pending.pending_transaction_path(tmp_path,digest)
    before = {p.name:p.read_bytes() for p in path.parent.iterdir()}
    second_receipt = {}
    with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=second_receipt):
        result = _stage_under_parent(tmp_path,transaction_hash=digest,completion_receipt=delivery)
        assert result.returncode == 0,result.stderr
    assert second_receipt == {}
    assert {p.name:p.read_bytes() for p in path.parent.iterdir()} == before
    assert pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest,
                                               completion_receipt=delivery) == path
    offer = terminal_decision_offer(repo_root=tmp_path,transaction_hash=digest,completion_receipt=delivery)
    assert all('--completion-receipt' in c['command'] for c in offer['choices'])
    assert 'greenfield prepare' in offer['choices'][1]['command']
    from odylith.runtime.domain_intelligence.greenfield_prepare_cli import _request
    from argparse import Namespace
    prompt, correction = _request(Namespace(transaction_hash=digest,release='',edit='clarify authority',
        edit_evidence=None,completion_receipt=str(delivery)),tmp_path)
    assert prompt and correction == 'clarify authority'
    contract = subprocess.run([sys.executable,'-m','odylith.cli','greenfield','candidate-contract',
        '--repo-root',str(tmp_path),'--transaction-hash',digest,'--completion-receipt',str(delivery),
        '--edit',correction],cwd=tmp_path,env=_env(),capture_output=True,text=True,timeout=5)
    assert contract.returncode == 0,contract.stderr+contract.stdout
    assert receipt['nonce'] not in contract.stdout


def test_reject_can_retire_failed_bounded_state_without_reopening_copied_create(tmp_path):
    _compile_transaction_fixture(tmp_path)
    from odylith.runtime.surfaces.greenfield_host_confirmation import handle_greenfield_decision
    from odylith.runtime.domain_intelligence.greenfield_create_commit import commit_greenfield_create_transaction
    with pytest.raises(RuntimeError,match='cancel'):
        with process.supervise_greenfield_journey(seconds=5):
            assert _stage_under_parent(tmp_path).returncode == 0
            digest = (tmp_path/'hash').read_text()
            path = pending.pending_transaction_path(tmp_path,digest)
            copy = tmp_path/'copy.json'
            copy.write_bytes(path.read_bytes())
            copy.with_name(copy.name+'.compiler-receipt.v1.json').write_bytes(
                path.with_name(path.name+'.compiler-receipt.v1.json').read_bytes())
            raise RuntimeError('cancel')
    assert handle_greenfield_decision(repo_root=tmp_path,command='REJECT',transaction_hash=digest)['status'] == 'ABORTED'
    with pytest.raises(ValueError,match='has not released'):
        commit_greenfield_create_transaction(repo_root=tmp_path,transaction_file=copy,transaction_hash=digest,confirm=True)


@pytest.mark.parametrize('command', ('CONFIRM','create'))
def test_real_source_cli_confirmation_requires_delivered_receipt(tmp_path,command):
    _compile_transaction_fixture(tmp_path)
    receipt = {}
    with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=receipt):
        assert _stage_under_parent(tmp_path).returncode == 0
    digest = (tmp_path/'hash').read_text()
    delivery = pending.write_completion_receipt_delivery(repo_root=tmp_path,receipt=receipt)
    assert delivery.stat().st_mode & 0o777 == 0o600
    path = pending.pending_transaction_path(tmp_path,digest)
    arguments = (['decide','CONFIRM',digest] if command == 'CONFIRM' else
                 ['create','--transaction-file',str(path),'--transaction-hash',digest,'--confirm'])
    base = [sys.executable,'-m','odylith.cli','greenfield',*arguments,'--repo-root',str(tmp_path),'--json']
    refused = subprocess.run(base,cwd=tmp_path,env=_env(),capture_output=True,text=True,timeout=5)
    assert refused.returncode == 2,refused.stdout
    accepted = subprocess.run([*base,'--completion-receipt',str(delivery)],cwd=tmp_path,env=_env(),
                              capture_output=True,text=True,timeout=10)
    assert accepted.returncode == 0,accepted.stdout+accepted.stderr
    payload = json.loads(accepted.stdout)
    assert (payload['status'] == 'CLOSED' if command == 'CONFIRM' else payload['mode'] == 'applied')


def test_prepare_delivery_file_error_reports_accepted_environment_outcome(tmp_path,monkeypatch):
    _compile_transaction_fixture(tmp_path)
    from argparse import Namespace
    from odylith.runtime.domain_intelligence import greenfield_prepare_cli as prepare
    monkeypatch.setattr(prepare,'resolve_trusted_codex_executable',lambda **_kwargs:sys.executable)
    def completed(flow):
        with process.supervise_greenfield_journey(seconds=5,completion_receipt_sink=flow.completion_receipt_sink):
            assert _stage_under_parent(tmp_path).returncode == 0
        digest = (tmp_path/'hash').read_text()
        return subprocess.CompletedProcess([],0,json.dumps({'mode':'product_create_transaction',
            'product_create_transaction':{'transaction_hash':digest}}),'')
    monkeypatch.setattr(prepare,'run_host_candidate_flow',completed)
    def failed_delivery(**_kwargs):
        raise OSError('controlled delivered receipt persistence failure')
    monkeypatch.setattr(pending,'write_completion_receipt_delivery',failed_delivery)
    with pytest.raises(RuntimeError,match='completion was accepted; receipt delivery failed'):
        prepare.prepare_request(Namespace(repo_root=str(tmp_path),prompt='a project',edit=None,
            edit_evidence=None,transaction_hash=None,release='',completion_receipt=''))
    digest = (tmp_path/'hash').read_text()
    assert pending.pending_transaction_path(tmp_path,digest).is_file()
    with pytest.raises(ValueError,match='has not released'):
        pending.resolve_pending_transaction(repo_root=tmp_path,transaction_hash=digest)


@pytest.mark.parametrize("output_format", ["json", "text"])
@pytest.mark.parametrize("refusal", ["nonzero-stdout", "nonzero-stderr", "unadmitted", "malformed"])
def test_proposal_refusal_preserves_bounded_detail_and_prior_seal(
    tmp_path, monkeypatch, capsys, output_format, refusal,
):
    import hashlib
    import io
    from odylith.runtime.domain_intelligence import greenfield_host_flow as host
    from odylith.runtime.domain_intelligence import greenfield_prepare_cli as prepare
    from odylith.runtime.domain_intelligence import greenfield_proposals_cli as proposal_cli
    from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
    from odylith.runtime.domain_intelligence.greenfield_source_duty_entailment import EDIT_SOURCE_DUTY_DECISION_SET_VERSION, source_duty_entailment_task
    from odylith.runtime.domain_intelligence.greenfield_source_duty_ledger import preflight_greenfield_source_duty_ledger
    from odylith.runtime.domain_intelligence.greenfield_source_duty_view import compact_source_duty_view
    from tests.unit.install.test_greenfield_matrix_host_candidate import _flow
    from tests.unit.runtime.test_greenfield_source_duty_ledger import _yes_decisions

    candidate = {"version": "candidate", "result": {"status": "authored"}}
    flow, _host_run, installed_calls, host_calls, _paths, repo = _flow(
        tmp_path, contract={"version": "contract"}, candidate=candidate,
    )
    old_transaction = _transaction(repo_root=repo)
    old_path = pending.stage_pending_transaction(repo_root=repo, transaction=old_transaction)
    prompt = old_transaction.proposal["intent"]["prompt"]
    prepared = prepare_model_authoring_evidence(prompt=prompt, edit_evidence=flow.edit_evidence)
    source = prepared.evidence_source
    context = proposal_cli._edit_preservation(
        old_transaction, correction=prepared.edit_evidence, evidence_text=source,
    )
    semantics = old_transaction.proposal["intent"]["authored_semantics"]
    ledger = semantics["source_duty"]["ledger_receipt"]["ledger"]
    preflight = preflight_greenfield_source_duty_ledger(ledger, evidence_text=source)
    task = source_duty_entailment_task(preflight, evidence_text=source, edit_preservation=context)
    # This supplier fixture has no prior passive duties; EDIT custody still binds its seal.
    assert task["decision_set_schema"]["properties"]["edit_preservation"]["required"] == []
    decisions = _yes_decisions(preflight, evidence_text=source)
    decisions.update(version=EDIT_SOURCE_DUTY_DECISION_SET_VERSION,
                     verifier_task_sha256=task["verifier_task_sha256"],
                     edit_preservation={})
    gate = {"decision": "admit", "required_fields": [], "question": "",
            "owner_quote": old_transaction.proposal["intent"]["human_actors"][0],
            "task_quote": semantics["first_path_relations"][0]["event_quote"],
            "result_quote": semantics["first_path_relations"][-1]["visible_result_quote"]}

    def installed(command, timeout):
        installed_calls.append((list(command), timeout))
        captured = io.StringIO()
        args = list(command[command.index("greenfield") + 1:])
        # The real installed transport runs with cwd=repo; make that boundary explicit in-process.
        args[args.index("--repo-root") + 1] = str(repo)
        with contextlib.redirect_stdout(captured):
            status = proposal_cli.main(args)
        assert status == 0, captured.getvalue()
        payload = json.loads(captured.getvalue())
        if "candidate-contract" in command:
            assert payload["source_ledger"]["edit_preservation"] == context
        elif "source-ledger-check" in command:
            if "--decision-file" in command:
                assert payload["receipt"]["edit_preservation"] == context
                assert payload["receipt"]["version"] == "odylith.greenfield.source-duty-ledger-receipt.v9"
            else:
                assert payload["decision_task"] == task
        return subprocess.CompletedProcess(command, status, captured.getvalue(), "")

    def host_run(command, **kwargs):
        host_calls.append((list(command), str(kwargs["contract_text"]),
                           float(kwargs["timeout"]), Path(kwargs["cwd"])))
        schema = Path(command[command.index("--output-schema") + 1])
        assert schema.is_file() and schema.parent == Path(kwargs["cwd"])
        result = {"authority-gate-schema.json": gate,
                  "source-ledger-schema.json": compact_source_duty_view(ledger),
                  "source-duty-decision-schema.json": decisions,
                  "candidate-schema.json": candidate}[schema.name]
        return subprocess.CompletedProcess(command, 0, json.dumps(result), "")

    before = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    stdout = json.dumps({"mode": "error", "error": "Diagnostic only: CONFIRM cannot authorize create. " + "x" * 900})
    stderr = "compiler diagnostic: " + "y" * 900 if refusal == "nonzero-stderr" else ""
    if refusal == "malformed":
        stdout = "not JSON: CONFIRM cannot authorize create. " + "z" * 900
    returncode = 2 if refusal.startswith("nonzero") else 0
    proposal_calls = []

    def denied(path, gate_path, ledger_path, _timeout):
        proposal_calls.append(path)
        assert json.loads(path.read_text()) == candidate
        assert gate_path.is_file() and ledger_path.is_file()
        return subprocess.CompletedProcess(["odylith", "greenfield", "propose"], returncode, stdout, stderr)

    flow = host.HostCandidateFlow(**{**flow.__dict__, "invoke_propose": denied,
                                    "invoke_installed": installed, "prompt": prompt,
                                    "edit_evidence": prepared.edit_evidence,
                                    "transaction_hash": old_transaction.transaction_hash})
    monkeypatch.setattr(host, "_invoke_host", host_run)
    monkeypatch.setattr(prepare, "prepare_request", lambda _args: host.run_host_candidate_flow(flow))
    result = prepare.main(["--repo-root", str(repo), "--transaction-hash", old_transaction.transaction_hash,
                           "--edit", flow.edit_evidence, "--format", output_format])
    rendered = capsys.readouterr().out
    observation = flow.observation_sink
    assert result == 2 and observation["status"] == "failed" and observation["stage"] == "propose"
    assert observation["detail"] == (stderr or stdout)[:800]
    assert len(observation["detail"]) == 800
    assert observation["proposal_returncode"] == returncode
    assert observation["proposal_mode"] == ("invalid" if refusal == "malformed" else "error")
    assert observation["proposal_stdout_sha256"] == hashlib.sha256(stdout.encode()).hexdigest()
    assert observation["proposal_stderr_sha256"] == hashlib.sha256(stderr.encode()).hexdigest()
    assert len(host_calls) == 4 and len(installed_calls) == 4 and len(proposal_calls) == 1
    assert observation["candidate_host_invocations"] == observation["proposal_command_invocations"] == 1
    assert observation["runtime_semantic_model_call_count"] == observation["post_receipt_provider_invocations"] == 0
    assert flow.completion_receipt_sink == {}
    assert all(observation[key] for key in ("candidate_temp_cleaned", "authority_gate_temp_cleaned",
               "source_ledger_temp_cleaned", "source_duty_decision_temp_cleaned", "host_workspace_cleaned"))
    assert not proposal_calls[0].exists()
    assert {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()} == before
    assert pending.resolve_pending_transaction(repo_root=repo, transaction_hash=old_transaction.transaction_hash) == old_path
    assert "Greenfield preparation stopped during propose before publication." in rendered
    if output_format == "json":
        payload = json.loads(rendered)
        assert payload["mode"] == "error" and payload["bounded_journey"]["detail"] == observation["detail"]
        assert not {"confirmation", "completion_receipt", "product_create_transaction"} & payload.keys()
    else:
        assert "Checker detail" not in rendered
        assert observation["detail"] not in rendered
