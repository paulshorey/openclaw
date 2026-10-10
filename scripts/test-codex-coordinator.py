#!/usr/bin/env python3
"""Offline tests for consequential policy, isolation and Cloud recovery behavior."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
import agent_policy as ap
from cloud_tasks import Cloud, Ledger, parse_page, task_url


class PolicyTests(unittest.TestCase):
    def test_independent_coordinator_change(self):
        original = ap.load_policy()
        changed = copy.deepcopy(original)
        changed["roles"]["coordinator"]["model"] = "gpt-6-luna"
        before = ap.coordinator_patch(original, ap.load_runtime())
        after = ap.coordinator_patch(changed, ap.load_runtime())
        self.assertNotEqual(before, after)
        for name in ("local_coding", "cloud_coding"):
            self.assertEqual(original["roles"][name], changed["roles"][name])

    def test_keys_removed_after_project_env_and_home_explicit(self):
        env = ap.cli_env(ap.load_runtime(), {"CODEX_HOME": "/wrong", "HOME": "/wrong", "OPENAI_API_KEY": "test", "CODEX_API_KEY": "test", "FIREWORKS_API_KEY": "retained"})
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CODEX_API_KEY", env)
        self.assertEqual(env["FIREWORKS_API_KEY"], "retained")
        self.assertEqual(env["CODEX_HOME"], ap.load_runtime()["cli_home"])

    def test_subscription_policy_rejects_api_fallback_and_unknown_fields(self):
        for mutation in (lambda p: p["roles"]["coordinator"].update(allow_api_fallback=True),
                         lambda p: p["roles"]["local_coding"].update(unknown=True)):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp); (root / "config").mkdir()
                p = ap.load_policy(); mutation(p)
                (root / "config/agent-models.json").write_text(json.dumps(p))
                with self.assertRaises(ap.PolicyError): ap.load_policy(root)

    def test_patch_preserves_unrelated_access_and_credentials(self):
        original = {"gateway": {"auth": {"token": "fixture"}, "tailscale": {"mode": "serve"}}, "plugins": {"entries": {"fireworks": {"enabled": True}}}, "unrelated": True}
        result = ap.merge_patch(original, ap.coordinator_patch(ap.load_policy(), ap.load_runtime()))
        self.assertEqual(result["gateway"]["auth"], original["gateway"]["auth"])
        self.assertEqual(result["gateway"]["tailscale"], original["gateway"]["tailscale"])
        self.assertFalse(result["plugins"]["entries"]["fireworks"]["enabled"])
        self.assertEqual(result["auth"]["order"]["openai"], [ap.load_runtime()["coordinator_auth_profile"]])
        self.assertEqual(result["agents"]["entries"]["main"]["model"]["fallbacks"], [])
        self.assertNotIn("cwd", result["agents"]["entries"]["main"])

    def test_wrong_auth_rejected_without_printing_key(self):
        replies = [subprocess.CompletedProcess([], 0, "codex-cli 0.160.0\n", ""), subprocess.CompletedProcess([], 0, "", "Logged in using an API key: fixture-secret")]
        with patch("agent_policy.os.access", return_value=True), patch("agent_policy.subprocess.run", side_effect=replies):
            with self.assertRaises(ap.PolicyError) as error: ap.require_cli(ap.load_runtime())
            self.assertNotIn("fixture-secret", str(error.exception))

    def test_custom_home_inference_route_is_rejected_before_cli_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = ap.load_runtime(); runtime["cli_home"] = temp
            Path(temp, "config.toml").write_text('[model_providers.openai]\nbase_url="https://fixture.invalid"\n')
            with patch("agent_policy.os.access", return_value=True), patch("agent_policy.subprocess.run") as run:
                with self.assertRaises(ap.PolicyError): ap.require_cli(runtime)
                run.assert_not_called()

    def test_project_chatgpt_route_is_rejected_before_cli_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp); (directory / ".codex").mkdir()
            (directory / ".codex/config.toml").write_text('chatgpt_base_url="https://fixture.invalid"\n')
            runtime = ap.load_runtime(); runtime["cli_home"] = str(directory / "home")
            with patch("agent_policy.os.access", return_value=True), patch("agent_policy.git", return_value=temp), patch("agent_policy.subprocess.run") as run:
                with self.assertRaises(ap.PolicyError): ap.require_cli(runtime, cwd=directory)
                run.assert_not_called()


class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.repo = self.root / "primary"; self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        self.run_git("config", "user.name", "Test")
        self.run_git("config", "user.email", "test@example.invalid")
        self.run_git("remote", "add", "origin", "git@github.com:paulshorey/map.git")
        (self.repo / "file").write_text("base")
        self.run_git("add", "."); self.run_git("commit", "-qm", "base")
        self.base = self.run_git("rev-parse", "HEAD").stdout.strip()
        self.worktree = self.root / "worktree"
        self.run_git("worktree", "add", "-qb", "codex/test", str(self.worktree), self.base)
        (self.root / "config").mkdir()
        (self.root / "config/managed-repositories.tsv").write_text(f"paulshorey/map\t{self.repo}\n")
    def run_git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True)
    def tearDown(self): self.temp.cleanup()
    def test_dirty_primary_preserved_and_linked_worktree_accepted(self):
        (self.repo / "file").write_text("user changes")
        self.assertEqual(ap.verified_worktree("paulshorey/map", self.worktree, self.base, self.root), self.worktree.resolve())
        self.assertEqual((self.repo / "file").read_text(), "user changes")
    def test_primary_dirty_worktree_and_wrong_base_rejected(self):
        with self.assertRaises(ap.PolicyError): ap.verified_worktree("paulshorey/map", self.repo, self.base, self.root)
        (self.worktree / "file").write_text("dirty")
        with self.assertRaises(ap.PolicyError): ap.verified_worktree("paulshorey/map", self.worktree, self.base, self.root)
        with self.assertRaises(ap.PolicyError): ap.verified_worktree("paulshorey/map", self.worktree, "0" * 40, self.root)
    def test_unrelated_clone_rejected(self):
        clone = self.root / "clone"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(clone)], check=True)
        subprocess.run(["git", "-C", str(clone), "remote", "set-url", "origin", "git@github.com:paulshorey/map.git"], check=True)
        with self.assertRaises(ap.PolicyError): ap.verified_worktree("paulshorey/map", clone, self.base, self.root)


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.path = Path(self.temp.name) / "tasks.sqlite3"
        self.ledger = Ledger(self.path)
        self.cloud = Cloud(ap.load_policy(), ap.load_runtime())
        self.data = {"repository": "paulshorey/map", "scope": "issue:1:base", "owner": "owner-a", "environment_id": "env1", "policy": ap.load_policy()["roles"]["cloud_coding"]}
        self.task = self.ledger.prepare(self.data)
    def tearDown(self): self.ledger.close(); self.temp.cleanup()
    def observation(self, status="pending", updated="2026-10-08T10:00:00Z"):
        return {"id": "task_1", "url": "https://chatgpt.com/codex/tasks/task_1", "status": status, "updated_at": updated, "environment_id": "env1"}
    def test_url_rejects_untrusted_host_and_mismatched_id(self):
        for url in ("https://chatgpt.com.evil.invalid/codex/tasks/task_1", "https://chatgpt.com@evil.invalid/codex/tasks/task_1", "http://chatgpt.com/codex/tasks/task_1"):
            with self.assertRaises(ap.PolicyError): task_url(url)
        task = self.observation(); task["id"] = "other"
        with self.assertRaises(ap.PolicyError): parse_page(json.dumps({"tasks": [task], "cursor": None}))
    def test_empty_unknown_and_malformed_pages(self):
        self.assertEqual(parse_page('{"tasks":[],"cursor":null}')["tasks"], [])
        for text in ("bad", "{}", '{"tasks":{},"cursor":null}'):
            with self.assertRaises(ap.PolicyError): parse_page(text)
        unknown = self.observation("new_status")
        self.assertEqual(parse_page(json.dumps({"tasks": [unknown], "cursor": None}))["tasks"][0]["status"], "new_status")
    def test_duplicate_claim_and_restart_cannot_resubmit(self):
        with self.assertRaises(ap.PolicyError): self.ledger.prepare(self.data)
        self.ledger.claim(self.task["id"], "owner-a")
        other = Ledger(self.path)
        try:
            with self.assertRaises(ap.PolicyError): other.claim(self.task["id"], "owner-a")
            other.update(self.task["id"], "submission_unknown")
            with self.assertRaises(ap.PolicyError): other.claim(self.task["id"], "owner-a")
        finally: other.close()
    def test_wrong_owner_and_expired_lease_are_not_permission_to_retry(self):
        with self.assertRaises(ap.PolicyError): self.ledger.claim(self.task["id"], "owner-b")
        self.ledger.claim(self.task["id"], "owner-a", seconds=-1)
        with self.assertRaises(ap.PolicyError): self.ledger.claim(self.task["id"], "owner-a")
    def test_user_follow_up_reopens_verification_and_stale_data_ignored(self):
        self.ledger.observe(self.task["id"], self.observation("ready"))
        self.ledger.update(self.task["id"], "verified")
        self.assertFalse(self.ledger.observe(self.task["id"], self.observation("ready"))["changed"])
        self.assertEqual(self.ledger.get(self.task["id"])["state"], "verified")
        self.ledger.observe(self.task["id"], self.observation("pending", "2026-10-08T11:00:00Z"))
        self.assertEqual(self.ledger.get(self.task["id"])["state"], "running")
        self.assertTrue(self.ledger.observe(self.task["id"], self.observation("ready"))["stale"])
    def test_unknown_status_never_completes(self):
        self.ledger.observe(self.task["id"], self.observation("unexpected"))
        self.assertEqual(self.ledger.get(self.task["id"])["state"], "remote_unknown")
    def test_paginated_and_bounded_search(self):
        replies = [subprocess.CompletedProcess([], 0, json.dumps({"tasks": [self.observation()], "cursor": "next"})), subprocess.CompletedProcess([], 0, '{"tasks":[],"cursor":null}')]
        with patch.object(self.cloud, "call", side_effect=replies) as call:
            page = self.cloud.pages(max_pages=2)
            self.assertTrue(page["complete"])
            self.assertIn("next", call.call_args_list[1].args[0])
        with patch.object(self.cloud, "call", return_value=replies[0]):
            self.assertFalse(self.cloud.pages(max_pages=1)["complete"])
            with self.assertRaises(ap.PolicyError): self.cloud.pages(max_pages=3)
    def test_missing_task_is_not_failed_and_submission_lease_becomes_unknown(self):
        self.ledger.claim(self.task["id"], "owner-a", seconds=-1)
        with patch("cloud_tasks.require_cli"), patch.object(self.cloud, "pages", return_value={"tasks": [], "complete": True, "cursor": None}):
            self.cloud.reconcile(self.ledger)
        self.assertEqual(self.ledger.get(self.task["id"])["state"], "submission_unknown")
    def test_disabled_environment_rejects_before_any_remote_write(self):
        with patch.object(self.cloud, "call") as call:
            with self.assertRaises(ap.PolicyError): self.cloud.submit(self.ledger, self.task["id"], "owner-a")
            call.assert_not_called()
        self.assertEqual(self.ledger.get(self.task["id"])["state"], "prepared")
    def test_lost_response_preserves_ambiguity_and_prompt_off_argv(self):
        private = Path(self.temp.name) / "prompt"; private.write_text("private test prompt")
        self.ledger.update(self.task["id"], prompt_path=str(private), prompt_digest=ap.fingerprint(private.read_text()), base_branch="main", expected_sha="a" * 40, authority="test", acceptance="test")
        with patch.object(self.cloud, "mapping", return_value={"environment_id": "env1", "base_branch": "main"}), patch("cloud_tasks.require_cli"), patch.object(self.cloud, "call", side_effect=subprocess.TimeoutExpired([], 90)) as call:
            with self.assertRaises(ap.PolicyError): self.cloud.submit(self.ledger, self.task["id"], "owner-a")
            self.assertEqual(call.call_args.args[0][-1], "-")
            self.assertNotIn("private test prompt", call.call_args.args[0])
        self.assertEqual(self.ledger.get(self.task["id"])["state"], "submission_unknown")
    def test_private_ledger_permissions(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
    def test_ready_flags_do_not_bypass_unsupported_remote_model_control(self):
        self.cloud.registry["paulshorey/map"].update(enabled=True, readiness="ready", environment_id="env1", model_control="verified_remote_setting", tested_cli_version="0.160.0", verified_at="today", pilot_evidence="fixture")
        self.cloud.policy["roles"]["cloud_coding"]["model_control"] = "verified_remote_setting"
        with self.assertRaisesRegex(ap.PolicyError, "cannot enforce"):
            self.cloud.mapping("paulshorey/map", submit=True)
    def test_binding_requires_exact_human_identity_evidence(self):
        self.ledger.update(self.task["id"], "submission_unknown", prompt_digest="digest")
        evidence = Path(self.temp.name) / "evidence.json"
        data = {"local_id": self.task["id"], "repository": "paulshorey/map", "environment_id": "env1", "prompt_digest": "digest", "remote_url": "https://chatgpt.com/codex/tasks/task_1", "source": "human_ui_review", "reviewed_at": "2026-10-08"}
        evidence.write_text(json.dumps(data))
        with patch("cloud_tasks.require_cli"), patch.object(self.cloud, "pages", return_value={"tasks": [self.observation()]}):
            task = self.cloud.bind(self.ledger, self.task["id"], evidence)
        self.assertEqual(task["remote_id"], "task_1")
        with self.assertRaises(ap.PolicyError): self.cloud.bind(self.ledger, self.task["id"], evidence)
    def test_timestamps_compare_instants_across_timezone_offsets(self):
        self.ledger.observe(self.task["id"], self.observation("pending", "2026-10-08T10:00:00Z"))
        update = self.ledger.observe(self.task["id"], self.observation("ready", "2026-10-08T04:30:00-05:00"))
        self.assertTrue(update["stale"])


class DeployTests(unittest.TestCase):
    def test_ui_prompt_update_reaches_main_despite_existing_override(self):
        spec = importlib.util.spec_from_file_location("ui_workflow", ap.ROOT / "scripts/configure-ui-workflow.py")
        ui = importlib.util.module_from_spec(spec); spec.loader.exec_module(ui)
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            original = {"agents": {"entries": {"main": {"heartbeat": {"prompt": "old"}, "model": "fixture-model"}}}, "gateway": {"auth": {"token": "fixture"}}}
            (state / "openclaw.json").write_text(json.dumps(original))
            with patch.object(ui, "STATE", state), patch("sys.argv", ["ui", "--dry-run"]), patch.object(ui.subprocess, "run") as run:
                ui.main()
                exported = json.loads(run.call_args.kwargs["input"])
            effective = ap.merge_patch(original, exported)
            self.assertEqual(effective["agents"]["entries"]["main"]["heartbeat"]["prompt"], exported["agents"]["defaults"]["heartbeat"]["prompt"])
            self.assertNotEqual(effective["agents"]["entries"]["main"]["heartbeat"]["prompt"], "old")
            self.assertEqual(effective["agents"]["entries"]["main"]["model"], "fixture-model")
            self.assertEqual(effective["gateway"], original["gateway"])

    def test_heartbeat_receipt_rejects_partial_identity_and_preserves_exact_launch(self):
        spec = importlib.util.spec_from_file_location("heartbeat_receipt", ap.ROOT / "scripts/heartbeat-receipt.py")
        receipt = importlib.util.module_from_spec(spec); spec.loader.exec_module(receipt)
        with tempfile.TemporaryDirectory() as temp:
            child = "agent:main:dashboard:fixture"; run = "12345678-1234-4234-8234-123456789abc"
            with self.assertRaises(ap.PolicyError): receipt.record(temp, "", run)
            with self.assertRaises(ap.PolicyError): receipt.record(temp, child, "")
            path = receipt.record(temp, child, run)
            self.assertEqual(json.loads(path.read_text())["childSessionKey"], child)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            original = path.read_bytes()
            self.assertEqual(receipt.record(temp, child, run), path)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ap.PolicyError): receipt.record(temp, child + "-other", run)

    def test_conflict_preserves_private_state_and_check_writes_nothing(self):
        spec = importlib.util.spec_from_file_location("deploy", ap.ROOT / "scripts/deploy-workspace.py")
        deploy = importlib.util.module_from_spec(spec); spec.loader.exec_module(deploy)
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "runtime"; dest.mkdir()
            (dest / "AGENTS.md").write_text("operator changed")
            (dest / "state").mkdir(); (dest / "state/keep").write_text("keep")
            with patch.object(deploy, "DEST", dest), patch.object(deploy, "MANIFEST", dest / ".deployed-files.json"), patch("sys.argv", ["deploy", "--check"]):
                self.assertEqual(deploy.main(), 1)
            self.assertEqual((dest / "state/keep").read_text(), "keep")
            self.assertFalse((dest / "CODEX-CLOUD.md").exists())


if __name__ == "__main__": unittest.main()
