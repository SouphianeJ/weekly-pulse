#!/usr/bin/env python3
"""Collect what shipped in one repository over the window, deterministically.

The agent reads this JSON instead of paging through the GitHub API itself,
then spends its judgment on what is non-enumerable: describing changes for a
reader, and deciding whether the docs still tell the truth.

Uses the REST API only (GraphQL is not available from Claude Code sessions).

Usage:
    python scripts/pulse_docs.py OWNER/REPO [--days 7] [--changelog CHANGELOG.md] > shipped.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys

# Files whose presence means the changelog is already owned by a release tool.
RELEASE_TOOLS = {
    "release-please": ["release-please-config.json", ".release-please-manifest.json"],
    "changesets": [".changeset/config.json"],
    "git-cliff": ["cliff.toml"],
    "semantic-release": [".releaserc", ".releaserc.json", "release.config.js"],
}
PR_REF = re.compile(r"\(#(\d+)\)|Merge pull request #(\d+)")


def gh_api(path: str) -> tuple[int, object]:
    proc = subprocess.run(["gh", "api", "-H", "Accept: application/vnd.github+json", path],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return proc.returncode, (proc.stderr or proc.stdout).strip()[:300]
    return 0, json.loads(proc.stdout) if proc.stdout.strip() else None


def exists(repo: str, path: str) -> bool:
    return gh_api(f"/repos/{repo}/contents/{path}")[0] == 0


def is_bot(user: dict | None) -> bool:
    user = user or {}
    return user.get("type") == "Bot" or user.get("login", "").endswith("[bot]")


def merged_prs(repo: str, base: str, since: dt.datetime, branch_prefix: str, errors: list) -> list[dict]:
    out, page = [], 1
    while page <= 5:  # 500 recently-updated closed PRs is plenty for a weekly window
        code, data = gh_api(f"/repos/{repo}/pulls?state=closed&base={base}&sort=updated"
                            f"&direction=desc&per_page=100&page={page}")
        if code:
            errors.append(f"merged PRs, page {page}: {data}")
            break
        if not data:
            break
        for pr in data:
            if not pr.get("merged_at"):
                continue
            merged = dt.datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
            if merged < since:
                continue
            fcode, files = gh_api(f"/repos/{repo}/pulls/{pr['number']}/files?per_page=100")
            if fcode:
                errors.append(f"files of PR #{pr['number']}: {files}")
            out.append({
                "number": pr["number"],
                "title": pr["title"],
                "author": (pr.get("user") or {}).get("login"),
                "bot": is_bot(pr.get("user")),
                "from_weekly_pulse": pr["head"]["ref"].startswith(branch_prefix),
                "labels": [lab["name"] for lab in pr.get("labels") or []],
                "merged_at": pr["merged_at"],
                "merge_commit_sha": pr.get("merge_commit_sha"),
                "body": (pr.get("body") or "")[:2000],
                "files": [f["filename"] for f in files or []] if isinstance(files, list) else [],
                "url": pr["html_url"],
            })
        last = data[-1].get("updated_at", "")
        if last and dt.datetime.fromisoformat(last.replace("Z", "+00:00")) < since:
            break  # sorted by update time: nothing older can have merged in the window
        page += 1
    return sorted(out, key=lambda p: p["merged_at"])


def direct_commits(repo: str, base: str, since: dt.datetime, prs: list[dict], errors: list) -> list[dict]:
    code, commits = gh_api(f"/repos/{repo}/commits?sha={base}&since={since.strftime('%Y-%m-%dT%H:%M:%SZ')}&per_page=100")
    if code or not isinstance(commits, list):
        errors.append(f"commits: {commits}")
        return []
    known = {p["merge_commit_sha"] for p in prs}
    out = []
    for c in commits:
        subject = (c["commit"]["message"] or "").split("\n", 1)[0]
        if c["sha"] in known or PR_REF.search(subject):
            continue
        # Commits that came in through a merge-commit PR are not "direct".
        _, linked = gh_api(f"/repos/{repo}/commits/{c['sha']}/pulls")
        if isinstance(linked, list) and any(p.get("merged_at") for p in linked):
            continue
        out.append({"sha": c["sha"][:10], "message": subject[:200] or "(empty message)",
                    "author": (c.get("author") or {}).get("login")})
    return out


def collect(repo: str, days: int, changelog: str, branch_prefix: str) -> dict:
    code, meta = gh_api(f"/repos/{repo}")
    if code:
        return {"repo": repo, "reachable": False, "error": str(meta)}
    base = meta["default_branch"]
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    errors: list[str] = []
    prs = merged_prs(repo, base, since, branch_prefix, errors)
    week = "{}-W{:02d}".format(*dt.date.today().isocalendar()[:2])
    branch = f"{branch_prefix}{week}"
    # Any still-open pulse PR, whatever its week: it gets extended rather than duplicated.
    ocode, open_prs = gh_api(f"/repos/{repo}/pulls?state=open&base={base}&per_page=100")
    if ocode:
        errors.append(f"open PRs: {open_prs}")
    open_pulse = [p for p in open_prs or [] if isinstance(open_prs, list) and p["head"]["ref"].startswith(branch_prefix)]
    return {
        "repo": repo,
        "reachable": True,
        "iso_week": week,
        "default_branch": base,
        "window": {"since": since.isoformat(timespec="seconds"), "days": days},
        "release_tools": [name for name, paths in RELEASE_TOOLS.items() if any(exists(repo, p) for p in paths)],
        "changelog_exists": exists(repo, changelog),
        "pulse_branch": branch,
        "open_pulse_pr": ({"url": open_pulse[0]["html_url"], "number": open_pulse[0]["number"],
                           "branch": open_pulse[0]["head"]["ref"]} if open_pulse else None),
        "merged_prs": [p for p in prs if not p["from_weekly_pulse"]],
        "direct_commits": direct_commits(repo, base, since, prs, errors),
        # Non-empty = incomplete facts: never conclude "quiet week" or open a new PR on them.
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", help="OWNER/REPO")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--changelog", default="CHANGELOG.md")
    ap.add_argument("--branch-prefix", default="claude/weekly-pulse-docs-")
    args = ap.parse_args()
    json.dump(collect(args.repo, args.days, args.changelog, args.branch_prefix),
              sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
