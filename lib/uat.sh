# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# 978 MHz UAT (United States only): a SECOND SDR dongle decoded by FlightAware's dump978-fa, with skyaware978
# writing /run/skyaware978/aircraft.json, which the FlightInfo wall merges with the 1090 MHz aircraft.
# Offered only when the region is "us". NOTE: written without access to a 978 MHz setup (the author lives in
# Europe): see docs/HARDWARE.md and the README "978 MHz" section.

is_region_us()  { [ "$(cfg_get REGION world)" = us ]; }
is_uat978()     { pkg_installed dump978-fa; }
UAT_DEFAULT_DIR="${ZB_DEFAULT_DIR:-/etc/default}"

# Put the dongle serial into the RECEIVER_OPTIONS line of /etc/default/dump978-fa (replacing any --sdr option).
uat978_set_sdr() {  # uat978_set_sdr SERIAL [FILE]
  local dev="$1" f="${2:-$UAT_DEFAULT_DIR/dump978-fa}"
  [ -n "$dev" ] || return 1
  [ -f "$f" ] || { warn "$f not found: set the dongle yourself with  --sdr driver=rtlsdr,serial=$dev  in RECEIVER_OPTIONS."; return 1; }
  sed -i -E 's/ ?--sdr [^" ]+//g' "$f"
  if grep -qE '^RECEIVER_OPTIONS="' "$f"; then
    sed -i -E "s|^(RECEIVER_OPTIONS=\")|\1--sdr driver=rtlsdr,serial=$dev |" "$f"
  else
    printf 'RECEIVER_OPTIONS="--sdr driver=rtlsdr,serial=%s"\n' "$dev" >> "$f"
  fi
}

uat978_ask_dongle() {   # prints the serial; non-zero if cancelled / invalid
  local dongles dev
  dongles=$(lsusb 2>/dev/null | grep -ci -E '0bda:(2832|2838)|rtl28|rtl-sdr') || true
  wt_msg "978 MHz UAT (United States) needs its OWN dongle and, ideally, a 978 MHz antenna: the 1090 MHz dongle cannot listen at 978 MHz.\n\nRTL-SDR dongles detected: ${dongles:-0}\n\nGive each dongle a unique serial number first (see docs/HARDWARE.md), e.g.:\n  rtl_eeprom -d 1 -s 00000978\nThen enter the 978 MHz dongle's serial on the next screen." 18 || return 1
  dev=$(wt_input "978 MHz dongle serial number." "$(cfg_get UAT_SDR)") || return 1
  [ -n "$dev" ] || { wt_msg "A dongle serial is required." 8; return 1; }
  if [ "$dev" = "$(cfg_get ADSB_SDR)" ] || [ "$dev" = "$(cfg_get ACARS_SDR)" ]; then
    wt_msg "That serial is already used for 1090 MHz ADS-B or ACARS. Pick a different dongle." 9; return 1
  fi
  printf '%s' "$dev"
}

install_uat978() {
  local dev
  dev=$(uat978_ask_dongle) || return 1
  log "Installing 978 MHz UAT (dump978-fa + skyaware978)"
  ensure_fa_repo || { err "Needs the FlightAware package repository."; return 1; }
  apt-get update -qq
  apt_install dump978-fa skyaware978 || return 1
  uat978_set_sdr "$dev" || true
  cfg_set UAT_SDR "$dev"; cfg_set UAT978 1
  systemctl enable dump978-fa skyaware978 2>/dev/null || true
  systemctl restart dump978-fa skyaware978 || true
  if is_piaware; then      # let FlightAware receive the 978 MHz data too (check it on your FlightAware stats page)
    piaware-config uat-receiver-type other >/dev/null 2>&1 || true
    piaware-config uat-receiver-host 127.0.0.1 >/dev/null 2>&1 || true
    piaware-config uat-receiver-port 30978 >/dev/null 2>&1 || true
    unit_active piaware && systemctl restart piaware || true
  fi
  restart_flightinfo
  echo "    978 MHz UAT is running. Aircraft show up on the wall next to the 1090 MHz ones. Check: sudo zenithboard status"
}

remove_uat978() {
  log "Removing 978 MHz UAT"
  systemctl disable --now skyaware978 dump978-fa 2>/dev/null || true
  apt_remove skyaware978 dump978-fa
  cfg_set UAT978 0
  restart_flightinfo
}
