# Design decisions

Dated, append-only. A decision that gets revisited gets a new entry pointing to the old one. Each entry says what would make us reopen it.

## 2026-10-17 — Scripts collect, the agent judges

**Decision.** Everything with a known expected output runs as a tested script: calling the GitHub API, running scanners, listing merged PRs, checking a report before posting. The agent only does what can't be written as an assertion in advance: triage, rating real exposure, telling a test fixture from a live key, describing a change for a user, spotting a doc that became false.

**Why.** A first draft asked the agent to "run npm audit, grep for secrets…" itself. That spends judgment on mechanics, varies from run to run, and can't be tested. The collectors were run against a real repo before being kept.

**Reopen if** a collector needs patching more than once a month to follow API or tool changes: the maintenance would then outweigh the stability.

## 2026-10-17 — Rely on GitHub's own alerts first, scan only to fill the gaps

**Decision.** The security pulse reads Dependabot, secret scanning and code scanning alerts through the API, and runs local tools (detect-secrets, zizmor, pip-audit, npm audit) next to them. A check that couldn't run is reported as a coverage gap, never as a clean result.

**Why.** Those GitHub features exist and are free on public repos; rebuilding them would be pointless. But from a Claude Code session several of those endpoints answer 403 (observed on 2026-10-17: secret scanning blocked by the proxy, code scanning not accessible to the integration). The local tools cover that gap; the agent's added value is the triage across all sources.

**Reopen if** the session gains full access to the alert APIs: the local secret scan could then be dropped for repos where secret scanning is on.

## 2026-10-17 — detect-secrets rather than gitleaks

**Decision.** Secret scanning in the tree uses `detect-secrets` (PyPI).

**Why.** Downloading gitleaks from GitHub releases is refused by the session proxy (403, 2026-10-17), while PyPI is reachable. detect-secrets also reports a hash instead of the value, which the collector drops too, so no secret value travels in the collected facts. The agent can still meet one when it opens a flagged file or reads the week's diff; that residual risk is what the verifier below covers.

**Reopen if** gitleaks becomes installable from a package registry the session can reach and finds things detect-secrets misses on our repos.

## 2026-10-17 — A fail-closed verifier before every post

**Decision.** `scripts/verify_report.py` must pass on every issue or PR body before it is posted. It refuses a body without this week's marker and any body containing a secret-shaped string.

It also checks titles, and the staged diff before a docs commit.

**Why.** "Never write a secret" as a prompt rule is a discipline; a check that blocks the post is a mechanism. The marker check is what makes re-runs update instead of duplicate.

**Reopen if** it refuses legitimate reports more than once in a month: the patterns would then need narrowing, with a test for each case.

## 2026-10-17 — Findings stay in the repo they concern

**Decision.** Security issues are opened in each watched repo. Nothing about a watched repo is written into weekly-pulse.

**Why.** weekly-pulse is public and the repos it watches are often private.

**Reopen if** an owner wants a cross-repo dashboard; it would then go to a private destination, never here.

## 2026-10-17 — Direct commits count as much as merged PRs

**Decision.** The docs pulse covers both merged PRs and commits pushed straight to the default branch.

**Why.** On the first real repo tested, every change since 2024 was a direct commit and no PR was ever merged. A PR-only pulse would report a quiet week forever.

## 2026-10-17 — Weekly docs branch under `claude/`

**Decision.** The docs PR branch is `claude/weekly-pulse-docs-<ISO week>`.

**Why.** Routines push to `claude/`-prefixed branches by default. Staying inside that convention keeps the default protection and means no extra permission to grant.

## 2026-10-17 — Leave the changelog to release tools when there is one

**Decision.** If a repo uses release-please, changesets, git-cliff or semantic-release, the docs pulse doesn't touch the changelog and only fixes doc drift.

**Why.** Those tools generate the changelog from commits; a second writer would conflict with them. Doc drift is the part no such tool covers.
