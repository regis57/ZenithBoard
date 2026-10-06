# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck shell=bash
# Menu 1 - ADSB: decoder (readsb preferred, dump1090-fa fallback) + feeders.
#
# Architecture (identical for both decoders):
#   SDR dongle -> decoder -> Beast TCP on 127.0.0.1:30005 -> every feeder reads from there.
#   Exactly ONE MLAT client may run (it is ADSB Exchange's). FlightAware / FR24 MLAT are switched off.

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
  fetch "$FA_REPO_URL" /tmp/flightaware-apt-repository.deb || {
    warn "FlightAware may have moved its repository package: check lib/versions.sh against https://www.flightaware.com/adsb/piaware/install"
    return 1
  }
  dpkg -i /tmp/flightaware-apt-repository.deb && apt-get update
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
      fetch "$READSB_INSTALL_URL" /tmp/readsb-install.sh || return 1
      bash /tmp/readsb-install.sh || return 1
      command -v readsb-set-location >/dev/null && readsb-set-location "$lat" "$lon"
      set_sdr_serial_readsb "$dev"
      systemctl enable readsb; systemctl restart readsb
      ;;
    dump1090-fa)
      log "Installing dump1090-fa"
      ensure_fa_repo || return 1
      apt_install dump1090-fa || return 1
      local f=/etc/default/dump1090-fa
      sed -i -E 's/ ?--lat [^" ]+//; s/ ?--lon [^" ]+//' "$f"
      sed -i -E "s|^(DECODER_OPTIONS=\")|\1--lat $lat --lon $lon |" "$f"
      [ -n "$dev" ] && sed -i -E "s/--device-index [^\" ]+/--device-index $dev/" "$f"
      systemctl enable dump1090-fa; systemctl restart dump1090-fa
      ;;
    *) err "Unknown decoder $d"; return 1 ;;
  esac
  cfg_set DECODER "$d"
  restart_flightinfo
}

remove_decoder() {
  if is_readsb; then
    log "Removing readsb"
    fetch "$READSB_UNINSTALL_URL" /tmp/readsb-uninstall.sh && bash /tmp/readsb-uninstall.sh
  fi
  if is_dump1090; then log "Removing dump1090-fa"; apt_remove dump1090-fa; fi
}

# ------------------------------------------------------------------ feeders
install_adsbx() {
  log "Installing ADSB Exchange feeder (mandatory base layer, owns the single MLAT client)"
  echo "    The ADSB Exchange script will now ask for a station name and your position."
  echo "    Latitude/longitude: $(cfg_get LAT) / $(cfg_get LON)   Altitude: $(cfg_get ALT_M 0) m"
  fetch "$ADSBX_FEED_URL" /tmp/axfeed.sh || return 1
  bash /tmp/axfeed.sh
}
remove_adsbx() {
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
  echo "    Claim this receiver at https://flightaware.com/adsb/piaware/claim (same public IP as this Pi)."
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

install_fr24() {
  log "Installing Flightradar24 feeder"
  # a repository left by an earlier attempt: give it the new key first
  [ -z "$(fr24_source_file)" ] || fr24_repair_key || true
  fetch "$FR24_INSTALL_URL" /tmp/install_fr24.sh || return 1
  if ! bash /tmp/install_fr24.sh; then
    # the installer adds the repository and then stops when apt refuses it: repair the key, then finish the job
    [ -n "$(fr24_source_file)" ] || { err "The Flightradar24 installer failed before adding its repository."; return 1; }
    fr24_repair_key || return 1
    if fr24_repo_broken; then err "apt still refuses the Flightradar24 repository. Nothing was changed about signature checking."; return 1; fi
    apt_install fr24feed || return 1
    if command -v fr24feed >/dev/null 2>&1; then
      log "Finish the Flightradar24 sign-up (choose: Beast, 127.0.0.1, port 30005, MLAT = no)"
      fr24feed --signup || warn "Sign-up not finished: run it again with  sudo fr24feed --signup"
    fi
  fi
  if [ -f /etc/fr24feed.ini ]; then
    ini_set /etc/fr24feed.ini receiver beast-tcp
    ini_set /etc/fr24feed.ini host 127.0.0.1:30005
    ini_set /etc/fr24feed.ini mlat no
    ini_set /etc/fr24feed.ini mlat-without-gps no
    systemctl restart fr24feed || true
  else
    warn "/etc/fr24feed.ini not found: finish the FR24 sign-up with 'sudo fr24feed --signup' (choose Beast, 127.0.0.1:30005, MLAT = no)."
  fi
}
remove_fr24() { systemctl disable --now fr24feed 2>/dev/null || true; apt_remove fr24feed; }

install_planefinder() {
  local url deb=/tmp/pfclient.deb
  case "$(arch)" in arm64) url="$PF_URL_ARM64" ;; armhf) url="$PF_URL_ARMHF" ;; *) err "Plane Finder: unsupported architecture $(arch)"; return 1 ;; esac
  log "Installing Plane Finder client"
  fetch "$url" "$deb" || { warn "Check lib/versions.sh: the Plane Finder package URL may have changed."; return 1; }
  dpkg -i "$deb" || apt-get -f install -y
  systemctl enable pfclient; systemctl restart pfclient
  echo "    Finish setup at http://$(local_ip):30053  (data source: Beast, 127.0.0.1, port 30005)."
}
remove_planefinder() { systemctl disable --now pfclient 2>/dev/null || true; apt_remove pfclient; }

