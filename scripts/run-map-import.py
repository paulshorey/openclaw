#!/usr/bin/env python3
"""Validate native ownership, witnessed completion and budgets before map watch."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / 'runtime/coordinator'
RECEIPT = WORKSPACE / 'state/map-native-completion.json'
MAP = Path('/Users/pshorey/git/map')
OWNER_SESSION = re.compile(r'^agent:main:dashboard:[A-Za-z0-9][A-Za-z0-9_.:-]*$')
MAX_SAFE_INTEGER = 2**53 - 1
OPENCLAW = '/opt/homebrew/bin/openclaw'
UUID = re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$', re.IGNORECASE)
MAX_OUTPUT_BYTES = 512 * 1024


def validate_owner(owner: str | None) -> str:
    if not owner or not OWNER_SESSION.fullmatch(owner) or ':subagent:' in owner:
        raise ValueError('--owner-session must be a visible agent:main:dashboard:... session; hidden subagents cannot own imports')
    return owner


def native_configuration(config_path: Path) -> None:
    config = json.loads(config_path.read_text())
    global_tools = config.get('tools', {})
    agents = config.get('agents', {})
    main_agent = agents.get('entries', {}).get('main', {})
    agent_tools = main_agent.get('tools', {})
    notify = agent_tools.get('exec', {}).get('notifyOnExit', global_tools.get('exec', {}).get('notifyOnExit', True))
    if notify is not True:
        raise ValueError('native background exec completion notifications are disabled')
    if 'process' in global_tools.get('deny', []) + agent_tools.get('deny', []):
        raise ValueError('OpenClaw process tool is denied')
    isolated = main_agent.get('heartbeat', {}).get('isolatedSession',
                agents.get('defaults', {}).get('heartbeat', {}).get('isolatedSession', False))
    if isolated is not False:
        raise ValueError('heartbeat isolatedSession must be false: isolated routing redirects background completion away from its owning dashboard conversation')
    target = main_agent.get('heartbeat', {}).get('target',
             agents.get('defaults', {}).get('heartbeat', {}).get('target'))
    if target == 'none':
        raise ValueError('heartbeat target must permit owner delivery: target=none removes raw completion details and internal dashboard projection')


def gateway_identity() -> dict[str, str | int]:
    # Capture launchctl output privately: its environment section may contain secrets.
    service = subprocess.run(
        ['/bin/launchctl', 'print', f'gui/{os.getuid()}/ai.openclaw.gateway'],
        capture_output=True, text=True, timeout=10,
    )
    if service.returncode:
        raise ValueError('current Gateway LaunchAgent is unavailable')
    pids = re.findall(r'^\s*pid = ([0-9]+)\s*$', service.stdout, re.MULTILINE)
    if len(pids) != 1 or int(pids[0]) <= 0:
        raise ValueError('current Gateway PID could not be verified')
    pid = int(pids[0])
    started = subprocess.run(
        ['/bin/ps', '-p', str(pid), '-o', 'lstart='],
        capture_output=True, text=True, timeout=10,
    )
    if started.returncode or not started.stdout.strip():
        raise ValueError('current Gateway process start time could not be verified')
    local_start = datetime.strptime(' '.join(started.stdout.split()), '%a %b %d %H:%M:%S %Y')
    return {'pid': pid, 'started_at': local_start.astimezone(timezone.utc).isoformat()}


def timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f'completion receipt is missing {field}')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'completion receipt has invalid {field}') from exc
    if result.tzinfo is None:
        raise ValueError(f'completion receipt needs timezone-aware {field}')
    return result.astimezone(timezone.utc)


def validate_receipt(path: Path, owner: str, gateway: dict, now: datetime | None = None) -> dict:
    path = path.expanduser().resolve()
    if not path.is_relative_to(WORKSPACE.resolve()):
        raise ValueError('completion receipt must remain in the ignored coordinator workspace')
    try:
        receipt = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise ValueError('native completion proof is missing; witness a harmless background completion in this dashboard session first') from exc
    if not isinstance(receipt, dict) or receipt.get('schema_version') != 1:
        raise ValueError('unsupported native completion receipt schema')
    if receipt.get('owner_session') != owner:
        raise ValueError('native completion receipt belongs to another session; do not borrow its proof')
    if receipt.get('gateway') != gateway:
        raise ValueError('native completion receipt is stale for the current Gateway PID/start time')
    if receipt.get('completion_status') != 'succeeded':
        raise ValueError('native completion receipt does not prove a successful completion')
    if receipt.get('notification_kind') != 'terminal_callback':
        raise ValueError('completion receipt must prove the targeted terminal_callback integration; native exit events can be delayed')
    for field in ('native_process_id', 'completion_event_id'):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError(f'native completion receipt is missing {field}')
    completed = timestamp(receipt.get('completed_at'), 'completed_at')
    checked = timestamp(receipt.get('checked_at'), 'checked_at')
    started = timestamp(gateway['started_at'], 'gateway.started_at')
    current = now or datetime.now(timezone.utc)
    if not started <= completed <= checked <= current:
        raise ValueError('native completion receipt timestamps do not match this Gateway lifetime')
    evidence_value = receipt.get('evidence_path')
    if not isinstance(evidence_value, str) or not Path(evidence_value).is_absolute():
        raise ValueError('native completion receipt needs an absolute private evidence_path')
    evidence = Path(evidence_value).resolve()
    if not evidence.is_relative_to(WORKSPACE.resolve()) or not evidence.is_file() or evidence.stat().st_size == 0:
        raise ValueError('native completion evidence file is missing or outside the private workspace')
    return receipt


def validate_budgets(run_args: list[str]) -> dict[str, Decimal]:
    budgets = {}
    for flag in ('--max-llm-requests', '--max-cost-usd', '--geocode-limit'):
        if run_args.count(flag) != 1 or any(value.startswith(flag + '=') for value in run_args):
            raise ValueError(f'provide exactly one explicit {flag} followed by its nonnegative budget')
        index = run_args.index(flag)
        if index + 1 >= len(run_args):
            raise ValueError(f'missing budget value for {flag}')
        value = run_args[index + 1]
        try:
            numeric = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f'invalid budget for {flag}') from exc
        if not numeric.is_finite() or numeric < 0:
            raise ValueError(f'{flag} must be a finite nonnegative budget')
        if flag != '--max-cost-usd' and (not re.fullmatch(r'[0-9]+', value) or numeric > MAX_SAFE_INTEGER):
            raise ValueError(f'{flag} must be a nonnegative safe integer')
        if flag == '--max-cost-usd' and not re.fullmatch(r'(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', value):
            raise ValueError('--max-cost-usd must use a nonnegative decimal number')
        # The downstream Node parser uses Number, which cannot represent huge finite decimals.
        if flag == '--max-cost-usd' and numeric > Decimal('1.7976931348623157e308'):
            raise ValueError('--max-cost-usd exceeds the supported numeric range')
        if flag == '--max-cost-usd' and numeric > 0 and float(numeric) == 0:
            raise ValueError('--max-cost-usd is too small to represent')
        budgets[flag] = numeric
    if '--consolidate' in run_args:
        raise ValueError('global consolidation is outside the native file queue')
    return budgets


def explicit_provider_free_scope(run_args: list[str], budgets: dict[str, Decimal]) -> bool:
    """Only a new, explicit report/verify suffix can omit provider credentials.

    Normalization/geocoder limits do not constrain embedding, matching or fusion.
    Resume retains the original stage scope, regardless of its replacement budgets.
    Be conservative about malformed, duplicate or unrecognized stage options.
    """
    if not run_args or run_args[0].startswith('--') or any(value != 0 for value in budgets.values()):
        return False
    valued_flags = {'--category', '--record', '--limit', '--from', '--stop-after',
                    '--max-llm-requests', '--max-cost-usd', '--geocode-limit'}
    values = {}
    seen = set()
    index = 1
    while index < len(run_args):
        flag = run_args[index]
        if flag in seen:
            return False
        seen.add(flag)
        if flag == '--dry-run':
            index += 1
            continue
        if flag not in valued_flags or index + 1 >= len(run_args) or run_args[index + 1].startswith('--'):
            return False
        values[flag] = run_args[index + 1]
        index += 2
    if not values.get('--category') or values.get('--from') not in ('report', 'verify'):
        return False
    if '--stop-after' in values:
        if values['--stop-after'] not in ('report', 'verify'):
            return False
        if values['--from'] == 'verify' and values['--stop-after'] == 'report':
            return False
    return True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f'{path.name}.{os.getpid()}.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        json.dump(value, output, indent=2)
        output.write('\n')
    temporary.replace(path)


def private_text(path: Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        output.write(text)


def parse_json_documents(text: str) -> list[dict]:
    if len(text.encode('utf-8')) > MAX_OUTPUT_BYTES:
        raise ValueError('watch receipts exceed the bounded capture; inspect private stdout')
    decoder = json.JSONDecoder()
    documents = []
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index == len(text):
            break
        document, index = decoder.raw_decode(text, index)
        if not isinstance(document, dict):
            raise ValueError('watch receipts must be JSON objects')
        documents.append(document)
    return documents


def durable_terminal(output: str, run_args: list[str], started_at: str) -> tuple[Path, dict]:
    documents = parse_json_documents(output)
    if len(documents) != 2 or documents[0].get('event') != 'ingestion.started':
        raise ValueError('expected one watch launch receipt and one terminal result; inspect private stdout')
    launch, terminal = documents
    job_id = launch.get('job_id')
    if not isinstance(job_id, str) or not UUID.fullmatch(job_id):
        raise ValueError('watch launch receipt needs an actual job UUID')
    expected = MAP / 'lib/db-map/.ingest-jobs' / job_id / 'result.json'
    if expected.resolve() != expected.absolute() or launch.get('result') != str(expected):
        raise ValueError('watch result path is not the canonical private map result')
    result = json.loads(expected.read_text())
    job = json.loads(expected.with_name('job.json').read_text())
    event_id = f'ingestion:{job_id}:terminal'
    if not isinstance(result, dict) or result != terminal:
        raise ValueError('watch terminal output does not match its durable result')
    if job.get('id') != job_id or job.get('mode') != 'native' or job.get('status') != 'finished' or job.get('argv') != run_args:
        raise ValueError('durable map job does not match this foreground watch scope')
    if timestamp(job.get('started_at'), 'job.started_at') < timestamp(started_at, 'wrapper.started_at'):
        raise ValueError('durable map result predates this wrapper; do not replay another execution')
    if result.get('job_id') != job_id or result.get('event_id') != event_id or job.get('result') != result:
        raise ValueError('durable map job/result/event identity does not match')
    for field in ('run_id', 'execution_id'):
        identifier = result.get(field)
        if identifier != job.get(field) or (identifier is not None and (not isinstance(identifier, str) or not UUID.fullmatch(identifier))):
            raise ValueError(f'durable map {field} identity does not match')
    if result.get('outcome') not in ('succeeded', 'paused', 'partial', 'waiting_budget', 'needs_attention'):
        raise ValueError('durable map result has no recognized terminal outcome')
    return expected, result


def foreground_watch(command: list[str], directory: Path) -> tuple[int, str]:
    """Ordinary code waits on one foreground child; never detach or invoke a model."""
    stdout_path = directory / 'watch.stdout'
    stderr_path = directory / 'watch.stderr'
    stdout_fd = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    stderr_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(stdout_fd, 'w') as stdout_log, os.fdopen(stderr_fd, 'w') as stderr_log:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=stderr_log,
                                 text=True, encoding='utf-8', errors='replace', env=os.environ.copy())
        previous_handlers = {}
        def forward_stop(signum, _frame):
            if child.poll() is None:
                child.send_signal(signum)
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous_handlers[signum] = signal.signal(signum, forward_stop)
        captured = []
        size = 0
        try:
            while True:
                chunk = child.stdout.readline(MAX_OUTPUT_BYTES + 1)
                if not chunk:
                    break
                stdout_log.write(chunk)
                stdout_log.flush()
                sys.stdout.write(chunk)
                sys.stdout.flush()
                size += len(chunk.encode('utf-8'))
                if size <= MAX_OUTPUT_BYTES:
                    captured.append(chunk)
            code = child.wait()
        except BaseException:
            if child.poll() is None:
                child.send_signal(signal.SIGTERM)
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            raise
        finally:
            child.stdout.close()
            for signum, handler in previous_handlers.items():
                signal.signal(signum, handler)
        if size > MAX_OUTPUT_BYTES:
            raise ValueError('watch receipts exceed the bounded capture; inspect private stdout')
        return code, ''.join(captured)


def terminal_callback(owner: str, event_id: str, text: str, directory: Path) -> dict:
    """One targeted wake-now attempt, with durable acceptance/ambiguity evidence."""
    receipt_path = directory / 'callback.json'
    claim = directory / 'callback.claim'
    try:
        descriptor = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError('terminal callback already attempted; inspect its receipt instead of resending')
    with os.fdopen(descriptor, 'w') as output:
        output.write(event_id + '\n')
    receipt = {'schema_version': 1, 'notification_kind': 'terminal_callback', 'owner_session': owner,
               'event_id': event_id, 'status': 'sending', 'attempted_at': utc_now()}
    private_json(receipt_path, receipt)
    try:
        result = subprocess.run([OPENCLAW, 'system', 'event', '--session-key', owner, '--mode', 'now',
                                 '--text', text, '--json', '--timeout', '15000'],
                                capture_output=True, text=True, timeout=20)
        private_text(directory / 'callback.stdout', result.stdout)
        private_text(directory / 'callback.stderr', result.stderr)
        try:
            acknowledgement = json.loads(result.stdout)
        except ValueError:
            acknowledgement = None
        receipt['exit_code'] = result.returncode
        receipt['acknowledgement'] = acknowledgement
        if result.returncode == 0 and isinstance(acknowledgement, dict) and acknowledgement.get('ok') is True:
            receipt['status'] = 'accepted'
        elif result.returncode == 0:
            receipt['status'] = 'uncertain'
            receipt['reason'] = 'CLI exited zero without a valid acceptance acknowledgement; do not resend automatically'
        else:
            receipt['status'] = 'failed'
    except subprocess.TimeoutExpired as exc:
        for name, value in (('callback.stdout', exc.stdout), ('callback.stderr', exc.stderr)):
            if value:
                private_text(directory / name, value.decode(errors='replace') if isinstance(value, bytes) else value)
        receipt['status'] = 'uncertain'
        receipt['reason'] = 'callback timed out; it might have been accepted, so do not resend automatically'
    except OSError as exc:
        receipt['status'] = 'failed'
        receipt['reason'] = f'callback could not launch ({type(exc).__name__})'
    receipt['finished_at'] = utc_now()
    private_json(receipt_path, receipt)
    return receipt


def preflight(owner: str, gateway: dict, directory: Path) -> int:
    identifier = str(uuid4())
    event_id = f'map-terminal-preflight:{identifier}'
    evidence_path = directory / 'preflight.json'
    evidence = {'schema_version': 1, 'notification_kind': 'terminal_callback', 'owner_session': owner,
                'gateway': gateway, 'event_id': event_id, 'marker': event_id, 'started_at': utc_now()}
    time.sleep(12)
    evidence.update({'completed_at': utc_now(), 'outcome': 'succeeded', 'exit_code': 0})
    private_json(evidence_path, evidence)
    text = f'Exec completed (map-preflight-{identifier}, code 0) :: {event_id} evidence={evidence_path} outcome=succeeded'
    callback = terminal_callback(owner, event_id, text, directory)
    print(json.dumps({'event': 'map.preflight.terminal', 'event_id': event_id, 'evidence_path': str(evidence_path),
                      'callback_receipt': str(directory / 'callback.json'), 'callback_status': callback['status'],
                      'acknowledgement': {'ok': True} if callback['status'] == 'accepted' else None,
                      'instruction': 'Acceptance is not automatic-continuation proof; verify this marker in the owning conversation before recording a completion receipt.'}), flush=True)
    return 0 if callback['status'] == 'accepted' else 78


def run_import(command: list[str], run_args: list[str], owner: str, gateway: dict, directory: Path) -> int:
    started_at = utc_now()
    wrapper_id = str(uuid4())
    record = {'schema_version': 1, 'notification_kind': 'terminal_callback', 'owner_session': owner,
              'gateway': gateway, 'started_at': started_at, 'wrapper_id': wrapper_id}
    terminal_path = directory / 'terminal.json'
    callback_attempted = False
    try:
        code, output = foreground_watch(command, directory)
        record['exit_code'] = code
        result_path, result = durable_terminal(output, run_args, started_at)
        record.update({'completed_at': utc_now(), 'result_path': str(result_path), 'event_id': result['event_id'],
                       'job_id': result['job_id'], 'run_id': result.get('run_id'),
                       'execution_id': result.get('execution_id'), 'outcome': result['outcome']})
        private_json(terminal_path, record)
        text = f"Exec completed (map-{result['job_id']}, code {code}) :: {result['event_id']} result={result_path} run={result.get('run_id') or 'unregistered'} outcome={result['outcome']}"
        callback_attempted = True
        callback = terminal_callback(owner, result['event_id'], text, directory)
        record['callback_status'] = callback['status']
        record['notification_blocked'] = callback['status'] != 'accepted'
        if record['notification_blocked']:
            record['instruction'] = 'Callback failed or is uncertain; inspect evidence/owner history and do not advance or relaunch.'
        private_json(terminal_path, record)
        print(json.dumps({'event': 'openclaw.import_runner.terminal', 'event_id': result['event_id'],
                          'evidence_path': str(terminal_path), 'callback_receipt': str(directory / 'callback.json'),
                          'callback_status': callback['status'], 'notification_blocked': record['notification_blocked']}), flush=True)
        return code if callback['status'] == 'accepted' and code >= 0 else 78
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        event_id = record.get('event_id') if callback_attempted else f'map-import-wrapper:{wrapper_id}:terminal'
        record.update({'completed_at': utc_now(), 'outcome': 'blocked', 'error': str(exc), 'event_id': event_id,
                       'instruction': 'Inspect private evidence; no import relaunch or queue advance.'})
        private_json(terminal_path, record)
        text = f"Exec completed (map-wrapper-{wrapper_id}, code {record.get('exit_code', 78)}) :: {event_id} evidence={terminal_path} outcome=blocked"
        try:
            if callback_attempted:
                record['callback_status'] = 'uncertain'
                record['callback_error'] = 'Callback already attempted; inspect its receipt and owner history without resending.'
            else:
                callback = terminal_callback(owner, event_id, text, directory)
                record['callback_status'] = callback['status']
        except (OSError, ValueError, TypeError, subprocess.SubprocessError) as callback_error:
            record['callback_status'] = 'uncertain'
            record['callback_error'] = str(callback_error)
        private_json(terminal_path, record)
        print(json.dumps({'event': 'openclaw.import_runner.blocked', 'event_id': event_id,
                          'evidence_path': str(terminal_path), 'callback_status': record['callback_status'],
                          'instruction': 'No verified map terminal result. Inspect evidence; do not relaunch or advance.'}), flush=True)
        return 78


def parse_arguments(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    if '--' in argv:
        boundary = argv.index('--')
        wrapper_args, run_args = argv[:boundary], argv[boundary + 1:]
    else:
        wrapper_args, run_args = argv, []
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='check configuration; include owner to verify witnessed completion')
    mode.add_argument('--preflight', action='store_true', help='native exec only: harmless 12-second targeted terminal callback test')
    parser.add_argument('--owner-session', help='actual visible dashboard session owning background exec')
    parser.add_argument('--completion-receipt', type=Path, default=RECEIPT, help='private witnessed-completion receipt')
    parser.add_argument('--max-hours', type=int, help='original remaining deadline, 1..168 hours')
    for flag in ('--check', '--preflight', '--owner-session', '--completion-receipt', '--max-hours'):
        if sum(value == flag or value.startswith(flag + '=') for value in wrapper_args) > 1:
            parser.error(f'duplicate wrapper option {flag}')
    options = parser.parse_args(wrapper_args)
    if options.max_hours is not None and not 1 <= options.max_hours <= 168:
        parser.error('--max-hours must be 1..168')
    if (options.check or options.preflight) and run_args:
        parser.error('--check/--preflight do not accept ingestion arguments')
    if options.preflight and (options.max_hours is not None or any(value == '--completion-receipt' or value.startswith('--completion-receipt=') for value in wrapper_args)):
        parser.error('--preflight does not accept an ingestion deadline or completion receipt')
    if not options.check and not options.preflight and (options.max_hours is None or not run_args):
        parser.error('provide --owner-session SESSION --max-hours 1..168 -- <managed run arguments with explicit budgets>')
    return options, run_args


def main(argv: list[str] | None = None) -> int:
    options, run_args = parse_arguments(sys.argv[1:] if argv is None else argv)
    try:
        if not options.check and os.environ.get('OPENCLAW_SHELL') != 'exec':
            raise ValueError('launch through OpenClaw exec background=true; a terminal or detached shell has no native completion owner')
        owner = validate_owner(options.owner_session) if options.owner_session or not options.check else None
        budgets = validate_budgets(run_args) if not options.check and not options.preflight else {}
        native_configuration(Path.home() / '.openclaw/openclaw.json')
        gateway = gateway_identity()
        if owner and not options.preflight:
            validate_receipt(options.completion_receipt, owner, gateway)
        if options.check:
            print(json.dumps({'native_configuration': 'enabled', 'gateway': gateway, 'owner_session': owner,
                              'completion_proof': 'verified' if owner else 'not checked; pass --owner-session after recording an actual completion'}))
            return 0
        directory = WORKSPACE / 'logs/map-import-runner' / str(uuid4())
        directory.mkdir(parents=True, mode=0o700)
        if options.preflight:
            return preflight(owner, gateway, directory)
        requirements = ['--require', 'DB_MAP_URL']
        if not explicit_provider_free_scope(run_args, budgets):
            requirements += ['--require', 'FIREWORKS_API_KEY']
        command = [str(ROOT / '.venv/bin/python'), str(ROOT / 'scripts/project-env.py'),
                   '--cwd', str(MAP), '--shell-only', *requirements, '--',
                   'pnpm', '--silent', '--filter', '@lib/db-map', 'ingest:supervise', 'watch',
                   '--max-hours', str(options.max_hours), '--', *run_args]
        return run_import(command, run_args, owner, gateway, directory)
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        # Do not echo raw launchctl/ps output or credential-bearing child environments.
        print(f'Blocked: {exc}', file=sys.stderr)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
