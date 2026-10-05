# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck disable=SC2034
# shellcheck shell=bash
# Third-party pins. Bump here when an upstream moves; everything else reads these.
ZB_VERSION="0.1.0"

# FlightAware APT repository package (provides piaware and dump1090-fa)
PIAWARE_REPO_VERSION="9.0.1"
PIAWARE_REPO_URL="https://www.flightaware.com/adsb/piaware/files/packages/pool/piaware/p/piaware-support/piaware-repository_${PIAWARE_REPO_VERSION}_all.deb"

# readsb (wiedehopf) - maintained installer/uninstaller scripts
READSB_INSTALL_URL="https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh"
READSB_UNINSTALL_URL="https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-uninstall.sh"

# ADSB Exchange feeder (installs adsbexchange-feed + the ONE mlat client)
ADSBX_FEED_URL="https://www.adsbexchange.com/feed.sh"
ADSBX_UPDATE_URL="https://www.adsbexchange.com/feed-update/"
ADSBX_UNINSTALL="/usr/local/share/adsbexchange/uninstall.sh"

# Flightradar24
FR24_INSTALL_URL="https://repo-feed.flightradar24.com/install_fr24_rpi.sh"

# Plane Finder client. Check https://planefinder.net/sharing/client for newer versions.
PF_VERSION_ARMHF="5.0.162"
PF_VERSION_ARM64="5.0.162"
PF_URL_ARMHF="http://client.planefinder.net/pfclient_${PF_VERSION_ARMHF}_armhf.deb"
PF_URL_ARM64="http://client.planefinder.net/pfclient_${PF_VERSION_ARM64}_arm64.deb"

# acarsdec (ACARS decoder), built from source
ACARSDEC_REPO="https://github.com/TLeconte/acarsdec.git"
ACARSDEC_REF="master"
