#!/usr/bin/env python3
"""Offline lifecycle tests; no desktop mutation, network or provider calls."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
import native_coordinator as n
import map_ingestion as m


def ident(): return str(uuid4())


class NativeLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'map'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Diagnostic')
        self.git('config', 'user.email', 'diagnostic@example.invalid')
        self.git('remote', 'add', 'origin', 'https://github.com/paulshorey/map.git')
        (self.repo / 'source.txt').write_text('baseline\n')
        self.git('add', '.')
        self.git('commit', '-m', 'baseline')
        self.base = self.git('rev-parse', 'HEAD')
        (self.root / 'config/coordinators').mkdir(parents=True)
        (self.root / 'config/coordinators/map.md').write_text('map rules')
        (self.root / 'config/projects.json').write_text(json.dumps({'schema_version':1,'projects':{'map':{
            'path':str(self.repo),'repository':'paulshorey/map','responsibilities':'config/coordinators/map.md',
            'schedule':'FREQ=DAILY;BYHOUR=0;BYMINUTE=0'}}}))
        self.settings={'schema_version':2,'roles':{name:{'runtime':'codex_desktop','model':'gpt-6.1-sol',
            'reasoning_effort':'high','speed':'standard','authentication':'chatgpt','allow_api_fallback':False}
            for name in ('coordinator','coding')}}
        self.save_settings()
        self.paths = patch.multiple(n, ROOT=self.root, RUNTIME=self.root / 'runtime/native')
        self.paths.start()
        n.bind_project('map','local-test-project')
        self.creator, self.child, self.observer = ident(), ident(), ident()
        n.pilot('map','claim',self.creator)
        n.pilot('map','attach',child_id=self.child)
        n.pilot('map','verify',self.observer,self.child,'native history fixture')
        self.owner = ident()
        self.pass_id = n.begin('map',self.owner)['pass']['id']
        self.prompt = n.state('map') / 'request.txt'
        self.prompt.write_text('Implement the scoped request')

    def tearDown(self):
        self.paths.stop()
        self.tmp.cleanup()

    def git(self,*args):
        return subprocess.run(['git','-C',str(self.repo),*args],check=True,capture_output=True,text=True).stdout.strip()

    def save_settings(self):
        (self.root / 'config/agent-models.json').write_text(json.dumps(self.settings))

    def prepared(self,scope='repair'):
        return n.prepare_task('map',scope,self.base,str(self.prompt),'human request','affected checks')['task']['id']

    def admitted(self):
        task=self.prepared()
        n.claim_task('map',task,self.pass_id)
        return task

    def test_concurrent_passes_never_reclaim_on_age(self):
        n.end('map',self.pass_id,'done')
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results=list(pool.map(lambda _:n.begin('map',ident()),range(4)))
        self.assertEqual(sum(r['status']=='claimed' for r in results),1)
        self.assertEqual(sum(r['status']=='blocked' for r in results),3)
        self.assertEqual(n.begin('map',ident())['status'],'blocked')

    def test_duplicate_scope_and_ambiguous_dispatch(self):
        task=self.admitted()
        self.assertEqual(self.prepared(),task)
        with self.assertRaises(ValueError): n.claim_task('map',task,self.pass_id)
        self.assertEqual(n.task('map',task)['state'],'dispatching')
        self.assertEqual(Path(n.task('map',task)['prompt_path']).stat().st_mode & 0o777,0o600)

    def test_project_pilot_requires_independent_observer(self):
        with self.assertRaises(ValueError): n.pilot('map','verify',self.creator,self.child,'own witness')
        with self.assertRaises(ValueError): n.pilot('map','verify',ident(),ident(),'wrong child')
        (n.state('map') / 'pilot/result.json').unlink()
        with self.assertRaises(ValueError): n.claim_task('map',self.prepared(),self.pass_id)

    def test_coordinator_change_does_not_change_coding(self):
        self.settings['roles']['coordinator']['model']='gpt-6-astra'
        self.settings['roles']['coordinator']['reasoning_effort']='medium'
        self.save_settings()
        task=self.admitted()
        self.assertEqual(n.schedule_plan('map')['model'],'gpt-6-astra')
        self.assertEqual(n.dispatch_plan('map',task)['model'],'gpt-6.1-sol')
        self.assertEqual(n.dispatch_plan('map',task)['thinking'],'high')
        self.assertNotIn('startingState',n.dispatch_plan('map',task)['target']['environment'])

    def test_follow_up_grant_does_not_authorize_another_project(self):
        statement = 'Human fixture: map coordinator may follow up within its own approved coding tasks.'
        n.private_json(self.root / 'config/follow-up-authorization.json', {
            'schema_version': 1, 'granted_by': 'Human fixture', 'granted_on': '2026-10-11',
            'source_thread': ident(), 'projects': ['map'], 'statement': statement})
        self.assertIn(statement, n.prompt('map'))
        self.assertEqual(n.follow_up_authorization('another-project'), '')
        (self.root / 'config/follow-up-authorization.json').unlink()
        self.assertEqual(n.follow_up_authorization('map'), '')

    def test_worktree_must_be_clean_correct_base_and_linked(self):
        task=self.admitted()
        thread=ident()
        with self.assertRaises(ValueError): n.start_task('map',task,self.repo,thread)
        self.assertEqual(n.task('map',task)['thread_id'],thread)
        self.assertEqual(n.task('map',task)['admission'],'blocked')
        worktree=self.root / 'coding'
        self.git('worktree','add','--detach',str(worktree),self.base)
        (worktree/'untracked.txt').write_text('human change')
        with self.assertRaises(ValueError): n.start_task('map',task,worktree,thread)
        (worktree/'untracked.txt').unlink()
        subprocess.run(['git','-C',str(worktree),'commit','--allow-empty','-m','different base'],check=True,capture_output=True)
        with self.assertRaises(ValueError): n.start_task('map',task,worktree,thread)
        subprocess.run(['git','-C',str(worktree),'checkout','--detach',self.base],check=True,capture_output=True)
        result=n.start_task('map',task,worktree,thread)
        self.assertEqual(result['admission'],'verified')
        self.assertEqual(n.task('map',task)['admission'],'verified')
        with self.assertRaises(ValueError): n.attach_task('map',task,ident(),'local')
        self.assertEqual(n.attach_task('map',task,thread,'local')['task']['cwd'],str(worktree.resolve()))

    def test_attach_race_only_one_thread_wins(self):
        task=self.admitted()
        def attach(_):
            try: n.attach_task('map',task,ident(),'local'); return True
            except ValueError: return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertEqual(sum(pool.map(attach,range(2))),1)

    def test_schedule_drift_and_notification_preservation(self):
        home=self.root/'codex-home'
        path=home/'automations/test-schedule/automation.toml'
        path.parent.mkdir(parents=True)
        path.write_text('status="ACTIVE"\nnotification_policy="failed_runs_only"\nmodel="wrong"\n')
        n.schedule_binding('map','test-schedule')
        with patch.dict(os.environ,{'CODEX_HOME':str(home)}):
            plan=n.schedule_plan('map')
            self.assertEqual(plan['status'],'ACTIVE')
            self.assertEqual(plan['notificationPolicy'],'failed_runs_only')
            self.assertIn('model',n.schedule_audit('map')['drift'])

    def test_wrong_origin_and_api_fallback_rejected(self):
        self.git('remote','set-url','origin','https://github.com/other/map.git')
        with self.assertRaises(ValueError): self.prepared()
        self.settings['roles']['coding']['allow_api_fallback']=True
        self.save_settings()
        with self.assertRaises(ValueError): n.role('coding')

    def test_map_resume_uncapped_and_scope_preserved(self):
        run=ident()
        self.assertEqual(m.run_arguments(['--resume',run]),['--resume',run,'--unlimited'])
        for args in (['--resume',run,'--from','report'], ['--resume',run,'--max-cost-usd','1'],
                     ['--resume',run,'--resume',run], ['--resume',run,'--unknown','x']):
            with self.assertRaises(ValueError): m.run_arguments(args)

    def test_map_ambiguous_submission_keeps_claim(self):
        n.private_json(n.state('map')/'ingestion-acceptance.json',{'status':'verified'})
        empty={'control':{'quiescent':True,'maintenance':{'maintenance':False}},'jobs':[]}
        with patch.object(m,'snapshot',return_value=empty), patch.object(m,'command',side_effect=ValueError('lost receipt')):
            with self.assertRaises(ValueError): m.start(self.owner,['--resume',ident()])
            lease=n.state('map')/'imports/active.claim'
            self.assertTrue(lease.exists())
            row=n.read_json(lease.parent/lease.read_text().strip()/'intent.json')
            self.assertEqual(row['status'],'dispatching')
            with self.assertRaises(FileExistsError): m.start(ident(),['--resume',ident()])

    def test_map_busy_precheck_releases_without_submission(self):
        n.private_json(n.state('map')/'ingestion-acceptance.json',{'status':'verified'})
        busy={'control':{'quiescent':False,'maintenance':{'maintenance':False}},'jobs':[]}
        with patch.object(m,'snapshot',return_value=busy), patch.object(m,'command') as launch:
            with self.assertRaises(ValueError): m.start(self.owner,['--resume',ident()])
            launch.assert_not_called()
            self.assertFalse((n.state('map')/'imports/active.claim').exists())

    def test_map_discovery_two_distinct_passes(self):
        job,run,execution=ident(),ident(),ident()
        current={'control':{'workers':[{'run_id':run,'execution_id':execution}]},
                 'jobs':[{'id':job,'status':'running','run_id':run,'execution_id':execution}]}
        with patch.object(m,'snapshot',return_value=current):
            self.assertEqual(m.accept(self.owner,job)['status'],'observed_once')
            self.assertEqual(m.accept(self.owner,job)['status'],'observed_once')
            self.assertEqual(m.accept(ident(),job)['status'],'verified')

    def test_map_stop_accepts_text_ack_without_claiming_exit(self):
        job=ident()
        reply=subprocess.CompletedProcess([],0,'Stop requested. This is not proof of exit.\n','')
        with patch.object(m.subprocess,'run',return_value=reply) as launch:
            result=m.command(['ingest:supervise','stop','--job',job])
            self.assertEqual(result['status'],'stop_requested')
            self.assertEqual(result['job_id'],job)
            self.assertIn('--shell-only',launch.call_args.args[0])

    def test_map_release_requires_exact_result_and_quiescence(self):
        intent,job=ident(),ident()
        directory=n.state('map')/'imports'
        n.private_json(directory/intent/'intent.json',{'id':intent,'job_id':job,'status':'started'})
        (directory/'active.claim').write_text(intent+'\n')
        current={'control':{'quiescent':True},'jobs':[{'id':job,'status':'running'}]}
        with patch.object(m,'snapshot',return_value=current):
            with self.assertRaises(ValueError): m.release(intent,'verified')
            current['jobs'][0]['status']='finished'
            with self.assertRaises(ValueError): m.release(intent,'verified')
            current['jobs'][0]['result_path']='private result'
            current['control']['quiescent']=False
            with self.assertRaises(ValueError): m.release(intent,'verified')
            current['control']['quiescent']=True
            self.assertEqual(m.release(intent,'actual terminal evidence')['status'],'reconciled')
            self.assertFalse((directory/'active.claim').exists())


if __name__ == '__main__':
    os.umask(0o077)
    unittest.main(verbosity=2)
