# Setup

🇫🇷 [Version française](setup.fr.md)

About ten minutes, from fork to first run.

## Before you start

- [Claude Code on the web](https://code.claude.com/docs/en/claude-code-on-the-web) with [routines](https://code.claude.com/docs/en/routines) (in research preview at the time of writing).
- GitHub connected to Claude, with access to every repo you want to watch. Private repos need the Claude GitHub App installed on them, or your `gh` token sent with `/web-setup`.

## 1. Fork and configure

Fork this repo (or **Use this template**), then edit [`pulse.config.yml`](../pulse.config.yml):

```yaml
language: en        # or fr
repos:
  - you/api
  - you/web-app
```

Check the scripts work with your account before scheduling anything:

```bash
bash scripts/setup.sh
python3 -m unittest discover tests
python3 scripts/pulse_security.py you/api | head -40
```

## 2. Create the two routines

For each file in [`routines/`](../routines/), create a routine with the settings and prompt it gives. Three things matter:

1. **Attach weekly-pulse first, then every watched repo.** A session can only call the GitHub API for the repos attached to it; any other repo answers 403. The config file alone is not enough.
2. **Paste [`scripts/setup.sh`](../scripts/setup.sh) as the environment's setup script** for the security routine, so the scanners are installed once and cached.
3. **Keep the default network.** PyPI, npm and the GitHub API are on its allowlist, and nothing else is needed.

Then **run each routine once by hand** and read the session.

## 3. What a good first run looks like

- [ ] Each watched repo has a `🔐 Security pulse — <week>` issue.
- [ ] Each repo with changes this week has a `📚 Docs pulse — <week>` PR on a `claude/weekly-pulse-docs-<week>` branch, or the summary says "quiet week" or "docs in sync".
- [ ] Running a routine again the same week updates the issue or PR instead of creating another.
- [ ] The "Not checked" section of the issue explains every missing check.

## Troubleshooting

| What you see | Why, and what to do |
|---|---|
| `not reachable` / 403 "access … not enabled for this session" | The repo isn't attached to the routine. Attach it. |
| `gh pr create` or `gh issue create` fails | GraphQL is blocked from cloud sessions. The skills use `gh api` (REST); don't switch back. |
| Secret scanning / code scanning listed under "Not checked" | These APIs aren't reachable from a session, and on private personal repos GitHub doesn't offer them. `detect-secrets` covers the tree instead. |
| `detect-secrets: not installed` | The setup script didn't run. Check the environment settings. |
| Two issues for the same week | The marker comment (first line of the body) was edited out. Restore it on one and close the other. |
| The routine doesn't seem to load the skills | Make sure weekly-pulse is the **first** attached repo; the prompt also tells the agent to `cd` into it. |

## Adding a pulse

1. A collector in `scripts/` for everything with a known expected output, with tests.
2. A skill in `.claude/skills/<name>-pulse/SKILL.md` for the judgment part: inputs, procedure, report with this week's marker, don'ts.
3. Its options under a new key in `pulse.config.yml`, a prompt in `routines/`, and an entry in `DECISIONS.md`.
