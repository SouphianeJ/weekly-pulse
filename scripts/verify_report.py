#!/usr/bin/env python3
"""Fail-closed check of a report before the agent posts it.

The agent must run this on every issue or PR body it is about to publish.
Exit 0 = safe to post. Exit 1 = do not post; the reasons are printed.

Checks:
  1. the first line is this week's marker, so re-runs update instead of duplicating;
  2. nothing in the body looks like a secret value (token prefixes, private keys,
     credentials in URLs), whatever the agent meant to write.

Usage:
    python3 scripts/verify_report.py BODY.md --pulse security --week 2026-W42 --title "..."
    git diff --cached | python3 scripts/verify_report.py - --secrets-only   # before a docs commit
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Closed class of well-known secret shapes. Locations like `config.py:12` and rule
# names like "Secret Keyword" do not match; values do.
SECRET_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS access key id": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})\b"),
    "Slack token": re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}"),
    "OpenAI/Anthropic key": re.compile(r"\bsk-(ant-)?[A-Za-z0-9_-]{20,}"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    "Stripe key": re.compile(r"\b[rs]k_(live|test)_[0-9A-Za-z]{16,}"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "credentials in URL": re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]{3,}@"),
}


def secret_problems(text: str) -> list[str]:
    found = []
    for name, pattern in SECRET_PATTERNS.items():
        for match in pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            found.append(f"line {line_no}: looks like a {name} — report its location, never its value")
    return found


def problems(body: str, pulse: str, week: str) -> list[str]:
    found = []
    lines = body.splitlines()
    marker = f"<!-- weekly-pulse:{pulse}:{week} -->"
    if not lines or lines[0].strip() != marker:
        found.append(f"first line must be exactly {marker}")
    if len(body.strip()) < len(marker) + 20:
        found.append("body is empty apart from the marker")
    return found + secret_problems(body)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("body", help="file to check, or - for stdin")
    ap.add_argument("--pulse", choices=["security", "docs"])
    ap.add_argument("--week", help="ISO week, e.g. 2026-W42")
    ap.add_argument("--title", default="", help="issue or PR title, checked for secrets too")
    ap.add_argument("--secrets-only", action="store_true", help="skip the marker check (diffs, commits)")
    args = ap.parse_args()
    text = sys.stdin.read() if args.body == "-" else Path(args.body).read_text(encoding="utf-8")
    if args.secrets_only:
        issues = secret_problems(text)
    else:
        if not (args.pulse and args.week):
            ap.error("--pulse and --week are required unless --secrets-only")
        issues = problems(text, args.pulse, args.week)
    issues += [f"title: {i}" for i in secret_problems(args.title)]
    for issue in issues:
        print(f"REFUSED: {issue}")
    if not issues:
        print("OK")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
