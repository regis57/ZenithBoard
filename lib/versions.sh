# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck disable=SC2034
# shellcheck shell=bash
# Third-party pins. Bump here when an upstream moves; everything else reads these.
ZB_VERSION="0.99.14"

# FlightAware APT repository package (provides piaware and dump1090-fa). FlightAware renamed it from
# piaware-repository (9.0.1) to flightaware-apt-repository; see https://www.flightaware.com/adsb/piaware/install
FA_REPO_VERSION="1.3"
FA_REPO_URL="https://www.flightaware.com/adsb/piaware/files/packages/pool/piaware/f/flightaware-apt-repository/flightaware-apt-repository_${FA_REPO_VERSION}_all.deb"

# readsb (wiedehopf) - maintained installer/uninstaller scripts
READSB_INSTALL_URL="https://github.com/wiedehopf/adsb-scripts/raw/master/readsb-install.sh"
# There is no readsb uninstaller: wiedehopf's scripts install readsb by building it, and provide no way back.
# ZenithBoard used to fetch a readsb-uninstall.sh that does not exist, so removing readsb quietly did nothing.
# It now says so and prints the commands instead of pretending (readsb_removal_help in lib/adsb.sh).
# The key GitHub signs merge commits with. Until 0.54.18 its fingerprint was deliberately not written here and every
# new card asked the owner to compare it with GitHub's Verified badge (zb_trust_setup in lib/update.sh). On a fresh
# card that question came right after install.sh had run as root from this same clone, so the clone was already
# trusted; the question only looked like an error (the expired key listed first, the owner's fresh card, 25 October
# 2026). The current key is now shipped: a key file from GitHub holding exactly it is trusted without a question. A
# key GitHub adds later (a rotation) is not in this list, and is asked about as before.
# Checked on 25 October 2026: main's latest commit (GitHub's squash merge) is signed by key ID B5690EEEBB952194, and
# web-flow.gpg, as the owner's fresh card read it that day, lists 968479A1AFF927E37D1A566BB5690EEEBB952194 (valid)
# and 5DE3E0509C47EA3CF04A42D34AEE18F83AFDEB23 (expired 2024, never trusted).
GITHUB_SIGNING_KEY_URL="https://github.com/web-flow.gpg"
GITHUB_SIGNING_KEY_FPRS="968479A1AFF927E37D1A566BB5690EEEBB952194"

# graphs1090 (wiedehopf), optional since 0.32.0: its author's installer, as for readsb; read in full on 20 October 2026
GRAPHS1090_INSTALL_URL="https://github.com/wiedehopf/graphs1090/raw/master/install.sh"

TAR1090_UNINSTALL_URL="https://github.com/wiedehopf/tar1090/raw/master/uninstall.sh"   # printed, never run by us

# ADSB Exchange feeder (installs adsbexchange-feed + the ONE mlat client)
ADSBX_FEED_URL="https://adsbexchange.com/feed.sh"
ADSBX_UPDATE_URL="https://adsbexchange.com/feed-update.sh"
ADSBX_UNINSTALL="/usr/local/share/adsbexchange/uninstall.sh"
# 0.52.0: their stats package, optional (lib/adsbxstats.sh); it redirects to github.com/adsbexchange/adsbexchange-stats
ADSBX_STATS_URL="https://adsbexchange.com/stats.sh"

# Tailscale
TAILSCALE_PKGS="https://pkgs.tailscale.com/stable"   # 0.45.0: Tailscale's own repository (pkgs.tailscale.com/stable, read 21 October 2026)

# Flightradar24
FR24_INSTALL_URL="https://repo-feed.flightradar24.com/install_fr24_rpi.sh"
# FR24 re-signed its apt repository with a new key because Debian 13 (trixie) rejects SHA1 signatures since
# 2026-02-01. The key is only installed if it has exactly this fingerprint (the one apt reports as "missing").
FR24_KEY_URL="https://repo-feed.flightradar24.com/flightradar24.2026.pub"
FR24_KEY_FPR="ED843290A602413685E57D436F7703F65FA1BDAF"

# AirNav Radar (RadarBox), 0.99.6: rbfeeder from AirNav's own apt repository. Their installer script could not be read
# from where this was written (30 October 2026), so the repository is added the way the community's container adds it
# (github.com/sdr-enthusiasts/docker-airnavradar, its Dockerfile read that day): key 1D043681, suite bookworm, package
# rbfeeder. The key is installed only with exactly this fingerprint, read from keyserver.ubuntu.com the same day
# ("AirNav Systems", made 30 January 2018). The claim page is the one that container's README gives.
RB24_REPO_URL="https://apt.rb24.com/"
RB24_SUITE="bookworm"
RB24_KEY_FPR="78F6D790E30AE7F360B716FED4F914061D043681"
RB24_KEY_URL="https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x${RB24_KEY_FPR}"
RB24_CLAIM_URL="https://www.airnavradar.com/raspberry-pi/claim"
RB24_STATION_URL="https://www.airnavradar.com/stations/"   # + the station's serial (EXTRPI...). 0.99.8: radarbox.com/stations/ answers 302 to this address (checked 31 October 2026): RadarBox is AirNav Radar's former name

# Plane Finder client. Check https://planefinder.net/sharing/client for newer versions.
PF_VERSION_ARMHF="5.4.211"
PF_VERSION_ARM64="5.4.211"
PF_URL_ARMHF="https://client-v2.planefinder.net/pfclient_${PF_VERSION_ARMHF}_armhf.deb"
PF_URL_ARM64="https://client-v2.planefinder.net/pfclient_${PF_VERSION_ARM64}_arm64.deb"

