#!/usr/bin/env python3
"""Collect the security facts of one repository, deterministically.

The agent never runs scanners itself: it runs this script, reads the JSON,
and spends its judgment on triage. Every check reports a status
(ok / skipped / unavailable / error) so a missing tool is never mistaken
for a clean result.

Secret values are never written: GitHub secret-scanning alerts are reduced
to type + location, and detect-secrets only yields hashes, which we drop too.

Usage:
    python scripts/pulse_security.py OWNER/REPO [--clone DIR] [--days 7] > facts.json

Needs: gh (authenticated). Optional, used when installed: detect-secrets,
zizmor, pip-audit, npm.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path

SEVERITIES = ("critical", "high", "medium", "low")


def gh_api(path: str, paginate: bool = False) -> tuple[int, object]:
    """Call the GitHub API. Returns (status, payload); status 0 means OK."""
    cmd = ["gh", "api", "-H", "Accept: application/vnd.github+json", path]
    if paginate:
        cmd.insert(2, "--paginate")
        cmd += ["--jq", ".[]"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return proc.returncode, (proc.stderr or proc.stdout).strip()[:300]
    out = proc.stdout.strip()
    if not out:
        return 0, None
    if paginate:
        return 0, [json.loads(line) for line in out.splitlines() if line.strip()]
    return 0, json.loads(out)


def norm_severity(value: str | None) -> str:
    value = (value or "").lower()
    if value in ("critical",):
        return "critical"
    if value in ("high", "error"):
        return "high"
    if value in ("medium", "moderate", "warning"):
        return "medium"
    return "low"


def check(name: str, fn):
    """Run one check; never let it crash the whole collection."""
    try:
        status, findings, note = fn()
    except Exception as exc:  # a broken check is reported, not hidden
        status, findings, note = "error", [], f"{type(exc).__name__}: {exc}"[:300]
    return {"check": name, "status": status, "note": note, "findings": findings}


# --- GitHub-native alerts -------------------------------------------------

def dependabot_alerts(repo: str):
    code, data = gh_api(f"/repos/{repo}/dependabot/alerts?state=open&per_page=100", paginate=True)
    if code:
        return "unavailable", [], str(data)
    return "ok", [
        {
            "severity": norm_severity(a["security_advisory"]["severity"]),
            "location": a["dependency"].get("manifest_path", ""),
            "rule": a["security_advisory"].get("ghsa_id", ""),
            "summary": f'{a["dependency"]["package"]["name"]}: {a["security_advisory"]["summary"]}',
            "fix": "upgrade to " + ((a.get("security_vulnerability") or {}).get("first_patched_version") or {}).get("identifier", "a patched version"),
            "url": a.get("html_url", ""),
        }
        for a in data or []
    ], ""


def secret_scanning_alerts(repo: str):
    code, data = gh_api(f"/repos/{repo}/secret-scanning/alerts?state=open&per_page=100", paginate=True)
    if code:
        return "unavailable", [], str(data)
    # Deliberately keep only the type: the API payload carries the secret itself.
    return "ok", [
        {
            "severity": "critical",
            "location": "see alert",
            "rule": a.get("secret_type", ""),
            "summary": f'{a.get("secret_type_display_name", "secret")} detected by GitHub secret scanning',
            "fix": "rotate the secret, then close the alert",
            "url": a.get("html_url", ""),
        }
        for a in data or []
    ], ""


def code_scanning_alerts(repo: str):
    code, data = gh_api(f"/repos/{repo}/code-scanning/alerts?state=open&per_page=100", paginate=True)
    if code:
        return "unavailable", [], str(data)
    out = []
    for a in data or []:
        rule = a.get("rule") or {}
        loc = ((a.get("most_recent_instance") or {}).get("location") or {})
        out.append({
            "severity": norm_severity(rule.get("security_severity_level") or rule.get("severity")),
            "location": f'{loc.get("path", "")}:{loc.get("start_line", "")}',
            "rule": rule.get("id", ""),
            "summary": rule.get("description", ""),
            "fix": "",
            "url": a.get("html_url", ""),
        })
    return "ok", out, ""


def repo_settings(repo: str, meta: dict):
    findings = []
    notes = []
    code, data = gh_api(f"/repos/{repo}/vulnerability-alerts")
    if code and "Not Found" not in str(data):
        notes.append(f"Dependabot alerts setting unreadable: {data}"[:200])
    elif code:  # 404 is the documented answer for "disabled"
        findings.append({"severity": "low", "location": "settings", "rule": "dependabot-alerts-off",
                         "summary": "Dependabot alerts are disabled (or not visible to this token)",
                         "fix": "enable Dependabot alerts in Settings > Code security", "url": ""})
    branch = meta.get("default_branch", "main")
    code, data = gh_api(f"/repos/{repo}/branches/{branch}/protection")
    if code:
        _, rules = gh_api(f"/repos/{repo}/rules/branches/{branch}")
        if isinstance(rules, list) and rules:
            pass  # protected by a ruleset instead of classic branch protection
        elif "Not Found" in str(data) or "not protected" in str(data):
            findings.append({"severity": "medium", "location": f"branch {branch}", "rule": "unprotected-default-branch",
                             "summary": "default branch has no protection rule",
                             "fix": "require pull requests (and status checks) on the default branch", "url": ""})
        else:
            notes.append(f"branch protection unreadable: {data}"[:200])
    code, perms = gh_api(f"/repos/{repo}/actions/permissions/workflow")
    if code:
        notes.append(f"Actions token default unreadable: {perms}"[:200])
    elif isinstance(perms, dict) and perms.get("default_workflow_permissions") == "write":
        findings.append({"severity": "medium", "location": "settings > Actions", "rule": "write-default-token",
                         "summary": "workflows get a read-write GITHUB_TOKEN by default",
                         "fix": "set the default workflow permissions to read-only", "url": ""})
    if meta.get("visibility") == "public":
        has_policy = any(gh_api(f"/repos/{repo}/contents/{p}")[0] == 0
                         for p in ("SECURITY.md", ".github/SECURITY.md"))
        if not has_policy:
            findings.append({"severity": "low", "location": "SECURITY.md", "rule": "no-security-policy",
                             "summary": "public repo without a security policy",
                             "fix": "add SECURITY.md with a private reporting channel", "url": ""})
    return ("partial" if notes else "ok"), findings, "; ".join(notes)


# --- Local scans on a clone -------------------------------------------------

def run_json(cmd: list[str], cwd: Path) -> object:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    if not proc.stdout.strip():
        raise RuntimeError((proc.stderr or "no output").strip()[:300])
    return json.loads(proc.stdout)


def detect_secrets_scan(clone: Path):
    if not shutil.which("detect-secrets"):
        return "skipped", [], "detect-secrets not installed"
    data = run_json(["detect-secrets", "scan", "--all-files", "--exclude-files",
                     r"(^|/)(node_modules|vendor|dist|\.git)/|\.lock$|-lock\.json$"], clone)
    out = []
    for path, hits in (data.get("results") or {}).items():
        for h in hits:
            # Only type and location: detect-secrets' hashed_secret is dropped as well.
            out.append({"severity": "high", "location": f'{path}:{h.get("line_number")}',
                        "rule": h.get("type", ""), "summary": f'possible {h.get("type", "secret")} in the tree',
                        "fix": "if real: rotate, then remove it from the code and history", "url": ""})
    return "ok", out, ""


def zizmor_scan(clone: Path):
    if not (clone / ".github" / "workflows").is_dir():
        return "skipped", [], "no workflows"
    if not shutil.which("zizmor"):
        return "skipped", [], "zizmor not installed"
    data = run_json(["zizmor", "--format", "json", "--offline", ".github/workflows"], clone)
    out = []
    for f in data or []:
        loc = ""
        for location in f.get("locations") or []:
            sym = (location.get("symbolic") or {})
            local = (sym.get("key") or {}).get("Local") or {}
            key = local.get("verbatim_path") or local.get("given_path", "")
            line = (((location.get("concrete") or {}).get("location") or {}).get("start_point") or {}).get("row")
            loc = f"{key}:{line + 1 if isinstance(line, int) else ''}"
            break
        out.append({"severity": norm_severity((f.get("determinations") or {}).get("severity")),
                    "location": loc, "rule": f.get("ident", ""), "summary": f.get("desc", ""),
                    "fix": f.get("url", ""), "url": f.get("url", "")})
    return "ok", out, ""


def pip_audit_scan(clone: Path):
    reqs = sorted(p for p in clone.glob("**/requirements*.txt") if "node_modules" not in p.parts)
    if not reqs:
        return "skipped", [], "no requirements*.txt"
    if not shutil.which("pip-audit"):
        return "skipped", [], "pip-audit not installed"
    out = []
    for req in reqs:
        data = run_json(["pip-audit", "-r", str(req), "-f", "json", "--progress-spinner", "off"], clone)
        for dep in data.get("dependencies", []):
            for v in dep.get("vulns", []):
                out.append({"severity": "medium", "location": str(req.relative_to(clone)),
                            "rule": v.get("id", ""), "summary": f'{dep["name"]} {dep.get("version", "")}: {v.get("id", "")}',
                            "fix": "upgrade to " + ", ".join(v.get("fix_versions") or ["a patched version"]), "url": ""})
    return "ok", out, "pip-audit gives no severity: medium by default, re-rate during triage"


def npm_audit_scan(clone: Path):
    locks = sorted(p for p in clone.glob("**/package-lock.json") if "node_modules" not in p.parts)
    if not locks:
        return "skipped", [], "no package-lock.json"
    if not shutil.which("npm"):
        return "skipped", [], "npm not installed"
    out = []
    for lock in locks:
        data = run_json(["npm", "audit", "--json", "--package-lock-only"], lock.parent)
        for name, v in (data.get("vulnerabilities") or {}).items():
            if not v.get("isDirect") and v.get("severity") in ("low", "info"):
                continue
            out.append({"severity": norm_severity(v.get("severity")), "location": str(lock.relative_to(clone)),
                        "rule": name, "summary": f'{name} ({v.get("range", "")})',
                        "fix": "npm audit fix" if v.get("fixAvailable") else "no automatic fix", "url": ""})
    return "ok", out, ""


# --- Main --------------------------------------------------------------------

def collect(repo: str, clone: Path | None, days: int) -> dict:
    code, meta = gh_api(f"/repos/{repo}")
    if code:
        return {"repo": repo, "reachable": False, "error": str(meta)}
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _, commits = gh_api(f"/repos/{repo}/commits?sha={meta['default_branch']}&since={since}&per_page=100")
    _, head = gh_api(f"/repos/{repo}/commits/{meta['default_branch']}")
    checks = [
        check("dependabot", lambda: dependabot_alerts(repo)),
        check("secret-scanning", lambda: secret_scanning_alerts(repo)),
        check("code-scanning", lambda: code_scanning_alerts(repo)),
        check("repo-settings", lambda: repo_settings(repo, meta)),
    ]
    if clone:
        checks += [
            check("secrets-in-tree", lambda: detect_secrets_scan(clone)),
            check("workflows", lambda: zizmor_scan(clone)),
            check("pip-audit", lambda: pip_audit_scan(clone)),
            check("npm-audit", lambda: npm_audit_scan(clone)),
        ]
    counts = {s: 0 for s in SEVERITIES}
    for c in checks:
        for f in c["findings"]:
            counts[f["severity"]] += 1
    return {
        "repo": repo,
        "reachable": True,
        "collected_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "iso_week": "{}-W{:02d}".format(*dt.date.today().isocalendar()[:2]),
        "default_branch": meta["default_branch"],
        "visibility": meta.get("visibility"),
        "head_sha": head.get("sha", "")[:7] if isinstance(head, dict) else None,
        # None = unknown (API error); 100 means "100 or more".
        "commits_in_window": len(commits) if isinstance(commits, list) else None,
        "window_days": days,
        "counts": counts,
        "checks": checks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo", help="OWNER/REPO")
    ap.add_argument("--clone", type=Path, help="local clone of the default branch, enables local scans")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    json.dump(collect(args.repo, args.clone, args.days), sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
