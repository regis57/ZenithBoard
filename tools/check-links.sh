#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Are the pinned download addresses in lib/versions.sh still there?
#
# Providers rename and move their files, and the first symptom is an install that stops with a 404 on somebody
# else's Pi. A monthly run of this says so first. It checks that each address answers, nothing more: it cannot
# know that a newer version exists behind a different name.
#
#   bash tools/check-links.sh
#
# Exit code 0: every address answered. 1: at least one did not (they are listed).
set -uo pipefail

here=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=lib/versions.sh
. "$here/lib/versions.sh"

urls=(
  "$FA_REPO_URL"
  "$READSB_INSTALL_URL"
  "$TAR1090_UNINSTALL_URL"
  "$ADSBX_FEED_URL"
  "$ADSBX_UPDATE_URL"
  "$FR24_INSTALL_URL"
  "$FR24_KEY_URL"
  "$PF_URL_ARMHF"
  "$PF_URL_ARM64"
)

fail=0
for u in "${urls[@]}"; do
  [ -n "$u" ] || continue
  code=$(curl -fsSIL -o /dev/null -w '%{http_code}' --connect-timeout 20 --max-time 60 "$u" 2>/dev/null) || code=""
  if [ -n "$code" ] && [ "$code" -lt 400 ] 2>/dev/null; then
    printf 'ok    %s  %s\n' "$code" "$u"
  else
    # a few servers refuse HEAD but serve the file: ask for the first bytes before calling it gone
    code=$(curl -fsSL -r 0-0 -o /dev/null -w '%{http_code}' --connect-timeout 20 --max-time 60 "$u" 2>/dev/null) || code=""
    if [ -n "$code" ] && [ "$code" -lt 400 ] 2>/dev/null; then
      printf 'ok    %s  %s\n' "$code" "$u"
    else
      printf 'GONE  %s  %s\n' "${code:-no answer}" "$u"
      fail=1
    fi
  fi
done

if [ "$fail" = 1 ]; then
  echo
  echo "At least one pinned address no longer answers. The fix is in lib/versions.sh:"
  echo "find the provider's current file and update the version or the URL."
fi
exit "$fail"
