# weekly-pulse

Two weekly Claude Code routines for people who maintain more repos than they have time to watch.

🇫🇷 [Lire en français](README.fr.md)

| Routine | Every week, for each repo you list | You get |
|---|---|---|
| 🔐 **security-pulse** | Dependency vulnerabilities, secrets in the tree, risky GitHub Actions workflows, weak repo settings, and a read of the week's diff | One issue in that repo, updated in place if the routine runs twice |
| 📚 **docs-pulse** | What was merged or pushed, changelog entries written for users, docs that no longer match the code | One pull request in that repo, for you to review and merge |

On side projects, security alerts pile up untriaged and READMEs keep describing options that were removed months ago. With weekly-pulse the owner reads one issue and one PR per repo each week, and decides.

Nothing is merged, deleted or pushed to a default branch. Claude proposes, you decide.

## How it works

```
pulse.config.yml ──► scripts/pulse_*.py ──► facts (JSON) ──► skill: triage & write ──► scripts/verify_report.py ──► issue / PR
                     tested, deterministic                    the agent's judgment        fail-closed check
```

Scripts do everything whose expected output can be written down in advance: calling the GitHub REST API, running detect-secrets, zizmor, pip-audit and npm audit, listing merged PRs and direct commits. Each check returns a status, so a scanner that couldn't run shows up as a gap and never as a clean result.

The agent does the rest. It tells a test fixture from a live key, groups dozens of transitive npm advisories under the few direct dependencies that pull them in, checks whether a vulnerable package is actually reached, reads the week's diff for missing auth checks, writes changelog lines for a reader, and notices that the README still documents a removed option.

Every body passes `verify_report.py` before it is posted. It refuses anything without this week's marker (that marker is what makes re-runs update instead of duplicate) and anything that looks like a secret value.

## Prior art, and where this fits

GitHub already offers Dependabot, secret scanning and CodeQL. On public repos, turn them on: they cover most of the detection. On private repos of a personal account, secret scanning and code scanning aren't available, and a cloud session can't read those alert APIs anyway. weekly-pulse reads what GitHub gives, fills the gaps with local scanners, and adds the weekly triage on top.

For changelogs, [release-please](https://github.com/googleapis/release-please), [changesets](https://github.com/changesets/changesets) and [git-cliff](https://git-cliff.org) do the job deterministically. If a repo uses one, docs-pulse leaves its changelog alone and only fixes doc drift. Doc-drift agents exist too, for example in [githubnext/agentics](https://github.com/githubnext/agentics).

What I couldn't find was the two jobs packaged as skills for scheduled routines, with a tested collection layer and a check that blocks a leak before it is posted.

## Repository layout

```
CLAUDE.md                 rules the agent follows on every run
DECISIONS.md              dated design decisions, and what would reopen each one
pulse.config.yml          the repos to watch and a few options
scripts/                  collectors, report verifier, setup
tests/                    unit tests for the scripts
.claude/skills/           security-pulse and docs-pulse, each with a report template
routines/                 settings and prompt for each routine
docs/setup.md             setup guide (also in French)
```

## Getting started

Fork, list your repos in `pulse.config.yml`, create two routines from `routines/`. The [setup guide](docs/setup.md) covers the details that matter: attach every watched repo to the routine, use `gh api` because GraphQL is blocked in cloud sessions, install scanners from PyPI.

## Status

v0.1, October 2026. Both collectors were run against a real repository; the collectors and the verifier are covered by unit tests. The routines have not yet run end to end on a schedule; the first runs will be reported in `DECISIONS.md`.

## License

[MIT](LICENSE)
