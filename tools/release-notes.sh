#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Prints the CHANGELOG section of one version, for the GitHub release of that version.
# Usage: tools/release-notes.sh 0.15.0 [CHANGELOG.md]
set -u
v="${1:?version}"; f="${2:-$(dirname "$0")/../CHANGELOG.md}"
awk -v v="$v" '
  /^## / { if (on) exit; on = ($2 == v); next }
  on { print }
' "$f" | sed -e '1{/^$/d}' -e '${/^$/d}'
