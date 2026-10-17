---
name: docs-pulse
description: Weekly documentation pass on the repositories listed in pulse.config.yml. A script lists what shipped (merged PRs and direct commits); you write the changelog entries a reader needs, find docs that no longer match the code, fix them minimally, and open one idempotent PR per repo. Use when a routine or user asks for the weekly docs pulse.
---

# docs-pulse

**Goal:** for each watched repo, one pull request per ISO week that brings the changelog and docs back in line with what actually shipped. The owner reviews and merges. You never do.

**Your job is judgment, not listing.** `scripts/pulse_docs.py` already lists merged PRs, direct commits, changed files and release tooling. You add what a script can't: describing a change for someone who uses the project, and noticing that a doc now says something false.

`CLAUDE.md` rules override everything below.

## 1. Per repo: collect

```bash
mkdir -p /tmp/pulse
python3 scripts/pulse_docs.py OWNER/REPO --days <docs.window_days> --changelog <docs.changelog> \
  --branch-prefix <docs.branch_prefix> > /tmp/pulse/REPO.docs.json
```

- `reachable: false` → not attached to the routine; note it, move on.
- `errors` non-empty → the facts are incomplete. Don't conclude "quiet week" and don't open a PR for this repo; report the errors in the final summary.
- `merged_prs` and `direct_commits` both empty → **quiet week**: no branch, no PR, one line in the final summary.
- `open_pulse_pr` set → a previous docs PR is still unmerged, possibly from an earlier week. You extend it (its branch, its PR) instead of opening another, so last week's corrections aren't lost.

Solo projects often commit straight to the default branch. **Direct commits count as much as PRs.**

## 2. Read the changes

```bash
git clone --filter=blob:none https://github.com/OWNER/REPO /tmp/pulse/REPO   # full history, light: needed to merge and push later
git -C /tmp/pulse/REPO log --since="<window start>" -p --stat
```

For each change, assign one category: **Added**, **Changed**, **Fixed**, **Removed**, **Security**, or **Internal** (refactor, CI, tests, tooling: invisible to a user). Bot dependency bumps collapse into a single "Dependencies" line.

## 3. Changelog — only if no release tool owns it

If `release_tools` is non-empty (release-please, changesets, git-cliff, semantic-release), **do not touch the changelog**: that tool writes it from the commits. Say so in the PR body and go to step 4.

Otherwise, in `docs.changelog` ([Keep a Changelog](https://keepachangelog.com) format; create the file with its standard header if `changelog_exists` is false):

- add or extend the `## [Unreleased]` section, one bullet per user-facing change: `- <what changed for the user> (#PR or short sha)`;
- write for someone who uses the project, not for someone reading the diff. "Export reports as CSV from the dashboard", not "add csvExport util";
- leave Internal changes out unless they change how to build, run or deploy;
- never edit or reorder released sections.

## 4. Doc drift

For each user-facing change, search `docs.docs_paths` for what it touched: new or renamed commands, flags, env vars, config keys, routes, public functions, default values, setup steps.

```bash
grep -rn "<identifier>" README.md docs/
```

- Documented and now wrong → fix the sentence, nothing around it.
- Missing and clearly needed (a new required env var, a new command) → add the shortest paragraph that makes it usable, next to its siblings.
- You can't tell the correct behaviour from the code → don't guess. Add a `TODO(weekly-pulse)` checkbox in the PR body under "Needs a human".

If neither the changelog nor any doc needs a change, don't open a PR: "docs in sync" in the final summary.

## 5. Open or update the PR

1. If `open_pulse_pr` is set, check out its `branch`, merge the default branch into it (never rebase: that would need a force-push), and add this week's changes on top. Otherwise create `pulse_branch` from the default branch.
2. Stage only the changelog and files under `docs_paths`, then check the staged diff before committing:
   ```bash
   git -C /tmp/pulse/REPO diff --cached | python3 scripts/verify_report.py - --secrets-only
   ```
   Commit and push with git (a plain push, never forced).
3. Fill [`report-template.md`](report-template.md) in the configured `language` → `/tmp/pulse/REPO.docs.md`, then:
   ```bash
   python3 scripts/verify_report.py /tmp/pulse/REPO.docs.md --pulse docs --week <iso_week> --title "<PR title>"
   ```
   Don't post if it fails.
4. With the REST API: if `open_pulse_pr` is set, `PATCH` its body (keep a section per week, newest first; the marker line is this week's) and its title (`📚 Docs pulse — <first week> → <week>`); else `POST /repos/OWNER/REPO/pulls` with title `📚 Docs pulse — <week>`, `head`, `base`, body, and `"draft": true` if "Needs a human" has items. Then add the label with `POST /repos/OWNER/REPO/issues/<n>/labels` (create it first with `POST /repos/OWNER/REPO/labels` if missing). An existing PR can't be switched to draft through REST: leave it as it is; the "Needs a human" section says enough.

## Don'ts

- Don't touch source code, tests or config. Only the changelog and `docs_paths`.
- Don't restyle docs you aren't correcting.
- Don't merge, approve or enable auto-merge.
