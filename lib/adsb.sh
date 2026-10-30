# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Menu 1 - ADSB: decoder (readsb preferred, dump1090-fa fallback) + feeders.
#
# Architecture (identical for both decoders):
#   SDR dongle -> decoder -> Beast TCP on 127.0.0.1:30005 -> every feeder reads from there.
#   Exactly ONE MLAT client may run (it is ADSB Exchange's). FlightAware / FR24 / AirNav Radar MLAT are switched off.

# ------------------------------------------------------------------ MLAT guard
mlat_count() { pgrep -fc 'mlat-client' || true; }

zb_mlat_guard() {
  log "Enforcing a single MLAT client (ADSB Exchange)"
  if is_piaware; then
    piaware-config allow-mlat no >/dev/null 2>&1 || true
    unit_active piaware && systemctl restart piaware || true
  fi
  if is_fr24 && [ -f /etc/fr24feed.ini ]; then
    ini_set /etc/fr24feed.ini mlat no
    ini_set /etc/fr24feed.ini mlat-without-gps no
    unit_active fr24feed && systemctl restart fr24feed || true
  fi
  # 0.99.6: AirNav's own line for it (the owner, 30 October 2026): autostart_mlat=false in [mlat], then a restart
  if is_radarbox && [ -f "$RB24_INI" ] && [ "$(ini_sec_get "$RB24_INI" mlat autostart_mlat)" != false ]; then
    ini_sec_set "$RB24_INI" mlat autostart_mlat false
    unit_active rbfeeder && systemctl restart rbfeeder || true
  fi
  sleep 3
  local n; n=$(mlat_count)
  if [ "${n:-0}" -gt 1 ]; then warn "$n mlat-client processes are running (expected 1). Run: zenithboard status"; else log "MLAT clients running: ${n:-0}"; fi
}

# ------------------------------------------------------------------ decoder
ensure_fa_repo() {
  # flightaware-apt-repository is the current name; piaware-repository is what older installs have (still valid)
  pkg_installed flightaware-apt-repository && return 0
  pkg_installed piaware-repository && return 0
  log "Adding the FlightAware package repository"
  local fa_deb; fa_deb=$(zb_tmp flightaware-apt-repository.deb) || return 1
  fetch "$FA_REPO_URL" "$fa_deb" || {
    warn "FlightAware may have moved its repository package: check lib/versions.sh against https://www.flightaware.com/adsb/piaware/install"
    return 1
  }
  dpkg -i "$fa_deb" && apt-get update
}

set_sdr_serial_readsb() {  # set_sdr_serial_readsb SERIAL_OR_INDEX
  local dev="$1" f=/etc/default/readsb
  [ -n "$dev" ] && [ -f "$f" ] || return 0
  sed -i -E 's/ ?--device [^" ]+//' "$f"
  sed -i -E "s|^(RECEIVER_OPTIONS=\")|\1--device $dev |" "$f"
}

install_decoder() {  # install_decoder readsb|dump1090-fa
  local d="$1" lat lon dev
  lat=$(cfg_get LAT); lon=$(cfg_get LON); dev=$(cfg_get ADSB_SDR)
  apt-get update
  apt_install curl ca-certificates wget
  case "$d" in
    readsb)
      log "Installing readsb"
      local rb; rb=$(zb_tmp readsb-install.sh) || return 1
      fetch "$READSB_INSTALL_URL" "$rb" || return 1
      bash "$rb" || return 1
      command -v readsb-set-location >/dev/null && readsb-set-location "$lat" "$lon"
      set_sdr_serial_readsb "$dev"
      systemctl enable readsb; systemctl restart readsb
      ;;
    dump1090-fa)
      log "Installing dump1090-fa"
      ensure_fa_repo || return 1
      apt_install dump1090-fa || return 1
      local f=/etc/default/dump1090-fa
      sed -i -E 's/--lat [^" ]+ ?//; s/--lon [^" ]+ ?//' "$f"
      sed -i -E "s|^(DECODER_OPTIONS=\")|\1--lat $lat --lon $lon |" "$f"
      [ -n "$dev" ] && sed -i -E "s/--device-index [^\" ]+/--device-index $dev/" "$f"
      systemctl enable dump1090-fa; systemctl restart dump1090-fa
      ;;
    *) err "Unknown decoder $d"; return 1 ;;
  esac
  cfg_set DECODER "$d"
  restart_flightinfo
}

