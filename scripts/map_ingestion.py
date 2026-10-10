"""Discover and admit detached map imports; no model calls and no automatic retry."""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
import subprocess
from uuid import uuid4
from native_coordinator import ROOT, state, project, verify_repository, identifier, now, private_json, read_json, pilot

def command(arguments, require=(), timeout=45):
    argv = [str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/project-env.py'),
            '--cwd', project('map')['path'], '--shell-only']
    for name in require:
        argv += ['--require', name]
    argv += ['--', 'pnpm', '--silent', '--filter', '@lib/db-map', *arguments]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Map command timed out; inspect durable state before any retry') from exc
    if result.returncode:
        # Raw stderr may contain database/provider URLs. Retain it in the command's own logs.
        raise ValueError(f'Map command failed (exit {result.returncode}); inspect project diagnostics privately')
    if arguments[:2] == ['ingest:supervise', 'stop']:
        # The existing stop interface prints text, unlike start/list/control JSON.
        return {'status': 'stop_requested', 'job_id': arguments[-1],
                'instruction': 'Confirm worker and lock exit with a fresh snapshot; this is only a request'}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError('Map command returned no valid receipt; inspect jobs before any retry') from exc

def job_directory():
    return Path(project('map')['path']) / 'lib/db-map/.ingest-jobs'

def jobs():
    result = []
    directory = job_directory()
    for path in sorted(directory.glob('*/job.json')):
        identifier(path.parent.name)
        row = read_json(path)
        if row.get('id') != path.parent.name:
            raise ValueError('Supervisor journal identity mismatch')
        # No raw logs, argv, summaries or fatal-error strings in the public snapshot.
        result.append({key: row.get(key) for key in ('id','status','host','supervisor_pid','child_pid',
          'run_id','execution_id','started_at','finished_at','stop_reason','health_checks','last_health_at')})
        result[-1]['journal'] = str(path)
        if (path.parent / 'result.json').exists():
            terminal = read_json(path.parent / 'result.json')
            result[-1]['terminal'] = {key: terminal.get(key) for key in ('outcome','exit_code','signal','forced','stop_reason')}
            result[-1]['result_path'] = str(path.parent / 'result.json')
    return sorted(result, key=lambda r: r.get('started_at') or '', reverse=True)

def snapshot():
    verify_repository('map')
    controls = command(['ingest:control', 'list', '--json'], require=('DB_MAP_URL',))
    if not isinstance(controls, dict) or not isinstance(controls.get('quiescent'), bool) or not isinstance(controls.get('workers'), list):
        raise ValueError('Unexpected map control schema; admission blocked')
    return {'observed_at': now(), 'control': controls, 'jobs': jobs(),
            'claims': [read_json(p) for p in (state('map') / 'imports').glob('*/intent.json')],
            'limitations': 'PID presence is not identity. Database and journals must agree. No immediate desktop callback.'}

def accept(owner, job_id):
    identifier(owner); identifier(job_id)
    if pilot('map', 'status').get('status') != 'verified':
        raise ValueError('Native map scheduling pilot is not verified')
    current = snapshot()
    row = next((r for r in current['jobs'] if r['id'] == job_id), None)
    if row is None or not row.get('run_id') or not row.get('execution_id'):
        raise ValueError('Exact durable job/run/execution evidence required')
    if row['status'] == 'running' and not any(w.get('run_id') == row['run_id'] and w.get('execution_id') == row['execution_id'] for w in current['control']['workers']):
        raise ValueError('Running job and database worker disagree; investigate')
    path = state('map') / 'ingestion-acceptance.json'
    receipt = read_json(path) if path.exists() else {'job_id': job_id, 'observations': []}
    if receipt['job_id'] != job_id:
        raise ValueError('Reconcile the original acceptance job; do not replace it')
    evidence_path = state('map') / 'observations' / f'{uuid4()}.json'
    private_json(evidence_path, current)
    if not any(r['owner'] == owner for r in receipt['observations']):
        receipt['observations'].append({'owner': owner, 'at': now(), 'evidence': str(evidence_path),
                                        'run_id': row['run_id'], 'execution_id': row['execution_id']})
    receipt['status'] = 'verified' if len(receipt['observations']) >= 2 else 'observed_once'
    private_json(path, receipt)
    return receipt

