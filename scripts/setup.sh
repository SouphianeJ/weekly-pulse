#!/usr/bin/env bash
# Tools used by the security pulse. Paste this into the cloud environment's setup
# script so the install is cached between runs; the skill re-runs it if a tool is missing.
set -euo pipefail
pip install --quiet --disable-pip-version-check detect-secrets zizmor pip-audit