# ------------------------------------------------------------------ menu 1
adsb_menu() {
  local dec_now dec_sel feeders plan="" dev
  dec_now=$(installed_decoder)
  local rs="OFF" ds="OFF"
  case "${dec_now:-readsb}" in dump1090-fa) ds=ON ;; *) rs=ON ;; esac
  dec_sel=$(wt_radio "ADS-B decoder.\n\nreadsb is recommended (what ADSB Exchange, tar1090 and most feeders expect).\ndump1090-fa also works; every feeder reads the same Beast port 30005." \
      readsb "readsb (recommended)" "$rs" dump1090-fa "dump1090-fa (FlightAware)" "$ds") || return 0

  dev=$(wt_input "ADS-B dongle serial number (or index).\nLeave empty if you have a single dongle.\nNeeded when a 2nd dongle is used for ACARS." "$(cfg_get ADSB_SDR)") || return 0
  cfg_set ADSB_SDR "$dev"

  local st_fa=OFF st_fr=OFF st_pf=OFF
  is_piaware && st_fa=ON; is_fr24 && st_fr=ON; is_planefinder && st_pf=ON
  feeders=$(wt_check "Where do you want to share your data?\n\nADSB Exchange is mandatory (it owns the single MLAT client).\nUnchecking an installed feeder REMOVES it." \
      ADSBX "ADSB Exchange (mandatory)" ON \
      FLIGHTAWARE "FlightAware (piaware)" "$st_fa" \
      FR24 "Flightradar24" "$st_fr" \
      PLANEFINDER "Plane Finder" "$st_pf") || return 0
  feeders=" ${feeders//\"/} ADSBX "

  [ "$dec_now" != "$dec_sel" ] && plan+="- Decoder: ${dec_now:-none} -> $dec_sel\n"
  is_adsbx || plan+="- Install ADSB Exchange\n"
  local pair f name checker
  for pair in "FLIGHTAWARE:is_piaware" "FR24:is_fr24" "PLANEFINDER:is_planefinder"; do
    f=${pair%%:*}; checker=${pair##*:}
    if [[ "$feeders" == *" $f "* ]]; then $checker || plan+="- Install $f\n"
    else $checker && plan+="- REMOVE $f\n"; fi
  done
  local n_extra=0; for f in FLIGHTAWARE FR24 PLANEFINDER; do [[ "$feeders" == *" $f "* ]] && n_extra=$((n_extra+1)); done
  if is_low_mem && [ "$n_extra" -gt 2 ]; then plan+="\nNOTE: $(mem_total_mb) MB RAM is low for $n_extra extra feeders: consider fewer.\n"; fi
  [ -z "$plan" ] && plan="Nothing to change. (Feeders and MLAT policy will simply be re-checked.)\n"
  wt_yesno "Planned changes:\n\n$plan\nContinue?" 18 || return 0

  clear
  if [ "$dec_now" != "$dec_sel" ]; then
    [ -n "$dec_now" ] && remove_decoder
    install_decoder "$dec_sel" || { err "Decoder installation failed"; read -rp "Press Enter to continue..." _; return 0; }
  else
    cfg_set DECODER "$dec_sel"
  fi
  is_adsbx || install_adsbx
  for pair in "FLIGHTAWARE:piaware" "FR24:fr24" "PLANEFINDER:planefinder"; do
    f=${pair%%:*}; name=${pair##*:}
    if [[ "$feeders" == *" $f "* ]]; then
      case $name in piaware) is_piaware || install_piaware ;; fr24) is_fr24 || install_fr24 ;; planefinder) is_planefinder || install_planefinder ;; esac
    else
      case $name in piaware) is_piaware && remove_piaware ;; fr24) is_fr24 && remove_fr24 ;; planefinder) is_planefinder && remove_planefinder ;; esac
    fi
  done
  zb_mlat_guard
  echo; log "ADSB step finished. Check everything with:  zenithboard status"
  read -rp "Press Enter to return to the menu..." _
}

# ------------------------------------------------------------------ position: update it EVERYWHERE it is stored
# Prints one line per place. "manual" lines are things only the provider's website can change.
_loc_line() { printf '  %-26s %s\n' "$1" "$2"; }

zb_apply_location() {  # zb_apply_location LAT LON [ALT_M]
  local lat="$1" lon="$2" alt="${3:-$(cfg_get ALT_M 0)}"
  log "Applying position $lat, $lon, ${alt} m everywhere"
  cfg_set LAT "$lat"; cfg_set LON "$lon"; cfg_set ALT_M "$alt"
  _loc_line "ZenithBoard wall" "updated"; restart_flightinfo

  if is_readsb && command -v readsb-set-location >/dev/null; then
    readsb-set-location "$lat" "$lon" >/dev/null 2>&1 && systemctl restart readsb && _loc_line "readsb" "updated"
  fi
  if is_dump1090; then
    local f=/etc/default/dump1090-fa
    sed -i -E 's/ ?--lat [^" ]+//; s/ ?--lon [^" ]+//' "$f"
    sed -i -E "s|^(DECODER_OPTIONS=\")|\1--lat $lat --lon $lon |" "$f"
    systemctl restart dump1090-fa && _loc_line "dump1090-fa" "updated"
  fi
  if is_adsbx; then
    local f=/etc/default/adsbexchange
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
  if is_planefinder; then
    local f=/etc/pfclient-config.json
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