# readsb is built from source by somebody else's installer, which provides no way to undo it. Rather than delete
# files on your Pi from guesswork, ZenithBoard refuses this one out loud and hands you the commands. Everything
# else ZenithBoard installed is removed normally; only readsb itself is left running.
readsb_removal_help() {
  cat <<HELP
readsb cannot be removed automatically.

  It is built and installed by wiedehopf's script, which ships no uninstaller, so there is
  nothing to run and ZenithBoard will not delete system files it did not put there.

  Everything else has been removed. readsb is still installed and still running.

To remove it yourself, as root:

  systemctl disable --now readsb
  rm -f /usr/bin/readsb /usr/bin/viewadsb /usr/local/bin/readsb-gain /usr/local/bin/readsb-set-location
  rm -f /lib/systemd/system/readsb.service /etc/default/readsb
  systemctl daemon-reload
  deluser --system readsb

  Its map (tar1090, on port 80) has its own uninstaller:
  d=\$(mktemp -d) && wget -O "\$d/u.sh" $TAR1090_UNINSTALL_URL && bash "\$d/u.sh"; rm -rf "\$d"

  Read each line before running it. Check /etc/default/readsb first if you want to keep your gain setting.
HELP
}

remove_decoder() {
  if is_readsb; then
    warn "readsb is NOT removed: there is no uninstaller for it (see below)."
    readsb_removal_help
  fi
  if is_dump1090; then log "Removing dump1090-fa"; apt_remove dump1090-fa; fi
}

# ------------------------------------------------------------------ feeders
# 0.54.2: what to type into ADSB Exchange's own boxes, which ask the position again (they take no default) and refuse an
# altitude that is not whole metres or feet with the unit glued to it: "180m", not "180" and not "180 m" (the old line
# here printed "180 m", the very form their box refuses, and a dialog drew over it anyway)
adsbx_answers() {
  local alt; alt=$(awk -v a="$(cfg_get ALT_M 0)" 'BEGIN { printf "%.0f", a }')
  printf 'Its boxes ask, in this order:\n  - a name for its MLAT map (a short word of your own, not 0)\n  - latitude:   %s\n  - longitude:  %s\n  - altitude:   %sm   (the unit glued to the number: not %s, not %s m)\n\nThese are the values already set on this Pi.' \
    "$(cfg_get LAT)" "$(cfg_get LON)" "$alt" "$alt" "$alt"
}
install_adsbx() {
  log "Installing ADSB Exchange feeder (mandatory base layer, owns the single MLAT client)"
  echo "    The ADSB Exchange script will now ask for a station name and your position."
  local ax; ax=$(zb_tmp axfeed.sh) || return 1
  fetch "$ADSBX_FEED_URL" "$ax" || return 1
  if [ -t 0 ] && command -v whiptail >/dev/null 2>&1; then wt_msg "$(adsbx_answers)" 15      # a screen they cannot draw over, kept until OK
  else adsbx_answers | sed 's/^/    /'; echo; fi
  bash "$ax"
}
remove_adsbx() {
  # 0.52.0: their stats read the feed's folder; the feed's uninstaller leaves them running, failing every two minutes
  if declare -F adsbx_stats_off >/dev/null && { is_adsbx_stats || [ -f "$AXS_STATE" ]; }; then adsbx_stats_off; fi
  if [ -x "$ADSBX_UNINSTALL" ] || [ -f "$ADSBX_UNINSTALL" ]; then bash "$ADSBX_UNINSTALL"
  else systemctl disable --now adsbexchange-feed adsbexchange-mlat 2>/dev/null || true; fi
}

install_piaware() {
  log "Installing FlightAware (piaware)"
  ensure_fa_repo || return 1
  apt_install --no-install-recommends piaware || return 1
  piaware-config receiver-type other
  piaware-config receiver-host 127.0.0.1
  piaware-config receiver-port 30005
  piaware-config allow-mlat no
  piaware-config allow-auto-updates yes
  systemctl enable piaware; systemctl restart piaware
  # 0.42.0: a feeder ID restored from a backup before this install keeps the old station; nothing to claim then
  if [ -f "${BK_PENDING:-/nonexistent}/piaware-feeder-id" ]; then bk_pending_apply piaware
  else echo "    Claim this receiver at https://flightaware.com/adsb/piaware/claim (same public IP as this Pi)."; fi
}
remove_piaware() { systemctl disable --now piaware 2>/dev/null || true; apt_remove piaware; }

# --- Flightradar24 -------------------------------------------------------------------------------------------
# Debian 13 (trixie) refuses signatures made with SHA1 since 2026-02-01 and FR24's first signing key used one, so
# `apt update` says the FR24 repository "is not signed". FR24 published a new key. We install it, but ONLY when its
# fingerprint is the pinned one: signature checking is never switched off.
fr24_source_file() { grep -rl "repo-feed.flightradar24.com" "${ZB_APT_DIR:-/etc/apt}/sources.list" "${ZB_APT_DIR:-/etc/apt}/sources.list.d" 2>/dev/null | head -1; }

