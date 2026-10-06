#!/usr/bin/env python3
"""Isolated native-runner admission tests: no Gateway, database or provider calls."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch


spec = importlib.util.spec_from_file_location('map_runner', Path(__file__).with_name('run-map-import.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

OWNER = 'agent:main:dashboard:fixture-owner'
GATEWAY = {'pid': 1234, 'started_at': '2026-10-05T08:00:00+00:00'}
NOW = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)
ZERO_BUDGETS = ['--max-llm-requests', '0', '--max-cost-usd', '0', '--geocode-limit', '0']


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.workspace = self.root / 'runtime/coordinator'
        self.workspace.mkdir(parents=True)
        self.evidence = self.workspace / 'completion-note.md'
        self.evidence.write_text('Fixture: witnessed automatic background completion.\n')
        self.receipt_path = self.workspace / 'map-native-completion.json'
        self.receipt = {'schema_version': 1, 'owner_session': OWNER, 'gateway': GATEWAY,
                        'checked_at': '2026-10-05T09:01:00+00:00', 'completed_at': '2026-10-05T09:00:00+00:00',
                        'native_process_id': 'fixture-process', 'completion_event_id': 'fixture-event',
                        'completion_status': 'succeeded', 'notification_kind': 'internal_system_event', 'evidence_path': str(self.evidence)}
        self.receipt_path.write_text(json.dumps(self.receipt))
        self.workspace_patch = patch.object(runner, 'WORKSPACE', self.workspace)
        self.workspace_patch.start()
        self.addCleanup(self.workspace_patch.stop)
        self.map = (self.root / 'map').resolve()
        self.map_patch = patch.object(runner, 'MAP', self.map)
        self.map_patch.start()
        self.addCleanup(self.map_patch.stop)
        self.addCleanup(self.directory.cleanup)

    def validate_receipt(self):
        return runner.validate_receipt(self.receipt_path, OWNER, GATEWAY, NOW)

    def rewrite_receipt(self, **changes):
        self.receipt.update(changes)
        self.receipt_path.write_text(json.dumps(self.receipt))

    def test_visible_dashboard_owner_is_required(self):
        self.assertEqual(runner.validate_owner(OWNER), OWNER)
        for owner in (None, 'agent:main:subagent:fixture', 'agent:main:dashboard:parent:subagent:fixture', 'agent:main:main'):
            with self.subTest(owner=owner), self.assertRaises(ValueError):
                runner.validate_owner(owner)

    def test_current_witnessed_receipt_is_accepted(self):
        self.assertEqual(self.validate_receipt(), self.receipt)

    def test_legacy_native_structured_system_or_chat_proof_cannot_admit_generic_events(self):
        for kind in (None, 'native_exec_completion', 'terminal_callback', 'chat_callback'):
            with self.subTest(kind=kind):
                self.rewrite_receipt(notification_kind=kind)
                with self.assertRaisesRegex(ValueError, 'generic internal_system_event'):
                    self.validate_receipt()

    def test_another_dashboard_cannot_borrow_receipt(self):
        self.rewrite_receipt(owner_session='agent:main:dashboard:another')
        with self.assertRaisesRegex(ValueError, 'another session'):
            self.validate_receipt()

    def test_pid_reuse_or_gateway_restart_invalidates_receipt(self):
        for identity in ({**GATEWAY, 'pid': 9999}, {**GATEWAY, 'started_at': '2026-10-05T08:01:00+00:00'}):
            with self.subTest(identity=identity):
                self.rewrite_receipt(gateway=identity)
                with self.assertRaisesRegex(ValueError, 'stale'):
                    self.validate_receipt()

    def test_receipt_cannot_precede_gateway_or_claim_future_completion(self):
        for changes in ({'completed_at': '2026-10-05T07:59:59+00:00'},
                        {'checked_at': '2026-10-05T10:00:01+00:00'},
                        {'completed_at': '2026-10-05T09:00:00'}):
            with self.subTest(changes=changes):
                original = self.receipt.copy()
                self.rewrite_receipt(**changes)
                with self.assertRaises(ValueError):
                    self.validate_receipt()
                self.receipt = original

    def test_missing_or_failed_completion_is_rejected(self):
        self.receipt_path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.validate_receipt()
        self.rewrite_receipt(completion_status='failed')
        with self.assertRaisesRegex(ValueError, 'successful'):
            self.validate_receipt()

    def test_receipt_requires_process_event_and_private_evidence(self):
        for changes in ({'native_process_id': ''}, {'completion_event_id': ''},
                        {'evidence_path': str(self.root / 'outside.md')},
                        {'evidence_path': 'relative-note.md'}):
            with self.subTest(changes=changes):
                original = self.receipt.copy()
                self.rewrite_receipt(**changes)
                with self.assertRaises(ValueError):
                    self.validate_receipt()
                self.receipt = original
        self.evidence.unlink()
        self.rewrite_receipt()
        with self.assertRaisesRegex(ValueError, 'evidence file'):
            self.validate_receipt()

    def test_receipt_outside_private_workspace_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ignored coordinator workspace'):
            runner.validate_receipt(self.root / 'receipt.json', OWNER, GATEWAY, NOW)

    def test_all_zero_budgets_are_valid(self):
        self.assertTrue(all(value == 0 for value in runner.validate_budgets(ZERO_BUDGETS).values()))

    def test_optional_budgets_when_present_are_unique_and_finite(self):
        cases = [[*ZERO_BUDGETS, '--max-cost-usd', '1'],
                 ['--max-llm-requests', '1.5', *ZERO_BUDGETS[2:]],
                 ['--max-llm-requests', str(2**53), *ZERO_BUDGETS[2:]],
                 [*ZERO_BUDGETS, '--max-cost-usd=1'], [*ZERO_BUDGETS, '--consolidate'],
                 ['--max-cost-usd'], ['--unlimited', '--unlimited'], ['--unlimited=true']]
        for cost in ('NaN', 'Infinity', '-1', '1_0', '1e999', '1e-999'):
            cases.append([*ZERO_BUDGETS[:3], cost, *ZERO_BUDGETS[4:]])
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                runner.validate_budgets(args)

    def test_manual_caps_are_independently_optional_and_conflict_with_unlimited(self):
        self.assertEqual(runner.validate_budgets([]), {})
        for arguments in (['--max-cost-usd', '0.10'], ['--max-llm-requests', '4'], ['--geocode-limit', '0']):
            with self.subTest(arguments=arguments):
                self.assertEqual(len(runner.validate_budgets(arguments)), 1)
                with self.assertRaisesRegex(ValueError, 'cannot be combined'):
                    runner.validate_budgets([*arguments, '--unlimited'])

    def test_gateway_identity_captures_only_pid_and_start_time(self):
        calls = [subprocess.CompletedProcess([], 0, 'state = running\n pid = 1234\n environment = {SECRET=fixture-secret}\n', ''),
                 subprocess.CompletedProcess([], 0, 'Mon Oct  5 08:00:00 2026\n', '')]
        output = io.StringIO()
        with patch.object(runner.subprocess, 'run', side_effect=calls) as run, redirect_stdout(output), redirect_stderr(output):
            identity = runner.gateway_identity()
        self.assertEqual(identity['pid'], 1234)
        self.assertEqual(datetime.fromisoformat(identity['started_at']).second, 0)
        self.assertEqual(run.call_args_list[1].args[0][-2:], ['-o', 'lstart='])
        self.assertNotIn('fixture-secret', output.getvalue())

    def test_gateway_without_verified_process_cannot_launch(self):
        for calls in ([subprocess.CompletedProcess([], 1, '', '')],
                      [subprocess.CompletedProcess([], 0, 'pid = 1234\n', ''), subprocess.CompletedProcess([], 1, '', '')]):
            with self.subTest(calls=calls), patch.object(runner.subprocess, 'run', side_effect=calls), self.assertRaises(ValueError):
                runner.gateway_identity()

    def main_fixture(self, args, shell='exec'):
        output = io.StringIO()
        with patch.object(runner, 'native_configuration'), patch.object(runner, 'gateway_identity', return_value=GATEWAY), \
             patch.object(runner, 'validate_receipt') as receipt, patch.object(runner, 'run_import', return_value=0) as execute, \
             patch.dict(os.environ, {'OPENCLAW_SHELL': shell}, clear=True), redirect_stdout(output), redirect_stderr(output):
            result = runner.main(args)
        return result, output.getvalue(), receipt, execute

    def test_new_report_scope_preserves_file_category_deadline_and_zero_budgets(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--from', 'report', *ZERO_BUDGETS]
        result, _, receipt, execute = self.main_fixture(['--owner-session', OWNER, '--max-hours', '7', '--', *scope])
        self.assertEqual(result, 0)
        receipt.assert_called_once()
        command = execute.call_args.args[0]
        self.assertEqual(command[command.index('watch') + 1:], ['--max-hours', '7', '--', *scope])
        self.assertIn('DB_MAP_URL', command)
        self.assertNotIn('FIREWORKS_API_KEY', command)

    def test_default_new_file_launch_is_unlimited_without_full_run_deadline(self):
        scope = ['data/poi/source.json', '--category', 'campground']
        result, _, receipt, execute = self.main_fixture(['--owner-session', OWNER, '--', *scope])
        self.assertEqual(result, 0)
        receipt.assert_called_once()
        command = execute.call_args.args[0]
        forwarded = [*scope, '--unlimited']
        self.assertEqual(command[command.index('watch') + 1:], ['--', *forwarded])
        self.assertEqual(execute.call_args.args[1], forwarded)
        self.assertNotIn('--max-hours', command)
        self.assertIn('FIREWORKS_API_KEY', command)

    def test_default_resume_clears_inherited_caps_and_has_no_deadline(self):
        scope = ['--resume', '11111111-2222-4333-8444-555555555555']
        result, _, _, execute = self.main_fixture(['--owner-session', OWNER, '--', *scope])
        self.assertEqual(result, 0)
        command = execute.call_args.args[0]
        self.assertEqual(command[command.index('watch') + 1:], ['--', *scope, '--unlimited'])
        self.assertEqual(execute.call_args.args[1], [*scope, '--unlimited'])
        self.assertNotIn('--max-hours', command)

    def test_explicit_unlimited_passes_once_and_optional_deadline_is_preserved(self):
        scope = ['--resume', '11111111-2222-4333-8444-555555555555', '--unlimited']
        result, _, _, execute = self.main_fixture(['--owner-session', OWNER, '--max-hours', '12', '--', *scope])
        self.assertEqual(result, 0)
        command = execute.call_args.args[0]
        self.assertEqual(command[command.index('watch') + 1:], ['--max-hours', '12', '--', *scope])
        self.assertEqual(command.count('--unlimited'), 1)

    def test_optional_single_manual_cap_neither_requires_other_caps_nor_sets_deadline(self):
        scope = ['--resume', '11111111-2222-4333-8444-555555555555', '--max-cost-usd', '1.25']
        result, _, _, execute = self.main_fixture(['--owner-session', OWNER, '--', *scope])
        self.assertEqual(result, 0)
        command = execute.call_args.args[0]
        self.assertEqual(command[command.index('watch') + 1:], ['--', *scope])
        self.assertNotIn('--unlimited', command)
        self.assertNotIn('--max-hours', command)
        self.assertIn('FIREWORKS_API_KEY', command)

    def test_explicit_zero_budget_suffix_still_exempts_key_without_deadline(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--from', 'verify', *ZERO_BUDGETS]
        result, _, _, execute = self.main_fixture(['--owner-session', OWNER, '--', *scope])
        self.assertEqual(result, 0)
        command = execute.call_args.args[0]
        self.assertEqual(command[command.index('watch') + 1:], ['--', *scope])
        self.assertNotIn('FIREWORKS_API_KEY', command)
        self.assertNotIn('--max-hours', command)

    def test_suffix_without_all_explicit_zero_caps_still_requires_fireworks(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--from', 'report', '--max-cost-usd', '0']
        self.assertFalse(runner.explicit_provider_free_scope(scope, runner.validate_budgets(scope)))

    def test_unlimited_with_manual_caps_blocks_before_foreground_launch(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--unlimited', '--max-cost-usd', '0']
        result, output, _, execute = self.main_fixture(['--owner-session', OWNER, '--', *scope])
        self.assertEqual(result, 78)
        self.assertIn('cannot be combined', output)
        execute.assert_not_called()

    def test_optional_manual_deadline_rejects_invalid_values(self):
        for hours in ('0', '169', '-1', '1.5'):
            with self.subTest(hours=hours), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                runner.parse_arguments(['--owner-session', OWNER, '--max-hours', hours, '--', 'source.json', '--category', 'campground'])

    def test_new_verify_scope_without_conflicts_is_provider_free(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--from', 'verify', *ZERO_BUDGETS]
        self.assertTrue(runner.explicit_provider_free_scope(scope, runner.validate_budgets(scope)))

    def test_zero_normalization_budgets_do_not_make_arbitrary_or_resume_scopes_free(self):
        scopes = [['data/poi/source.json', '--category', 'campground', *ZERO_BUDGETS],
                  ['--resume', '11111111-2222-4333-8444-555555555555', *ZERO_BUDGETS]]
        for scope in scopes:
            with self.subTest(scope=scope):
                result, _, _, execute = self.main_fixture(['--owner-session', OWNER, '--max-hours', '7', '--', *scope])
                self.assertEqual(result, 0)
                command = execute.call_args.args[0]
                self.assertIn('FIREWORKS_API_KEY', command)
                self.assertEqual(command[command.index('watch') + 1:], ['--max-hours', '7', '--', *scope])

    def test_provider_free_exemption_rejects_duplicate_alias_and_resume_stage_claims(self):
        base = ['data/poi/source.json', '--category', 'campground', '--from', 'report', *ZERO_BUDGETS]
        for extra in (['--from', 'verify'], ['--start-at', 'report'], ['--from-stage', 'report'],
                      ['--from=verify'], ['--resume', '11111111-2222-4333-8444-555555555555'],
                      ['--stop-after', 'normalize'], ['--consolidate'], ['--reprocess', 'all']):
            with self.subTest(extra=extra):
                self.assertFalse(runner.explicit_provider_free_scope([*base, *extra], runner.validate_budgets(base)))

    def test_positive_budgets_keep_provider_requirement_for_report_scope(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--from', 'report',
                 '--max-llm-requests', '0', '--max-cost-usd', '.10', '--geocode-limit', '0']
        self.assertFalse(runner.explicit_provider_free_scope(scope, runner.validate_budgets(scope)))

    def test_paid_scope_requires_fireworks_without_changing_file_scope(self):
        scope = ['data/poi/source.json', '--category', 'campground', '--max-llm-requests', '4', '--max-cost-usd', '.10', '--geocode-limit', '0']
        result, _, _, execute = self.main_fixture(['--owner-session', OWNER, '--max-hours', '48', '--', *scope])
        self.assertEqual(result, 0)
        command = execute.call_args.args[0]
        self.assertIn('FIREWORKS_API_KEY', command)
        self.assertEqual(command[command.index('watch') + 4:], scope)

    def test_missing_owner_terminal_and_hidden_session_do_not_execute(self):
        for header, shell in (([], 'exec'), (['--owner-session', OWNER], ''),
                              (['--owner-session', 'agent:main:subagent:fixture'], 'exec')):
            with self.subTest(header=header, shell=shell):
                result, _, _, execute = self.main_fixture([*header, '--max-hours', '1', '--', '--resume', 'fixture', *ZERO_BUDGETS], shell)
                self.assertEqual(result, 78)
                execute.assert_not_called()

    def test_config_check_clearly_separates_completion_proof(self):
        result, output, receipt, execute = self.main_fixture(['--check'], shell='')
        self.assertEqual(result, 0)
        self.assertIn('not checked', output)
        receipt.assert_not_called()
        execute.assert_not_called()

    def test_owner_check_requires_real_receipt(self):
        with patch.object(runner, 'native_configuration'), patch.object(runner, 'gateway_identity', return_value=GATEWAY), \
             redirect_stderr(io.StringIO()):
            result = runner.main(['--check', '--owner-session', OWNER, '--completion-receipt', str(self.workspace / 'absent.json')])
        self.assertEqual(result, 78)

    def test_disabled_completion_and_denied_process_are_rejected(self):
        config_path = self.root / 'config.json'
        for tools in ({'exec': {'notifyOnExit': False}}, {'deny': ['process']}):
            config_path.write_text(json.dumps({'tools': tools}))
            with self.subTest(tools=tools), self.assertRaises(ValueError):
                runner.native_configuration(config_path)

    def test_isolated_heartbeat_default_or_owner_override_blocks_native_imports(self):
        config_path = self.root / 'config.json'
        configs = [{'agents': {'defaults': {'heartbeat': {'isolatedSession': True}}}},
                   {'agents': {'defaults': {'heartbeat': {'isolatedSession': False}},
                               'entries': {'main': {'heartbeat': {'isolatedSession': True}}}}}]
        for config in configs:
            config_path.write_text(json.dumps(config))
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, 'isolated routing redirects'):
                runner.native_configuration(config_path)

    def test_owner_nonisolated_override_preserves_same_conversation_continuation(self):
        config_path = self.root / 'config.json'
        config_path.write_text(json.dumps({'agents': {'defaults': {'heartbeat': {'isolatedSession': True}},
                                           'entries': {'main': {'heartbeat': {'isolatedSession': False}}}}}))
        runner.native_configuration(config_path)

    def test_none_heartbeat_default_or_owner_override_blocks_completion_details(self):
        config_path = self.root / 'config.json'
        configs = [{'agents': {'defaults': {'heartbeat': {'target': 'none'}}}},
                   {'agents': {'defaults': {'heartbeat': {'target': 'owner'}},
                               'entries': {'main': {'heartbeat': {'target': 'none'}}}}}]
        for config in configs:
            config_path.write_text(json.dumps(config))
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, 'target=none removes raw completion details'):
                runner.native_configuration(config_path)

    def test_owner_delivery_override_restores_internal_dashboard_projection(self):
        config_path = self.root / 'config.json'
        config_path.write_text(json.dumps({'agents': {'defaults': {'heartbeat': {'target': 'none'}},
                                           'entries': {'main': {'heartbeat': {'target': 'owner'}}}}}))
        runner.native_configuration(config_path)

    def terminal_fixture(self, scope, outcome='succeeded'):
        job_id = '11111111-2222-4333-8444-555555555555'
        result = {'event_id': f'ingestion:{job_id}:terminal', 'job_id': job_id,
                  'run_id': '22222222-3333-4444-8555-666666666666',
                  'execution_id': '33333333-4444-4555-8666-777777777777', 'outcome': outcome, 'exit_code': 0}
        result_path = self.map / 'lib/db-map/.ingest-jobs' / job_id / 'result.json'
        result_path.parent.mkdir(parents=True)
        result_path.write_text(json.dumps(result))
        job = {'id': job_id, 'mode': 'native', 'status': 'finished', 'argv': scope,
               'started_at': '2026-10-05T09:01:00+00:00', 'run_id': result['run_id'],
               'execution_id': result['execution_id'], 'result': result}
        result_path.with_name('job.json').write_text(json.dumps(job))
        launch = {'event': 'ingestion.started', 'job_id': job_id, 'result': str(result_path)}
        output = json.dumps(launch, indent=2) + '\n' + json.dumps(result)
        return result_path, result, job, launch, output

    def test_concatenated_watch_json_matches_canonical_durable_identity(self):
        scope = ['source.json', '--category', 'campground', '--from', 'report', *ZERO_BUDGETS]
        result_path, result, _, _, output = self.terminal_fixture(scope)
        self.assertEqual(runner.durable_terminal(output, scope, '2026-10-05T09:00:00+00:00'), (result_path, result))

    def test_terminal_rejects_noncanonical_path_scope_or_mismatched_job_ids(self):
        scope = ['source.json', '--category', 'campground', '--from', 'report', *ZERO_BUDGETS]
        result_path, result, job, launch, _ = self.terminal_fixture(scope)
        cases = [(dict(job, argv=['different.json']), launch),
                 (dict(job, execution_id='44444444-5555-4666-8777-888888888888'), launch),
                 (dict(job, status='running'), launch),
                 (dict(job, started_at='2026-10-05T08:59:59+00:00'), launch),
                 (job, dict(launch, result='/tmp/noncanonical-result.json'))]
        for candidate, receipt in cases:
            result_path.with_name('job.json').write_text(json.dumps(candidate))
            output = json.dumps(receipt) + json.dumps(result)
            with self.subTest(candidate=candidate, receipt=receipt), self.assertRaises(ValueError):
                runner.durable_terminal(output, scope, '2026-10-05T09:00:00+00:00')

    def test_banners_extra_or_malformed_watch_receipts_are_not_success(self):
        for text in ('banner\n{}{}', '{}{}{}', '[]', '{', 'x' * (runner.MAX_OUTPUT_BYTES + 1)):
            with self.subTest(text=text[:30]), self.assertRaises(ValueError):
                runner.durable_terminal(text, [], '2026-10-05T09:00:00+00:00')

    def test_foreground_watch_forwards_and_privately_captures_without_detaching(self):
        child = Mock(stdout=io.StringIO('{"started":true}\n{"terminal":true}\n'))
        child.wait.return_value = 0
        with patch.dict(os.environ, {'OPENCLAW_SUBAGENT_EXEC': '1'}), \
             patch.object(runner.subprocess, 'Popen', return_value=child) as start, \
             patch.object(runner.signal, 'signal'), redirect_stdout(io.StringIO()) as output:
            code, captured = runner.foreground_watch(['fixture-command'], self.workspace)
        self.assertEqual(code, 0)
        self.assertEqual(captured, output.getvalue())
        self.assertEqual((self.workspace / 'watch.stdout').read_text(), captured)
        self.assertEqual((self.workspace / 'watch.stdout').stat().st_mode & 0o777, 0o600)
        self.assertNotIn('start_new_session', start.call_args.kwargs)
        self.assertNotIn('shell', start.call_args.kwargs)
        self.assertEqual(start.call_args.kwargs['env']['OPENCLAW_SUBAGENT_EXEC'], '1')
        child.wait.assert_called_once_with()

    def test_targeted_generic_system_event_preserves_subagent_flag_and_never_waits_for_model(self):
        acknowledgement = {'ok': True}
        response = subprocess.CompletedProcess([], 0, json.dumps(acknowledgement), '')
        with patch.dict(os.environ, {'OPENCLAW_SUBAGENT_EXEC': '1'}), \
             patch.object(runner.subprocess, 'run', return_value=response) as send:
            receipt = runner.terminal_callback(OWNER, 'fixture-event', 'outcome=succeeded exit_code=0', self.workspace)
        self.assertEqual(receipt['status'], 'accepted')
        self.assertEqual(receipt['acknowledgement'], acknowledgement)
        self.assertEqual(receipt['notification_kind'], 'internal_system_event')
        self.assertNotIn('dispatch_id', receipt)
        args = send.call_args.args[0]
        self.assertEqual(args[:3], [runner.OPENCLAW, 'system', 'event'])
        self.assertEqual(args[args.index('--session-key') + 1], OWNER)
        self.assertEqual(args[args.index('--mode') + 1], 'now')
        self.assertEqual(send.call_args.kwargs['env']['OPENCLAW_SUBAGENT_EXEC'], '1')
        message = args[args.index('--text') + 1]
        self.assertTrue(message.startswith('INTERNAL_MAP_TERMINAL_EVENT\n'))
        self.assertIn('Sender: local run-map-import wrapper', message)
        self.assertIn('event_id=fixture-event', message)
        self.assertIn('outcome=succeeded exit_code=0', message)
        self.assertIn('Read AGENTS.md and MAP-IMPORTS.md', message)
        self.assertNotIn('--expect-final', args)
        self.assertNotIn('--params', args)
        self.assertEqual(json.loads((self.workspace / 'callback.json').read_text())['acknowledgement'], acknowledgement)

    def test_generic_payload_cannot_match_installed_structured_exec_event_classifier(self):
        # These patterns match the installed heartbeat-events-filter implementation.
        structured = re.compile(r'^exec (completed|failed) \(([a-z0-9_-]{1,64}), (code -?\d+|signal [^)]+)\)(?: :: ([\s\S]*))?$', re.IGNORECASE)
        finished = re.compile(r'^exec finished(?::|\s*\()', re.IGNORECASE)
        with patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{"ok":true}', '')) as send:
            runner.terminal_callback(OWNER, 'fixture-event', 'event=fixture-event evidence=/private/terminal.json outcome=blocked exit_code=78', self.workspace)
        args = send.call_args.args[0]
        text = args[args.index('--text') + 1]
        self.assertFalse(structured.search(text.strip()))
        self.assertFalse(finished.search(text.lstrip()))
        self.assertNotIn('Exec completed', text)
        self.assertNotIn('Exec failed', text)
        self.assertTrue(structured.search('Exec completed (fixture, code 0) :: old structured payload'))

    def test_chained_generic_events_target_same_owner_and_preserve_distinct_event_ids(self):
        captured = []
        def acknowledge(command, **_kwargs):
            captured.append(command)
            return subprocess.CompletedProcess(command, 0, '{"ok":true}', '')
        events = ['map-terminal-preflight:11111111-2222-4333-8444-555555555555',
                  'ingestion:22222222-3333-4444-8555-666666666666:terminal']
        with patch.object(runner.subprocess, 'run', side_effect=acknowledge) as send:
            for index, event in enumerate(events):
                directory = self.workspace / f'chained-{index}'
                directory.mkdir()
                receipt = runner.terminal_callback(OWNER, event, f'event={event} evidence=/private/fixture-{index}.json', directory)
                self.assertEqual(receipt['status'], 'accepted')
                self.assertEqual(receipt['event_id'], event)
        self.assertEqual(send.call_count, 2)
        for command, event in zip(captured, events):
            self.assertEqual(command[command.index('--session-key') + 1], OWNER)
            message = command[command.index('--text') + 1]
            self.assertIn(f'event_id={event}', message)
            self.assertIn('INTERNAL_MAP_TERMINAL_EVENT', message)

    def test_zero_exit_without_positive_system_ack_remains_uncertain(self):
        acknowledgements = [{}, {'runId': 'old-chat-run', 'status': 'started'},
                            {'ok': 1}, {'ok': 'true'}, {'status': 'ok'}]
        for index, acknowledgement in enumerate(acknowledgements):
            directory = self.workspace / f'callback-{index}'
            directory.mkdir()
            with self.subTest(acknowledgement=acknowledgement), \
                 patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(acknowledgement), '')) as send:
                receipt = runner.terminal_callback(OWNER, 'fixture-event', 'fixture-text', directory)
            self.assertEqual(receipt['status'], 'uncertain')
            self.assertEqual(receipt['acknowledgement'], acknowledgement)
            send.assert_called_once()

    def test_false_ack_is_explicit_failure_even_with_zero_exit(self):
        with patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '{"ok":false}', '')):
            receipt = runner.terminal_callback(OWNER, 'fixture-event', 'fixture-text', self.workspace)
        self.assertEqual(receipt['status'], 'failed')
        self.assertIn('explicitly rejected', receipt['reason'])

    def test_zero_exit_without_ack_is_uncertain_and_second_attempt_is_blocked(self):
        with patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'not-json', '')) as send:
            receipt = runner.terminal_callback(OWNER, 'fixture-event', 'fixture-text', self.workspace)
            self.assertEqual(receipt['status'], 'uncertain')
            with self.assertRaisesRegex(ValueError, 'already attempted'):
                runner.terminal_callback(OWNER, 'fixture-event', 'fixture-text', self.workspace)
        send.assert_called_once()

    def test_callback_timeout_retains_private_ambiguity_without_retry(self):
        timeout = subprocess.TimeoutExpired(['fixture-cli'], 20, output=b'partial acknowledgement')
        with patch.object(runner.subprocess, 'run', side_effect=timeout) as send:
            receipt = runner.terminal_callback(OWNER, 'fixture-event', 'fixture-text', self.workspace)
        self.assertEqual(receipt['status'], 'uncertain')
        self.assertIn('do not resend', receipt['reason'])
        self.assertEqual((self.workspace / 'callback.stdout').read_text(), 'partial acknowledgement')
        send.assert_called_once()

    def test_failed_callback_retains_actual_failure(self):
        with patch.object(runner.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '{"ok":false}', 'private failure')):
            receipt = runner.terminal_callback(OWNER, 'fixture-event', 'fixture-text', self.workspace)
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['exit_code'], 1)
        self.assertEqual((self.workspace / 'callback.stderr').read_text(), 'private failure')

    def test_production_callback_uses_exact_durable_event_and_nonzero_watch_code(self):
        scope = ['source.json', '--category', 'campground', '--from', 'report', *ZERO_BUDGETS]
        result_path, result, _, _, output = self.terminal_fixture(scope, outcome='paused')
        with patch.object(runner, 'utc_now', return_value='2026-10-05T09:00:00+00:00'), \
             patch.object(runner, 'foreground_watch', return_value=(2, output)) as watch, \
             patch.object(runner, 'terminal_callback', return_value={'status': 'accepted'}) as callback, \
             redirect_stdout(io.StringIO()):
            code = runner.run_import(['fixture-command'], scope, OWNER, GATEWAY, self.workspace)
        self.assertEqual(code, 2)
        self.assertEqual(callback.call_args.args[1], result['event_id'])
        self.assertIn(f'result={result_path}', callback.call_args.args[2])
        self.assertIn('exit_code=2', callback.call_args.args[2])
        watch.assert_called_once()
        callback.assert_called_once()

    def test_watch_startup_failure_sends_distinct_wrapper_blocker_without_fake_job(self):
        with patch.object(runner, 'foreground_watch', return_value=(78, '')) as watch, \
             patch.object(runner, 'terminal_callback', return_value={'status': 'accepted'}) as callback, \
             redirect_stdout(io.StringIO()):
            code = runner.run_import(['fixture-command'], ZERO_BUDGETS, OWNER, GATEWAY, self.workspace)
        self.assertEqual(code, 78)
        evidence = json.loads((self.workspace / 'terminal.json').read_text())
        self.assertEqual(evidence['outcome'], 'blocked')
        self.assertNotIn('job_id', evidence)
        self.assertNotIn('run_id', evidence)
        self.assertTrue(callback.call_args.args[1].startswith('map-import-wrapper:'))
        self.assertIn('exit_code=78', callback.call_args.args[2])
        watch.assert_called_once()
        callback.assert_called_once()

    def test_spawn_failure_raw_error_stays_private_callback_only_points_to_evidence(self):
        with patch.object(runner, 'foreground_watch', side_effect=OSError('private-startup-fixture')) as watch, \
             patch.object(runner, 'terminal_callback', return_value={'status': 'accepted'}) as callback, \
             redirect_stdout(io.StringIO()) as output:
            code = runner.run_import(['fixture-command'], ZERO_BUDGETS, OWNER, GATEWAY, self.workspace)
        self.assertEqual(code, 78)
        self.assertIn('private-startup-fixture', (self.workspace / 'terminal.json').read_text())
        self.assertNotIn('private-startup-fixture', callback.call_args.args[2])
        self.assertNotIn('private-startup-fixture', output.getvalue())
        watch.assert_called_once()
        callback.assert_called_once()

    def test_callback_failure_blocks_advance_even_when_map_succeeded(self):
        scope = ['source.json', '--category', 'campground', '--from', 'report', *ZERO_BUDGETS]
        _, result, _, _, output = self.terminal_fixture(scope)
        with patch.object(runner, 'utc_now', return_value='2026-10-05T09:00:00+00:00'), \
             patch.object(runner, 'foreground_watch', return_value=(0, output)), \
             patch.object(runner, 'terminal_callback', return_value={'status': 'failed'}) as callback, \
             redirect_stdout(io.StringIO()):
            code = runner.run_import(['fixture-command'], scope, OWNER, GATEWAY, self.workspace)
        self.assertEqual(code, 78)
        evidence = json.loads((self.workspace / 'terminal.json').read_text())
        self.assertTrue(evidence['notification_blocked'])
        self.assertEqual(evidence['event_id'], result['event_id'])
        callback.assert_called_once()

    def test_unlimited_terminal_with_unknown_cost_evidence_is_not_a_wrapper_blocker(self):
        scope = ['source.json', '--category', 'campground', '--unlimited']
        result_path, result, job, launch, _ = self.terminal_fixture(scope)
        result['evidence'] = {'normalization_usage': {'requests': 1, 'estimated_cost_usd': 0, 'unknown_cost_requests': 1}}
        result_path.write_text(json.dumps(result))
        result_path.with_name('job.json').write_text(json.dumps(job))
        output = json.dumps(launch) + '\n' + json.dumps(result)
        with patch.object(runner, 'utc_now', return_value='2026-10-05T09:00:00+00:00'), \
             patch.object(runner, 'foreground_watch', return_value=(0, output)), \
             patch.object(runner, 'terminal_callback', return_value={'status': 'accepted'}) as callback, \
             redirect_stdout(io.StringIO()):
            code = runner.run_import(['fixture-command'], scope, OWNER, GATEWAY, self.workspace)
        self.assertEqual(code, 0)
        evidence = json.loads((self.workspace / 'terminal.json').read_text())
        self.assertEqual(evidence['outcome'], 'succeeded')
        self.assertFalse(evidence['notification_blocked'])
        callback.assert_called_once()

    def test_preflight_waits_fixed_time_writes_evidence_and_cannot_create_proof(self):
        with patch.object(runner.time, 'sleep') as sleep, \
             patch.object(runner, 'terminal_callback', return_value={'status': 'accepted'}) as callback, \
             redirect_stdout(io.StringIO()) as output:
            code = runner.preflight(OWNER, GATEWAY, self.workspace)
        self.assertEqual(code, 0)
        sleep.assert_called_once_with(12)
        evidence = json.loads((self.workspace / 'preflight.json').read_text())
        self.assertEqual(evidence['owner_session'], OWNER)
        self.assertEqual(evidence['gateway'], GATEWAY)
        self.assertEqual(evidence['notification_kind'], 'internal_system_event')
        self.assertTrue(evidence['event_id'].startswith('map-terminal-preflight:'))
        self.assertIn(evidence['marker'], callback.call_args.args[2])
        self.assertIn('Acceptance is not automatic-continuation proof', output.getvalue())
        self.assertEqual(json.loads(self.receipt_path.read_text()), self.receipt)
        callback.assert_called_once()

    def test_preflight_does_not_use_import_credentials_or_existing_receipt(self):
        with patch.object(runner, 'native_configuration'), patch.object(runner, 'gateway_identity', return_value=GATEWAY), \
             patch.object(runner, 'validate_receipt') as receipt, patch.object(runner, 'preflight', return_value=0) as preflight, \
             patch.object(runner, 'run_import') as run_import, patch.dict(os.environ, {'OPENCLAW_SHELL': 'exec'}, clear=True):
            result = runner.main(['--preflight', '--owner-session', OWNER])
        self.assertEqual(result, 0)
        receipt.assert_not_called()
        run_import.assert_not_called()
        preflight.assert_called_once()

    def test_preflight_rejects_terminal_and_ingestion_scope_flags(self):
        for arguments in (['--preflight', '--owner-session', OWNER, '--max-hours', '1'],
                          ['--preflight', '--owner-session', OWNER, '--completion-receipt', '/tmp/proof.json'],
                          ['--preflight', '--owner-session', OWNER, '--', 'source.json']):
            with self.subTest(arguments=arguments), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                runner.parse_arguments(arguments)
        with patch.dict(os.environ, {}, clear=True), redirect_stderr(io.StringIO()), patch.object(runner, 'preflight') as preflight:
            self.assertEqual(runner.main(['--preflight', '--owner-session', OWNER]), 78)
        preflight.assert_not_called()

    def test_shell_entry_forwards_arguments_without_detaching(self):
        scripts = self.root / 'scripts'
        scripts.mkdir()
        shutil.copyfile(Path(__file__).with_name('run-map-import.sh'), scripts / 'run-map-import.sh')
        python = self.root / '.venv/bin/python'
        python.parent.mkdir(parents=True)
        python.write_text('#!/bin/sh\nexec /usr/bin/python3 -c \'import json,sys; print(json.dumps(sys.argv[1:]))\' "$@"\n')
        python.chmod(0o700)
        args = ['--owner-session', OWNER, '--max-hours', '12', '--', 'source path.json', *ZERO_BUDGETS]
        result = subprocess.run(['/bin/bash', str(scripts / 'run-map-import.sh'), *args], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [str(scripts / 'run-map-import.py'), *args])


if __name__ == '__main__':
    unittest.main()
