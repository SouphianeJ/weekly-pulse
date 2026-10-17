"""Tests for the deterministic parts. Run: python -m unittest discover tests"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pulse_docs  # noqa: E402
import pulse_security  # noqa: E402
from verify_report import problems, secret_problems  # noqa: E402

WEEK = "2026-W42"
MARKER = f"<!-- weekly-pulse:security:{WEEK} -->"
# Fake values, assembled at runtime so this file itself never contains a secret shape.
FAKE_GH = "ghp_" + "a1B2" * 9
FAKE_AWS = "AKIA" + "ABCDEFGHIJKLMNOP"


class VerifyReport(unittest.TestCase):
    def ok_body(self, extra=""):
        return f"{MARKER}\n## Security pulse\nStatus: all clear, nothing to report.\n{extra}"

    def test_clean_report_passes(self):
        self.assertEqual(problems(self.ok_body("`config.py:12` Secret Keyword"), "security", WEEK), [])

    def test_missing_or_wrong_marker_is_refused(self):
        self.assertTrue(problems("## no marker\nsome text long enough here", "security", WEEK))
        body = self.ok_body().replace(WEEK, "2026-W41")
        self.assertTrue(problems(body, "security", WEEK))

    def test_secret_values_are_refused(self):
        fake_url = "https://admin:" + "hunter22" + "@db.example.com"
        fake_key = "-----BEGIN RSA " + "PRIVATE KEY-----"
        for value in (FAKE_GH, FAKE_AWS, fake_url, fake_key):
            with self.subTest(value=value[:8]):
                self.assertTrue(problems(self.ok_body(value), "security", WEEK))

    def test_secrets_only_mode_ignores_marker(self):
        self.assertEqual(secret_problems("+ new docs line, no marker"), [])
        self.assertTrue(secret_problems("+ token = " + FAKE_GH))

    def test_empty_body_is_refused(self):
        self.assertTrue(problems(MARKER, "security", WEEK))


class SecurityCollector(unittest.TestCase):
    def test_severity_mapping(self):
        self.assertEqual(pulse_security.norm_severity("moderate"), "medium")
        self.assertEqual(pulse_security.norm_severity("CRITICAL"), "critical")
        self.assertEqual(pulse_security.norm_severity(None), "low")

    def test_broken_check_is_reported_not_raised(self):
        def boom():
            raise ValueError("tool crashed")
        result = pulse_security.check("x", boom)
        self.assertEqual(result["status"], "error")
        self.assertIn("tool crashed", result["note"])

    def test_secret_scanning_never_keeps_the_value(self):
        alert = {"secret_type": "github_personal_access_token", "secret": FAKE_GH,  # pragma: allowlist secret
                 "secret_type_display_name": "GitHub PAT", "html_url": "https://x"}  # pragma: allowlist secret
        with mock.patch.object(pulse_security, "gh_api", return_value=(0, [alert])):
            _, findings, _ = pulse_security.secret_scanning_alerts("o/r")
        self.assertNotIn(FAKE_GH, json.dumps(findings))


class SettingsCheck(unittest.TestCase):
    def test_unreadable_setting_is_partial_not_ok(self):
        def fake(path, paginate=False):
            if "rules/branches" in path:
                return 0, []
            return 1, "Resource not accessible by integration (HTTP 403)"
        with mock.patch.object(pulse_security, "gh_api", side_effect=fake):
            status, findings, note = pulse_security.repo_settings("o/r", {"default_branch": "main"})
        self.assertEqual(status, "partial")
        self.assertEqual(findings, [])  # a 403 is not evidence that a feature is off
        self.assertIn("unreadable", note)

    def test_ruleset_counts_as_protection(self):
        def fake(path, paginate=False):
            if path.endswith("/protection"):
                return 1, "Branch not protected (HTTP 404)"
            if "rules/branches" in path:
                return 0, [{"type": "pull_request"}]
            return 0, {}
        with mock.patch.object(pulse_security, "gh_api", side_effect=fake):
            _, findings, _ = pulse_security.repo_settings("o/r", {"default_branch": "main"})
        self.assertNotIn("unprotected-default-branch", [f["rule"] for f in findings])


class DocsCollector(unittest.TestCase):
    def test_api_failure_is_reported_not_a_quiet_week(self):
        def fake(path):
            if path == "/repos/o/r":
                return 0, {"default_branch": "main"}
            return 1, "HTTP 502"
        with mock.patch.object(pulse_docs, "gh_api", side_effect=fake):
            out = pulse_docs.collect("o/r", 7, "CHANGELOG.md", "claude/weekly-pulse-docs-")
        self.assertTrue(out["errors"])

    def test_bot_detection(self):
        self.assertTrue(pulse_docs.is_bot({"login": "dependabot[bot]", "type": "Bot"}))
        self.assertFalse(pulse_docs.is_bot({"login": "alice", "type": "User"}))

    def test_pr_reference_in_commit_subject(self):
        self.assertTrue(pulse_docs.PR_REF.search("Add export (#123)"))
        self.assertTrue(pulse_docs.PR_REF.search("Merge pull request #7 from a/b"))
        self.assertFalse(pulse_docs.PR_REF.search("fix typo in README"))


if __name__ == "__main__":
    unittest.main()