fr24_repair_key() {
  local apt_dir="${ZB_APT_DIR:-/etc/apt}" src keyring="" tmp fprs
  src=$(fr24_source_file)
  # the keyring file the FR24 source points to (deb822 "Signed-By:" or one-line "[signed-by=...]")
  [ -z "$src" ] || keyring=$(grep -o -i -E 'signed-by(=|: *)[^] ]+' "$src" | head -1 | sed -E 's/^[^=:]*(=|: *)//')
  [ -n "$keyring" ] || keyring="$apt_dir/keyrings/flightradar24.gpg"
  command -v gpg >/dev/null 2>&1 || apt_install gpg || return 1
  tmp=$(mktemp -d) || return 1
  if ! fetch "$FR24_KEY_URL" "$tmp/key.pub"; then rm -rf "$tmp"; return 1; fi
  fprs=$(gpg --batch --show-keys --with-colons "$tmp/key.pub" 2>/dev/null | awk -F: '$1=="fpr"{print $10}')
  if ! printf '%s\n' "$fprs" | grep -qx "$FR24_KEY_FPR"; then
    err "The Flightradar24 key does not have the expected fingerprint ($FR24_KEY_FPR): NOT installed."
    err "Flightradar24 may have changed its key again: check lib/versions.sh against https://forum.flightradar24.com/"
    rm -rf "$tmp"; return 1
  fi
  install -d -m 755 "$(dirname "$keyring")"
  case "$keyring" in
    *.asc) install -m 644 "$tmp/key.pub" "$keyring" ;;                           # apt wants it armoured
    *)     gpg --batch --yes --dearmor -o "$tmp/key.gpg" "$tmp/key.pub" && install -m 644 "$tmp/key.gpg" "$keyring" ;;
  esac
  local rc=$?
  rm -rf "$tmp"
  [ "$rc" -eq 0 ] && log "Flightradar24 signing key (2026) installed in $keyring"
  return "$rc"
}

# true when `apt-get update` still complains about the FR24 repository
fr24_repo_broken() { apt-get update 2>&1 | grep -i "flightradar24" | grep -qi -E "not signed|signature|NO_PUBKEY|GPG error"; }

FR24_INI="${FR24_INI:-/etc/fr24feed.ini}"

# The sign-up wizard is FR24's own and always runs (it also accepts an existing sharing key). What it must be answered
# is printed first, and the receiver settings are enforced afterwards in case of a wrong answer.
fr24_write_ini() {
  ini_set "$FR24_INI" receiver beast-tcp
  ini_set "$FR24_INI" host 127.0.0.1:30005
  ini_set "$FR24_INI" bs no
  ini_set "$FR24_INI" raw no
  ini_set "$FR24_INI" mlat no
  ini_set "$FR24_INI" mlat-without-gps no
}

fr24_has_key() { grep -qE '^fr24key="?[A-Za-z0-9]{8,}' "$FR24_INI" 2>/dev/null; }

