#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Sanity checks on the pinned third-party addresses (no network): every download is https and has the shape
# the installer expects. It cannot know a provider renamed a file - that is what the README's note is for.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=lib/versions.sh
. "$HERE/lib/versions.sh"
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

for v in FA_REPO_URL READSB_INSTALL_URL TAR1090_UNINSTALL_URL ADSBX_FEED_URL ADSBX_UPDATE_URL FR24_INSTALL_URL PF_URL_ARMHF PF_URL_ARM64; do
  check "$v is an https address" '[[ "${!v:-}" == https://* ]]'
done
check "FlightAware repo package is flightaware-apt-repository_<version>_all.deb" '[[ "$FA_REPO_URL" == *"/flightaware-apt-repository_${FA_REPO_VERSION}_all.deb" ]]'
check "the old piaware-repository name is gone from the pinned URL" '[[ "$FA_REPO_URL" != *piaware-repository* ]]'
check "Plane Finder packages match their pinned versions" '[[ "$PF_URL_ARMHF" == *"_${PF_VERSION_ARMHF}_armhf.deb" && "$PF_URL_ARM64" == *"_${PF_VERSION_ARM64}_arm64.deb" ]]'
check "ZenithBoard version looks like x.y.z" '[[ "$ZB_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]'
# 0.54.1: the docs said this test fails when the version numbers drift; it only checked the shape. The places CLAUDE.md
# step 3 names must now say the same version as lib/versions.sh.
check "the wall server says the same version"        '[ "$(sed -n "s/^VERSION = \"\(.*\)\"$/\1/p" "$HERE/flightinfo/server.py")" = "$ZB_VERSION" ]'
check "the wiki's home page says the same version"   'grep -q "^Current version: \*\*$ZB_VERSION\*\*" "$HERE/docs/wiki/Home.md"'
check "Project-status says the same version"         'grep -q "version \*\*$ZB_VERSION\*\*" "$HERE/docs/wiki/Project-status.md"'
exit "$fail"
