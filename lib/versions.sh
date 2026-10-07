# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck disable=SC2034
# shellcheck shell=bash
# Third-party pins. Bump here when an upstream moves; everything else reads these.
ZB_VERSION="0.8.5"

# FlightAware APT repository package (provides piaware and dump1090-fa). FlightAware renamed it from
# piaware-repository (9.0.1) to flightaware-apt-repository; see https://www.flightaware.com/adsb/piaware/install
FA_REPO_VERSION="1.3"
FA_REPO_URL="https://www.flightaware.com/adsb/piaware/files/packages/pool/piaware/f/flightaware-apt-repository/flightaware-apt-repository_${FA_REPO_VERSION}_all.deb"

# readsb (wiedehopf) - maintained installer/uninstaller scripts
READSB_INSTALL_URL="https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh"
READSB_UNINSTALL_URL="https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-uninstall.sh"

# ADSB Exchange feeder (installs adsbexchange-feed + the ONE mlat client)
ADSBX_FEED_URL="https://adsbexchange.com/feed.sh"
ADSBX_UPDATE_URL="https://adsbexchange.com/feed-update.sh"
ADSBX_UNINSTALL="/usr/local/share/adsbexchange/uninstall.sh"

# Flightradar24
FR24_INSTALL_URL="https://repo-feed.flightradar24.com/install_fr24_rpi.sh"
# FR24 re-signed its apt repository with a new key because Debian 13 (trixie) rejects SHA1 signatures since
# 2026-02-01. The key is only installed if it has exactly this fingerprint (the one apt reports as "missing").
FR24_KEY_URL="https://repo-feed.flightradar24.com/flightradar24.2026.pub"
FR24_KEY_FPR="ED843290A602413685E57D436F7703F65FA1BDAF"

# Plane Finder client. Check https://planefinder.net/sharing/client for newer versions.
PF_VERSION_ARMHF="5.4.211"
PF_VERSION_ARM64="5.4.211"
PF_URL_ARMHF="https://client-v2.planefinder.net/pfclient_${PF_VERSION_ARMHF}_armhf.deb"
PF_URL_ARM64="https://client-v2.planefinder.net/pfclient_${PF_VERSION_ARM64}_arm64.deb"

# acarsdec (ACARS decoder), built from source
ACARSDEC_REPO="https://github.com/TLeconte/acarsdec.git"
ACARSDEC_REF="master"