fr24_signup_help() {
  cat >&2 <<'EOT'

  Flightradar24 sign-up (FR24's own wizard). Answer like this:
    Email .................... your FR24 email (a free account is created if you have none)
    Sharing key .............. ALREADY FEEDING FR24? Paste your key (flightradar24.com > account > My data sharing,
                               or fr24key= in /etc/fr24feed.ini of an old receiver). Otherwise just press Enter.
    MLAT ..................... no   (ADSB Exchange keeps the only MLAT)
    Autoconfig / receiver .... yes, or: Beast (TCP), host 127.0.0.1, port 30005
    Raw / BS data feed ....... no
  ZenithBoard re-applies the receiver settings afterwards, so a wrong answer is corrected.

EOT
}

install_fr24() {
  log "Installing Flightradar24 feeder"
  # a repository left by an earlier attempt: give it the new key first
  [ -z "$(fr24_source_file)" ] || fr24_repair_key || true
  local fr; fr=$(zb_tmp install_fr24.sh) || return 1
  fetch "$FR24_INSTALL_URL" "$fr" || return 1
  fr24_signup_help
  if [ -n "$(declare -F bk_pending_fr24_key >/dev/null && bk_pending_fr24_key)" ]; then
    # 0.42.0: shown on this terminal only (never logged): FR24's sign-up asks for it, and it is set again afterwards
    printf '  Your sharing key, from your backup:  %s   (paste it at the sharing-key question)\n\n' "$(bk_pending_fr24_key)" >&2
  fi
  if ! bash "$fr" && ! command -v fr24feed >/dev/null 2>&1; then
    # the installer adds the repository and then stops when apt refuses it: repair the key, then finish the job
    [ -n "$(fr24_source_file)" ] || { err "The Flightradar24 installer failed before adding its repository."; return 1; }
    fr24_repair_key || return 1
    if fr24_repo_broken; then err "apt still refuses the Flightradar24 repository. Nothing was changed about signature checking."; return 1; fi
    apt_install fr24feed || return 1
  fi
  [ ! -f "${BK_PENDING:-/nonexistent}/fr24key" ] || bk_pending_apply fr24
  if fr24_has_key; then
    fr24_write_ini
    systemctl enable fr24feed 2>/dev/null || true
    systemctl restart fr24feed || true
    log "Flightradar24 feeder configured (Beast 127.0.0.1:30005, MLAT off)."
  else
    warn "The Flightradar24 sign-up did not finish (no sharing key saved). Run it again:  sudo fr24feed --signup  then  sudo zenithboard update"
  fi
}
remove_fr24() { systemctl disable --now fr24feed 2>/dev/null || true; apt_remove fr24feed; }

install_planefinder() {
  local url deb; deb=$(zb_tmp pfclient.deb) || return 1
  case "$(arch)" in arm64) url="$PF_URL_ARM64" ;; armhf) url="$PF_URL_ARMHF" ;; *) err "Plane Finder: unsupported architecture $(arch)"; return 1 ;; esac
  log "Installing Plane Finder client"
  fetch "$url" "$deb" || { warn "Check lib/versions.sh: the Plane Finder package URL may have changed."; return 1; }
  dpkg -i "$deb" || apt-get -f install -y
  systemctl enable pfclient; systemctl restart pfclient
  [ -f "${BK_PENDING:-/nonexistent}/pfclient-config.json" ] && bk_pending_apply planefinder && return 0
  echo "    Finish setup at http://$(local_ip):30053  (data source: Beast, 127.0.0.1, port 30005)."
}
remove_planefinder() { systemctl disable --now pfclient 2>/dev/null || true; apt_remove pfclient; }

# --- AirNav Radar (RadarBox) -------------------------------------------------------------------------------------
# 0.99.6, asked for by the owner (30 October 2026). rbfeeder from AirNav's own repository, added with its key pinned
# (lib/versions.sh says where each value was read). It reads the decoder's Beast port like every other feeder, makes its
# own sharing key at its first start and keeps it in /etc/rbfeeder.ini, and its MLAT is off: ADSB Exchange keeps the only
# MLAT client. rbfeeder.ini has sections ([client], [network], [mlat]) and plain key=value lines, hence a setter of its
# own, ini_sec_set in lib/common.sh (ini_set writes KEY="VALUE" at the top level, the form of fr24feed.ini).
RB24_INI="${RB24_INI:-/etc/rbfeeder.ini}"
rb24_keyring() { echo "${ZB_APT_DIR:-/etc/apt}/keyrings/zenithboard-rb24.gpg"; }
rb24_our_source() { echo "${ZB_APT_DIR:-/etc/apt}/sources.list.d/zenithboard-rb24.list"; }
rb24_source_file() { grep -rl "apt.rb24.com" "${ZB_APT_DIR:-/etc/apt}/sources.list" "${ZB_APT_DIR:-/etc/apt}/sources.list.d" 2>/dev/null | head -1; }

# true when `apt-get update` complains about AirNav's repository (no such suite, a key apt refuses)
rb24_repo_broken() { apt-get update 2>&1 | grep -i "rb24" | grep -qi -E "not signed|signature|NO_PUBKEY|GPG error|Release file|404|Err:"; }

