# Routine: security-pulse

| Setting | Value |
|---|---|
| Schedule | Weekly, Monday early morning |
| Repositories | **weekly-pulse first**, then every repo in `pulse.config.yml` |
| Environment setup script | the content of [`scripts/setup.sh`](../scripts/setup.sh) |
| Network | Default (trusted) is enough: PyPI and npm are on its allowlist |

Prompt:

```text
Run the weekly security pulse.

Work from the weekly-pulse repository: cd into its clone first, wherever the
session started. Read its CLAUDE.md and pulse.config.yml, then load the
`security-pulse` skill from its .claude/skills folder and follow it for every
repo in the config.

All CLAUDE.md rules apply. Above all: never write a secret's value, never post
findings outside the repo they concern, run scripts/verify_report.py on every
body before posting, and update this week's issue if it already exists.

Finish with one line per repo and the issue links.
```
