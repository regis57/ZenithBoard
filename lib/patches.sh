# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Debian security patches, installed by themselves (menu 4 Settings -> Reliability, and `zenithboard patches`).
#
# Debian publishes security fixes for the packages the Pi runs on — openssl, the kernel, curl, python — and nothing
# installs them unless something does. unattended-upgrades does, once a day. It is told to take ONLY the Debian
# security channel, nothing else: the feeders (FlightAware, Flightradar24, Plane Finder, ADSB Exchange) come from
# other repositories and are never touched, readsb is built from source and is not a package at all, and the Pi is
# never rebooted by it. `sudo zenithboard update` remains the way the ADS-B software moves.
#
# Reversible: `off` removes the one file this writes, and removes unattended-upgrades too if it was `on` that
# installed it — a Pi that had it before keeps it exactly as it was.
PATCHES_CONF="${ZB_APT_CONF_DIR:-/etc/apt/apt.conf.d}/52zenithboard-security-patches"
PATCHES_LOG="${ZB_UU_LOG:-/var/log/unattended-upgrades/unattended-upgrades.log}"
PATCHES_FEEDERS="dump1090-fa piaware fr24feed pfclient adsbexchange-feed adsbexchange-stats readsb"   # never touched; belt and braces, the origin filter already leaves them out

patches_state() { [ -f "$PATCHES_CONF" ] && echo on || echo off; }

patches_conf_text() {
  local p
  cat <<'C'
// Written by ZenithBoard (zenithboard patches on). Remove with: sudo zenithboard patches off
// Debian security fixes only. The ADS-B feeders live in other repositories and are left to `zenithboard update`.
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
#clear Unattended-Upgrade::Origins-Pattern;
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=${distro_codename}-security,label=Debian-Security";
    "origin=Debian,codename=${distro_codename},label=Debian-Security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "false";
Unattended-Upgrade::Package-Blacklist {
C
  for p in $PATCHES_FEEDERS; do printf '    "%s";\n' "$p"; done
  echo '};'
}

patches_on() {
  if ! pkg_installed unattended-upgrades; then
    apt_install unattended-upgrades || { echo "Could not install unattended-upgrades."; return 1; }
    cfg_set PATCHES_PKG_BY_ZB 1          # so that `off` knows to take it away again
  fi
  install -d -m 755 "$(dirname "$PATCHES_CONF")"
  patches_conf_text > "$PATCHES_CONF.new" && mv -f "$PATCHES_CONF.new" "$PATCHES_CONF" && chmod 644 "$PATCHES_CONF"
  cfg_set PATCHES 1
  echo "Debian security patches: ON. Once a day, security fixes from Debian only; the feeders are left alone and the Pi is never rebooted by it."
  echo "Log: $PATCHES_LOG    Off again: sudo zenithboard patches off"
}

patches_off() {
  rm -f "$PATCHES_CONF"
  if [ "$(cfg_get PATCHES_PKG_BY_ZB 0)" = 1 ]; then
    apt_remove unattended-upgrades >/dev/null 2>&1 || true
    cfg_set PATCHES_PKG_BY_ZB 0
    echo "Debian security patches: OFF. unattended-upgrades, which ZenithBoard had installed, was removed again."
  else
    echo "Debian security patches: OFF. unattended-upgrades was on this Pi before ZenithBoard, so it is left as it was."
  fi
  cfg_set PATCHES 0
}

patches_status() {
  echo "Debian security patches: $(patches_state)"
  if [ -f "$PATCHES_CONF" ]; then
    echo "Rule: $PATCHES_CONF (Debian security channel only; feeders excluded; no reboot)"
    if [ -f "$PATCHES_LOG" ]; then echo "Last lines of $PATCHES_LOG:"; tail -n 5 "$PATCHES_LOG" | sed 's/^/  /'
    else echo "No run yet (the first one happens within a day)."; fi
  else
    echo "Turn on with: sudo zenithboard patches on"
  fi
}