# The repository, once: a source that already points at it (AirNav's own installer, an earlier run) is used as it is.
# The suite is this system's own when AirNav has it, else bookworm, the one the community's container uses.
rb24_add_repo() {
  local apt_dir="${ZB_APT_DIR:-/etc/apt}" tmp fprs suite keyring src
  if [ -n "$(rb24_source_file)" ]; then apt-get update -qq >/dev/null 2>&1 || true; return 0; fi   # its lists, fresh
  keyring=$(rb24_keyring); src=$(rb24_our_source)
  command -v gpg >/dev/null 2>&1 || apt_install gpg || return 1
  tmp=$(mktemp -d) || return 1
  if ! fetch "$RB24_KEY_URL" "$tmp/key.asc"; then rm -rf "$tmp"; return 1; fi
  fprs=$(gpg --batch --show-keys --with-colons "$tmp/key.asc" 2>/dev/null | awk -F: '$1=="fpr"{print toupper($10)}')
  if ! printf '%s\n' "$fprs" | grep -qx "$RB24_KEY_FPR"; then
    err "AirNav's key does not have the expected fingerprint ($RB24_KEY_FPR): NOT installed, nothing added."
    err "AirNav may have changed its key: check lib/versions.sh against https://www.airnavradar.com/sharing-data"
    rm -rf "$tmp"; return 1
  fi
  install -d -m 755 "$(dirname "$keyring")" "$(dirname "$src")"
  if ! { gpg --batch --yes --dearmor -o "$tmp/key.gpg" "$tmp/key.asc" && install -m 644 "$tmp/key.gpg" "$keyring"; }; then
    rm -rf "$tmp"; err "AirNav's key could not be written to $keyring"; return 1
  fi
  rm -rf "$tmp"
  suite=$(sed -n -E 's/^VERSION_CODENAME="?([a-z]+)"?$/\1/p' "${ZB_OS_RELEASE:-/etc/os-release}" 2>/dev/null | head -1)   # read, never sourced
  printf 'deb [signed-by=%s] %s %s main\n' "$keyring" "$RB24_REPO_URL" "${suite:-$RB24_SUITE}" > "$src"
  if rb24_repo_broken && [ "${suite:-$RB24_SUITE}" != "$RB24_SUITE" ]; then
    log "AirNav's repository has no '$suite' suite: using '$RB24_SUITE', the one the community's container uses"
    printf 'deb [signed-by=%s] %s %s main\n' "$keyring" "$RB24_REPO_URL" "$RB24_SUITE" > "$src"
  fi
  if rb24_repo_broken; then
    err "apt refuses AirNav's repository on this system (see the line about rb24 in: sudo apt-get update)."
    err "It was taken away again; nothing was changed about signature checking."
    rm -f "$src" "$keyring"; apt-get update -qq >/dev/null 2>&1 || true
    return 1
  fi
}

# Its settings, every time it is installed (a wrong one is put right): the decoder's Beast port, the antenna, MLAT off.
rb24_write_ini() {
  local alt; alt=$(awk -v a="$(cfg_get ALT_M 0)" 'BEGIN { printf "%.0f", a }')
  ini_sec_set "$RB24_INI" client network_mode true
  ini_sec_set "$RB24_INI" client lat "$(cfg_get LAT)"
  ini_sec_set "$RB24_INI" client lon "$(cfg_get LON)"
  ini_sec_set "$RB24_INI" client alt "$alt"
  ini_sec_set "$RB24_INI" network mode beast
  ini_sec_set "$RB24_INI" network external_host 127.0.0.1
  ini_sec_set "$RB24_INI" network external_port 30005
  ini_sec_set "$RB24_INI" mlat autostart_mlat false
}
rb24_key() { local k; k=$(ini_sec_get "$RB24_INI" client key); [[ $k =~ ^[A-Za-z0-9]{8,64}$ ]] && printf '%s' "$k"; }
# The station's serial (EXTRPI...), which its page on AirNav's site is named by: rbfeeder prints it when the server
# accepts the key ("This is your station serial number: EXTRPI000000"); kept in config.env once seen (not a secret: the
# page is public). Read from this boot's journal only, which stays quick on a Pi 3.
rb24_station() {
  local s; s=$(cfg_get RADARBOX_STATION "")
  if [ -z "$s" ] && is_radarbox; then
    s=$(journalctl -u rbfeeder -b --no-pager -o cat 2>/dev/null | sed -n 's/.*station serial number: *\([A-Za-z0-9]\{6,20\}\).*/\1/p' | tail -1)
    [ -z "$s" ] || [ "$(id -u)" -ne 0 ] || cfg_set RADARBOX_STATION "$s"
  fi
  printf '%s' "$s"
}