def run_arguments(arguments):
    args = list(arguments)
    forbidden = {'--max-llm-requests','--max-cost-usd','--geocode-limit','--consolidate','--limit','--record'}
    if not args or any(a.split('=')[0] in forbidden for a in args):
        raise ValueError('This full-import interface requires uncapped file/resume scope; smoke and consolidation are separate')
    seen = set()
    index = 0 if args[0].startswith('--') else 1
    stages = {'extract','normalize','geocode','embed','match','canonical','consolidate','verify','report'}
    while index < len(args):
        flag = args[index]
        if flag in seen or flag not in {'--resume','--category','--from','--stop-after','--unlimited'}:
            raise ValueError('Unknown, duplicate or non-full-import argument')
        seen.add(flag)
        index += 1
        if flag == '--unlimited':
            continue
        if index >= len(args) or args[index].startswith('--'):
            raise ValueError('Missing managed argument value')
        value = args[index]
        if flag == '--resume': identifier(value)
        if flag == '--category' and not re.fullmatch(r'[a-z][a-z0-9_]*', value):
            raise ValueError('Invalid category slug')
        if flag in {'--from','--stop-after'} and value not in stages:
            raise ValueError('Invalid managed stage')
        index += 1
    if '--resume' in args:
        index = args.index('--resume')
        if index + 1 >= len(args):
            raise ValueError('Missing run UUID')
        identifier(args[index + 1])
        if any(a in args for a in ('--from','--category','--version')) or not args[0].startswith('--'):
            raise ValueError('Resume preserves original source, cohort and stages')
    elif args[0].startswith('--') or '--category' not in args:
        raise ValueError('New full runs need an exact data/poi file and category')
    else:
        path = (Path(project('map')['path']) / args[0]).resolve()
        if not path.is_relative_to((Path(project('map')['path']) / 'data/poi').resolve()) or not path.is_file():
            raise ValueError('New import must select an existing intended data/poi capture')
    if '--unlimited' not in args:
        args.append('--unlimited')
    return args

def start(owner, arguments):
    identifier(owner)
    args = run_arguments(arguments)
    if pilot('map', 'status').get('status') != 'verified':
        raise ValueError('Native map pilot must be verified')
    acceptance = state('map') / 'ingestion-acceptance.json'
    if not acceptance.exists() or read_json(acceptance).get('status') != 'verified':
        raise ValueError('Two independent native scheduled discovery observations are required')
    directory = state('map') / 'imports'
    directory.mkdir(mode=0o700, exist_ok=True)
    # This exclusive lease has no time-based expiry, including across ambiguous launches.
    lease = directory / 'active.claim'
    intent_id = str(uuid4())
    fd = os.open(lease, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(intent_id + '\n')
    path = directory / intent_id / 'intent.json'
    private_json(path, {'id': intent_id, 'owner': owner, 'status': 'checking', 'created_at': now(), 'argv': args})
    try:
        current = snapshot()
        controls = current['control']
        if controls.get('process_scan_error') or controls['maintenance'].get('maintenance') or not controls['quiescent']:
            raise ValueError('Map is not verified quiescent/admitted for a new import')
        if any(r['status'] != 'finished' for r in current['jobs']):
            raise ValueError('Unresolved supervisor journal exists; inspect before launch')
    except Exception:
        private_json(path, {'id': intent_id, 'owner': owner, 'status': 'not_submitted', 'created_at': now(), 'argv': args})
        lease.unlink()
        raise
    intent = {'id': intent_id, 'owner': owner, 'status': 'dispatching', 'created_at': now(), 'argv': args}
    private_json(path, intent)
    # After this point, all failures are ambiguous and the lease stays held.
    receipt = command(['ingest:supervise', 'start', '--local-only', '--', *args],
                      require=('DB_MAP_URL','FIREWORKS_API_KEY'))
    job_id = receipt.get('job_id') or receipt.get('id') or (receipt.get('job') or {}).get('id')
    identifier(job_id)
    intent.update(status='started', job_id=job_id, receipt=receipt, started_at=now())
    private_json(path, intent)
    return intent

def release(intent_id, evidence):
    identifier(intent_id)
    if not evidence.strip():
        raise ValueError('Verification evidence required')
    directory = state('map') / 'imports'
    lease = directory / 'active.claim'
    if lease.read_text().strip() != intent_id:
        raise ValueError('Intent does not own the active import claim')
    path = directory / intent_id / 'intent.json'
    intent = read_json(path)
    if not intent.get('job_id'):
        raise ValueError('Ambiguous dispatch requires manual journal reconciliation; no automatic release')
    current = snapshot()
    row = next((r for r in current['jobs'] if r['id'] == intent['job_id']), None)
    if row is None or row['status'] != 'finished' or not row.get('result_path') or not current['control']['quiescent']:
        raise ValueError('Exact terminal journal and database quiescence required')
    intent.update(status='reconciled', evidence=evidence, reconciled_at=now())
    private_json(path, intent)
    lease.unlink()
    return intent
