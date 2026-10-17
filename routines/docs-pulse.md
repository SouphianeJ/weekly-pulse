# Routine: docs-pulse

| Setting | Value |
|---|---|
| Schedule | Weekly, Friday afternoon (PRs ready to review before the weekend) |
| Repositories | **weekly-pulse first**, then every repo in `pulse.config.yml` |
| Environment setup script | none needed |
| Network | Default (trusted) |

Prompt:

```text
Run the weekly docs pulse.

Work from the weekly-pulse repository: cd into its clone first, wherever the
session started. Read its CLAUDE.md and pulse.config.yml, then load the
`docs-pulse` skill from its .claude/skills folder and follow it for every repo
in the config.

All CLAUDE.md rules apply. Above all: only touch the changelog and the docs,
push only to branches starting with `branch_prefix` from the config, never merge, run
scripts/verify_report.py on every PR body before posting, and update this
week's PR if it already exists.

Finish with one line per repo and the PR links.
```