install_radarbox() {
  local k
  log "Installing AirNav Radar (rbfeeder)"
  rb24_add_repo || return 1
  # as piaware: what AirNav only recommends (a decoder of its own among them) is not wanted beside readsb
  apt_install --no-install-recommends rbfeeder || { err "rbfeeder could not be installed from AirNav's repository."; return 1; }
  # 0.99.6: a key from a backup, or the one kept when it was removed, makes it the same station again: nothing to claim
  if [ -f "${BK_PENDING:-/nonexistent}/rb24key" ]; then bk_pending_apply radarbox
  elif [ -z "$(rb24_key)" ] && [[ $(cat "$(rb24_kept)" 2>/dev/null) =~ ^[A-Za-z0-9]{8,64}$ ]]; then
    ini_sec_set "$RB24_INI" client key "$(cat "$(rb24_kept)")" && rm -f "$(rb24_kept)" && echo "    AirNav Radar: the sharing key kept when it was removed is set again; the same station."
  fi
  rb24_write_ini
  systemctl enable rbfeeder 2>/dev/null || true
  systemctl restart rbfeeder || true
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12; do k=$(rb24_key); [ -n "$k" ] && break; [ "${ZB_SKIP_SERVICES:-}" = 1 ] && break; sleep 5; done   # a minute at most
  if [ -n "$k" ]; then
    log "AirNav Radar configured (Beast 127.0.0.1:30005, MLAT off)."
    # shown on this terminal only, never logged: the claim page asks for it
    printf '    Your sharing key:  %s   (kept in %s; a backup keeps it too)\n' "$k" "$RB24_INI" >&2
    rb24_claim_steps
  else
    warn "rbfeeder has not written its sharing key yet. In a minute, show it with:  sudo rbfeeder --showkey --no-start"
    rb24_claim_steps
  fi
}
# 0.99.7 (the owner, 30 October 2026): the claim, step by step, as AirNav's page asks it (read that day): an AirNav Radar
# account, then the key typed into the page's *Sharing Key* field. The key never goes into the address, and the claim
# does not depend on the public IP (0.99.6 said it did, wrongly)
rb24_claim_steps() {
  echo "    To link this station to your AirNav Radar account (once; nothing to do if it is yours already):"
  echo "      1. Sign in at https://www.airnavradar.com (a free account; ZenithBoard never creates it)."
  echo "      2. Open $RB24_CLAIM_URL"
  echo "      3. Paste the sharing key into the 'Sharing Key' field and press 'Claim!'."
  echo "    The key again, at any time:  sudo rbfeeder --showkey --no-start"
}
# its sharing key is the station: kept when it is removed (root only, not among a restore's waiting identities, which
# would tick it again in menu 1), so a station taken off and put back is the same one
rb24_kept() { echo "${BK_DATA:-$ZB_DATA}/radarbox-key-kept"; }
remove_radarbox() {
  local k; k=$(rb24_key)
  if [ -n "$k" ]; then mkdir -p "$(dirname "$(rb24_kept)")"; ( umask 077; printf '%s\n' "$k" > "$(rb24_kept)" ); fi
  systemctl disable --now rbfeeder 2>/dev/null || true
  apt_remove rbfeeder
  # what ZenithBoard added for it, and only that; a source of AirNav's own installer stays
  if [ -f "$(rb24_our_source)" ]; then rm -f "$(rb24_our_source)" "$(rb24_keyring)"; apt-get update -qq >/dev/null 2>&1 || true; fi
  cfg_del RADARBOX_STATION 2>/dev/null || true
}

# ------------------------------------------------------------------ menu 1
# shellcheck disable=SC2034  # ADSB_CANCELLED is read by start_here (lib/menus.sh)
adsb_menu() {
  local dec_now dec_sel feeders plan="" dev
  ADSB_CANCELLED=      # 0.54.5: Start here says "you left" for a screen backed out of, and "no internet" only for a real failure
  dec_now=$(installed_decoder)
  local rs="OFF" ds="OFF"
  case "${dec_now:-readsb}" in dump1090-fa) ds=ON ;; *) rs=ON ;; esac
  dec_sel=$(wt_radio "ADS-B decoder.\n\nreadsb is recommended (what ADSB Exchange, tar1090 and most feeders expect).\ndump1090-fa also works; every feeder reads the same Beast port 30005." \
      readsb "readsb (recommended)" "$rs" dump1090-fa "dump1090-fa (FlightAware)" "$ds") || { ADSB_CANCELLED=1; return 0; }

  dev=$(wt_input "ADS-B dongle serial number (or index).\nLeave empty if you have a single dongle.\nNeeded when a 2nd dongle is used for 978 MHz UAT." "$(cfg_get ADSB_SDR)") || { ADSB_CANCELLED=1; return 0; }
  cfg_set ADSB_SDR "$dev"

  local st_fa=OFF st_fr=OFF st_pf=OFF st_rb=OFF
  is_piaware && st_fa=ON; is_fr24 && st_fr=ON; is_planefinder && st_pf=ON; is_radarbox && st_rb=ON
  local st_axs=OFF; is_adsbx_stats && st_axs=ON
  # 0.54.5: after a restore on a new card, the networks the backup fed are ticked: their identities wait in restore-pending/
  # for exactly this step, and the list used to start with everything unticked, as if the backup had said nothing
  local pend="${BK_PENDING:-/nonexistent}" ticked=""
  [ -f "$pend/piaware-feeder-id" ] && { st_fa=ON; ticked=1; }
  [ -f "$pend/fr24key" ] && { st_fr=ON; ticked=1; }
  [ -f "$pend/pfclient-config.json" ] && { st_pf=ON; ticked=1; }
  [ -f "$pend/rb24key" ] && { st_rb=ON; ticked=1; }
  [ -f "${BK_DATA:-/nonexistent}/adsbx-stats-wanted" ] && { st_axs=ON; ticked=1; }      # a mark of its own: restore-pending/ must stay empty once the networks are in
  local -a items=(ADSBX "ADSB Exchange (mandatory)" ON ADSBX_STATS "ADSB Exchange stats: their map of your aircraft" "$st_axs" FLIGHTAWARE "FlightAware (piaware)" "$st_fa" FR24 "Flightradar24" "$st_fr" PLANEFINDER "Plane Finder" "$st_pf" RADARBOX "AirNav Radar (RadarBox)" "$st_rb")
  local st_uat=OFF
  is_uat978 && st_uat=ON
  # 978 MHz UAT is only used in the United States; a region that has it installed keeps seeing it so it can be removed
  if is_region_us || is_uat978; then items+=(UAT978 "978 MHz UAT (USA only, needs a 2nd dongle)" "$st_uat"); fi
  feeders=$(wt_check "Where do you want to share your data?\n\nADSB Exchange is mandatory (it owns the single MLAT client).\nUnchecking an installed feeder REMOVES it.${ticked:+\n\nTicked already: the networks your backup fed.}" "${items[@]}") || { ADSB_CANCELLED=1; return 0; }
  feeders=" ${feeders//\"/} ADSBX "

  [ "$dec_now" != "$dec_sel" ] && plan+="- Decoder: ${dec_now:-none} -> $dec_sel\n"
  is_adsbx || plan+="- Install ADSB Exchange\n"
  if [[ "$feeders" == *" ADSBX_STATS "* ]]; then is_adsbx_stats || plan+="- Install ADSB Exchange stats (every 5 s, the aircraft heard, to them)\n"
  elif is_adsbx_stats; then plan+="- REMOVE ADSB Exchange stats\n"
  elif [ -f "$AXS_STATE" ]; then plan+="- Finish removing ADSB Exchange stats (what an earlier attempt left)\n"; fi
  local pair f name checker
  for pair in "FLIGHTAWARE:is_piaware" "FR24:is_fr24" "PLANEFINDER:is_planefinder" "RADARBOX:is_radarbox"; do
    f=${pair%%:*}; checker=${pair##*:}
    if [[ "$feeders" == *" $f "* ]]; then $checker || plan+="- Install $f\n"
    else $checker && plan+="- REMOVE $f\n"; fi
  done
  if is_region_us || is_uat978; then
    if [[ "$feeders" == *" UAT978 "* ]]; then is_uat978 || plan+="- Install 978 MHz UAT (2nd dongle)\n"; else is_uat978 && plan+="- REMOVE 978 MHz UAT\n"; fi
  fi
  local n_extra=0; for f in FLIGHTAWARE FR24 PLANEFINDER RADARBOX; do [[ "$feeders" == *" $f "* ]] && n_extra=$((n_extra+1)); done
  if is_low_mem && [ "$n_extra" -gt 2 ]; then plan+="\nNOTE: $(mem_total_mb) MB RAM is low for $n_extra extra feeders: consider fewer.\n"; fi
  [ -z "$plan" ] && plan="Nothing to change. (Feeders and MLAT policy will simply be re-checked.)\n"
  wt_yesno "Planned changes:\n\n$plan\nContinue?" 18 || { ADSB_CANCELLED=1; return 0; }

  clear
  if [ "$dec_now" != "$dec_sel" ]; then
    [ -n "$dec_now" ] && remove_decoder
    install_decoder "$dec_sel" || {
      err "Decoder installation failed, so nothing else was installed: ADSB Exchange and the feeders need the decoder."
      err "Fix the cause (the line above says what failed: usually no internet) and come back to menu 1."
      read -rp "Press Enter to continue..." _; return 0; }
  else
    cfg_set DECODER "$dec_sel"
  fi
  is_adsbx || install_adsbx
  if [[ "$feeders" == *" ADSBX_STATS "* ]]; then
    is_adsbx_stats || { is_adsbx && adsbx_stats_on; } || warn "ADSB Exchange stats were not installed."
  elif is_adsbx_stats || [ -f "$AXS_STATE" ]; then
    adsbx_stats_off
  fi
  for pair in "FLIGHTAWARE:piaware" "FR24:fr24" "PLANEFINDER:planefinder" "RADARBOX:radarbox"; do
    f=${pair%%:*}; name=${pair##*:}
    if [[ "$feeders" == *" $f "* ]]; then
      case $name in piaware) is_piaware || install_piaware ;; fr24) is_fr24 || install_fr24 ;; planefinder) is_planefinder || install_planefinder ;;
        radarbox) is_radarbox || install_radarbox || warn "AirNav Radar was not installed (the lines above say why)." ;; esac
    else
      case $name in piaware) is_piaware && remove_piaware ;; fr24) is_fr24 && remove_fr24 ;; planefinder) is_planefinder && remove_planefinder ;;
        radarbox) is_radarbox && remove_radarbox ;; esac
    fi
  done
  if is_region_us || is_uat978; then
    if [[ "$feeders" == *" UAT978 "* ]]; then is_uat978 || install_uat978 || warn "978 MHz UAT was not installed."
    else is_uat978 && remove_uat978; fi
  fi
  zb_mlat_guard
  echo; log "ADSB step finished. Check everything with:  zenithboard status"
  rm -f "${BK_DATA:-/nonexistent}/adsbx-stats-wanted"; read -rp "Press Enter to continue..." _
}

# ------------------------------------------------------------------ position: update it EVERYWHERE it is stored
# Prints one line per place. "manual" lines are things only the provider's website can change.
_loc_line() { printf '  %-26s %s\n' "$1" "$2"; }

# The decoders' and feeders' own files; a test points them at a folder of its own (the audit of 22-23 October 2026:
# the sed of dump1090, ADSB Exchange's ALTITUDE and Plane Finder's JSON were never run by a test)
zb_apply_location() {  # zb_apply_location LAT LON [ALT_M]
  local lat="$1" lon="$2" alt="${3:-$(cfg_get ALT_M 0)}" dd="${ZB_DEFAULT_DIR:-/etc/default}"
  log "Applying position $lat, $lon, ${alt} m everywhere"
  cfg_set LAT "$lat"; cfg_set LON "$lon"; cfg_set ALT_M "$alt"
  _loc_line "ZenithBoard wall" "updated"; restart_flightinfo

  if is_readsb && command -v readsb-set-location >/dev/null; then
    readsb-set-location "$lat" "$lon" >/dev/null 2>&1 && systemctl restart readsb && _loc_line "readsb" "updated"
  fi
  if is_dump1090; then
    local f="$dd/dump1090-fa"
    sed -i -E 's/--lat [^" ]+ ?//; s/--lon [^" ]+ ?//' "$f"
    sed -i -E "s|^(DECODER_OPTIONS=\")|\1--lat $lat --lon $lon |" "$f"
    systemctl restart dump1090-fa && _loc_line "dump1090-fa" "updated"
  fi
  if is_adsbx; then
    local f="$dd/adsbexchange"
    if [ -f "$f" ] && grep -q '^LATITUDE=' "$f"; then
      ini_set "$f" LATITUDE "$lat"; ini_set "$f" LONGITUDE "$lon"; ini_set "$f" ALTITUDE "${alt}m"
      systemctl restart adsbexchange-feed adsbexchange-mlat 2>/dev/null
      _loc_line "ADSB Exchange (+MLAT)" "updated"
    else
      _loc_line "ADSB Exchange (+MLAT)" "MANUAL: /etc/default/adsbexchange not found; re-run the ADSB Exchange setup"
    fi
  fi
  if is_piaware; then
    _loc_line "FlightAware" "MANUAL: set it on https://flightaware.com/adsb/stats (My ADS-B -> your site)"
  fi
  if is_fr24; then
    _loc_line "Flightradar24" "MANUAL: edit your receiver on https://www.flightradar24.com (My data sharing)"
  fi
  if is_radarbox && [ -f "$RB24_INI" ]; then
    ini_sec_set "$RB24_INI" client lat "$lat"; ini_sec_set "$RB24_INI" client lon "$lon"
    ini_sec_set "$RB24_INI" client alt "$(awk -v a="$alt" 'BEGIN { printf "%.0f", a }')"
    systemctl restart rbfeeder 2>/dev/null; _loc_line "AirNav Radar" "updated"
  fi
  if is_planefinder; then
    local f="${ZB_PF_CONFIG:-/etc/pfclient-config.json}"
    if [ -f "$f" ] && command -v python3 >/dev/null && python3 - "$f" "$lat" "$lon" <<'PY'
import json, sys
f, lat, lon = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
d = json.load(open(f))
if "latitude" not in d:
    sys.exit(1)
d["latitude"], d["longitude"] = lat, lon
json.dump(d, open(f, "w"), indent=2)
PY
    then systemctl restart pfclient; _loc_line "Plane Finder" "updated"
    else _loc_line "Plane Finder" "MANUAL: open http://$(local_ip):30053 and change the position"; fi
  fi
}
