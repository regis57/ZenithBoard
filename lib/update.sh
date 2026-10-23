# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Updating: ZenithBoard itself (git pull) and every component installed through it.
# Safe to run any time and as often as you like; your settings in /etc/zenithboard are never touched.

# Bring the download folder in line with GitHub. A normal update is a fast-forward; if the history was rewritten
# upstream (e.g. the author re-signed the commits) the folder is simply reset to GitHub's version, as long as you
# have not edited any tracked file in it.
# ------------------------------------------------------------------ trusting the code before running it
# `zenithboard update` pulls from GitHub and then runs install.sh as root. So the commit it is about to run is
# checked first: it must carry a good signature from the same key as last time. The first time, the key is shown
# and you say yes or no; after that it is silent unless something changes. Turn it off with UPDATE_VERIFY=0.
ZB_TRUST_DIR="${ZB_VAR_DIR:-/var/lib/zenithboard}/trust"
ZB_TRUST_FPR="$ZB_TRUST_DIR/signer.fpr"
ZB_TRUST_GPG="$ZB_TRUST_DIR/gnupg"

# Every unit file this Pi has is replaced by the repository's copy, whatever is being updated: an older
# unit left behind (one from before the sandboxes, say) would otherwise keep running as it was, and
# `zenithboard security` would keep pointing at it.
zb_refresh_units() {
  local f n changed=0 dir="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
  for f in "$ZB_HOME"/systemd/zenithboard-*.service "$ZB_HOME"/systemd/zenithboard-*.timer; do
    [ -f "$f" ] || continue
    n=$(basename "$f")
    [ -f "$dir/$n" ] || continue
    cmp -s "$f" "$dir/$n" && continue
    install -m 644 "$f" "$dir/$n" && changed=1
  done
  [ "$changed" = 0 ] || systemctl daemon-reload 2>/dev/null || true
}

zb_trust_stored() { cat "$ZB_TRUST_FPR" 2>/dev/null; }      # one fingerprint per line

# zb_verify_decide STATUS SIGNER STORED -> ok | bad | unknown     (STATUS is git's %G?; STORED: one per line)
# "ok" only for a good signature made by one of the keys we recorded. Separated out so it can be tested.
# GitHub's key file holds more than one key (it rotated its key in 2024 and still publishes the old one), so
# what is recorded is a list, not one fingerprint.
zb_verify_decide() {
  local st="$1" signer="$2" stored="$3"
  case "$st" in
    B) echo bad; return ;;                                     # a bad signature is never a question
    G|U)                                                        # good now (X/Y = expired: not good enough)
      if [ -n "$signer" ] && grep -qixF -- "$signer" <<<"$stored"; then echo ok; else echo unknown; fi ;;
    *) echo unknown ;;                                         # N: not signed at all, E: could not be checked
  esac
}

# The keys in a key file: "FINGERPRINT STATE EXPIRY UID" per key. STATE is gpg's validity letter: e = expired,
# r = revoked. Only keys that are neither are offered for trust.
zb_keys_in() {
  GNUPGHOME="$ZB_TRUST_GPG" gpg --batch --show-keys --with-colons "$1" 2>/dev/null | awk -F: '
    $1=="pub" { st=$2; ex=$7; fpr=""; uid=""; want=1; next }
    $1=="fpr" && want { fpr=$10; want=0; next }
    $1=="uid" && fpr!="" && uid=="" { uid=$10; print fpr, (st==""?"-":st), (ex==""?"never":ex), uid }'
}

# zb_signature STATUS: "LETTER FINGERPRINT" of the commit REF in DIR
zb_signature() {
  local dir="$1" ref="$2"
  GNUPGHOME="$ZB_TRUST_GPG" git -c "safe.directory=$dir" -C "$dir" log -1 --format='%G? %GF' "$ref" 2>/dev/null
}

# First time: fetch the key, show it, ask. Records the fingerprint only if you say yes.
zb_trust_setup() {
  local tmp
  command -v gpg >/dev/null 2>&1 || { warn "gpg is not installed: the update cannot be checked."; return 1; }
  tmp=$(zb_tmp github-signing.gpg) || return 1
  fetch "$GITHUB_SIGNING_KEY_URL" "$tmp" || return 1
  install -d -m 700 "$ZB_TRUST_DIR" "$ZB_TRUST_GPG"
  local keys usable fpr st uid
  keys=$(zb_keys_in "$tmp")
  [ -n "$keys" ] || { warn "That key file could not be read."; return 1; }
  usable=""
  echo
  echo "ZenithBoard is about to trust the keys GitHub signs its releases with:"
  while read -r fpr st _ uid; do
    case "$st" in
      e) echo "    $fpr   (expired, will NOT be trusted)   $uid" ;;
      r) echo "    $fpr   (revoked, will NOT be trusted)   $uid" ;;
      *) echo "    $fpr   $uid"; usable="$usable$fpr"$'\n' ;;
    esac
  done <<<"$keys"
  [ -n "$usable" ] || { warn "None of those keys can be used."; return 1; }
  echo "On GitHub, click the Verified badge beside a commit at"
  echo "    https://github.com/regis57/ZenithBoard/commits/main"
  echo "It shows a key ID: it must be the LAST 16 characters of one of the lines above."
  if [ -t 0 ]; then
    read -rp "Trust these keys for future updates? [y/N] " a
    case "$a" in y|Y|o|O) ;; *) echo "Not trusted. The update will ask again."; return 1 ;; esac
  else
    warn "Nothing to answer here (not a terminal): run the update by hand once to confirm the key."
    return 1
  fi
  GNUPGHOME="$ZB_TRUST_GPG" gpg --batch --quiet --import "$tmp" || return 1
  printf '%s' "$usable" > "$ZB_TRUST_FPR"; chmod 600 "$ZB_TRUST_FPR"
  log "Keys recorded. Future updates are checked against them."
}

# -> 0 continue, 1 stop
zb_verify_source() {
  local dir="$1" ref="$2" st signer stored verdict a
  [ "$(cfg_get UPDATE_VERIFY 1)" = 1 ] || return 0
  stored=$(zb_trust_stored)
  [ -n "$stored" ] || zb_trust_setup || true
  stored=$(zb_trust_stored)
  read -r st signer <<<"$(zb_signature "$dir" "$ref")"
  verdict=$(zb_verify_decide "${st:-N}" "${signer:-}" "$stored")
  # 0.12.0 and 0.12.1 recorded only the FIRST key of GitHub's file, which is its old, expired key. The current
  # one was imported in the same step you approved, but not recorded. Offer it once, and only that case.
  if [ "$verdict" = unknown ] && [ -n "$stored" ] && { [ "$st" = G ] || [ "$st" = U ]; } && [ -n "$signer" ] \
     && GNUPGHOME="$ZB_TRUST_GPG" gpg --batch --list-keys "$signer" >/dev/null 2>&1; then
    warn "This update is signed by $signer."
    warn "That key came in the same file from GitHub you approved earlier, but only the first key of that file"
    warn "was recorded (a mistake in ZenithBoard 0.12.0 and 0.12.1). Check: GitHub's Verified badge shows its"
    warn "key ID, which must be the last 16 characters above."
    if [ -t 0 ]; then
      read -rp "Trust this key too, from now on? [y/N] " a
      case "$a" in
        y|Y|o|O) printf '%s\n' "$signer" >> "$ZB_TRUST_FPR"; log "Key added. Future updates are checked silently."; return 0 ;;
      esac
    fi
  fi
  case "$verdict" in
    ok) return 0 ;;
    bad)
      err "The signature on the code GitHub just sent is BAD. Nothing was installed."
      err "This is not a normal failure. Do not force it: ask on the project page first."
      return 1 ;;
    *)
      warn "This update could not be shown to come from the usual signing key."
      case "${st:-N}" in
        N) warn "Reason: the commit is not signed." ;;
        E) warn "Reason: the signature could not be checked (the key is missing here)." ;;
        *) warn "Reason: signed by $signer, which is not the key recorded on this Pi ($stored)." ;;
      esac
      warn "That happens for an honest reason too: your own commits, a fork, or a new signing key."
      if [ -t 0 ]; then
        read -rp "Install it anyway? [y/N] " a
        case "$a" in y|Y|o|O) return 0 ;; *) echo "Stopped. Nothing was installed."; return 1 ;; esac
      fi
      warn "Nothing to answer here (not a terminal), so it was NOT installed. Run the update by hand to decide."
      return 1 ;;
  esac
}

zb_sync_source() {  # zb_sync_source DIR
  local dir="$1" owner rc=0
  owner=$(stat -c '%u:%g' "$dir" 2>/dev/null)
  _zb_sync_source "$dir" || rc=$?
  # git ran as root: give the folder back to its owner, otherwise the owner's own `git fetch` fails with "Permission denied"
  [ -z "$owner" ] || chown -R "$owner" "$dir" 2>/dev/null || true
  return "$rc"
}

_zb_sync_source() {
  local dir="$1" branch
  local -a g=(git -c "safe.directory=$dir" -C "$dir")
  branch=$("${g[@]}" rev-parse --abbrev-ref HEAD 2>/dev/null) || return 1
  "${g[@]}" fetch -q origin "$branch" || { warn "Could not reach GitHub."; return 1; }
  zb_verify_source "$dir" "origin/$branch" || return 1      # checked before anything is merged or run
  "${g[@]}" merge --ff-only -q "origin/$branch" >/dev/null 2>&1 && return 0
  if [ -n "$("${g[@]}" status --porcelain --untracked-files=no)" ]; then
    warn "You changed files in $dir, so it was not updated. Undo with: git -C $dir checkout . (then update again)"
    return 1
  fi
  log "GitHub's history was rewritten (for example commits were re-signed): resynchronising $dir"
  "${g[@]}" reset -q --hard "origin/$branch"
}

# Components that can be updated one by one (the name is what `zenithboard update only NAME...` and the menu use).
ZB_COMPONENTS="zenithboard readsb dump1090 adsbx piaware fr24 planefinder flightinfo graphs1090"
zb_component_label() {
  case "$1" in
    zenithboard) echo "ZenithBoard itself (installer, menu, wall code)" ;;
    readsb) echo "readsb decoder" ;;
    dump1090) echo "dump1090-fa decoder" ;;
    adsbx) echo "ADSB Exchange feeder + MLAT" ;;
    piaware) echo "FlightAware (piaware)" ;;
    fr24) echo "Flightradar24 (fr24feed)" ;;
    planefinder) echo "Plane Finder" ;;
    flightinfo) echo "FlightInfo wall + aircraft data" ;;
    graphs1090) echo "graphs1090 (the decoder's graphs)" ;;
  esac
}
zb_component_installed() {
  case "$1" in
    zenithboard) return 0 ;;
    readsb) is_readsb ;; dump1090) is_dump1090 ;; adsbx) is_adsbx ;; piaware) is_piaware ;;
    fr24) is_fr24 ;; planefinder) is_planefinder ;; flightinfo) is_flightinfo ;; graphs1090) is_graphs ;;
    *) return 1 ;;
  esac
}
zb_component_version() {   # a short version when it is cheap to know, else nothing
  local v=""
  case "$1" in
    zenithboard) v="$ZB_VERSION" ;;
    readsb) v=$(readsb --version 2>&1 | head -1 | grep -oE '[0-9][0-9A-Za-z.+~-]*' | head -1) ;;
    dump1090) v=$(dpkg-query -W -f='${Version}' dump1090-fa 2>/dev/null) ;;
    piaware) v=$(dpkg-query -W -f='${Version}' piaware 2>/dev/null) ;;
    fr24) v=$(dpkg-query -W -f='${Version}' fr24feed 2>/dev/null) ;;
    graphs1090) v=$(graphs_version) ;;
  esac
  printf '%s' "$v"
}
zb_update_list() {   # what is installed, and what `update only` accepts
  local c v
  for c in $ZB_COMPONENTS; do
    zb_component_installed "$c" || continue
    v=$(zb_component_version "$c")
    printf '  %-12s %s%s\n' "$c" "$(zb_component_label "$c")" "${v:+  ($v)}"
  done
}

# zb_update [--no-pull] [--only NAME...]
#   no arguments : everything installed (ZenithBoard code, then every component)
#   --only NAMES : just those (name "zenithboard" = the ZenithBoard code itself; without it the code is not pulled)
zb_update() {
  local src="" old="$ZB_VERSION" pull=1 only=0 c names=()
  while [ $# -gt 0 ]; do
    case "$1" in
      --no-pull) pull=0 ;;
      --only) only=1; pull=0 ;;
      "") ;;
      *) names+=("$1") ;;
    esac; shift
  done
  if [ "$only" = 1 ]; then
    for c in "${names[@]}"; do
      case " $ZB_COMPONENTS " in *" $c "*) ;; *) err "Unknown component: $c. Choose from: $ZB_COMPONENTS"; return 1 ;; esac
      zb_component_installed "$c" || { err "$c is not installed (see: zenithboard update list)"; return 1; }
      [ "$c" != zenithboard ] || pull=1
    done
  fi
  [ -f "$ZB_HOME/.source" ] && src=$(cat "$ZB_HOME/.source")
  if [ "$pull" = 1 ] && [ -n "$src" ] && [ -d "$src/.git" ]; then
    log "Updating ZenithBoard from GitHub ($src), current version $old"
    zb_sync_source "$src" || { warn "The ZenithBoard code was NOT updated: staying on version $old."; export ZB_CODE_NOT_UPDATED="$old"; }
    bash "$src/install.sh" --deploy                      # copy the new files to /opt/zenithboard
  elif [ "$pull" = 1 ]; then
    warn "Original download folder not found: skipping the ZenithBoard code update (git clone it again to get the newest version)."
    export ZB_CODE_NOT_UPDATED="$old"
  fi
  if [ "$only" = 1 ]; then
    local rest=(); for c in "${names[@]}"; do [ "$c" = zenithboard ] || rest+=("$c"); done
    exec "$ZB_HOME/bin/zenithboard" update-components --only "${rest[@]}"
  fi
  exec "$ZB_HOME/bin/zenithboard" update-components      # run the freshly deployed code
}

# zb_update_components [--only NAME...]   (no arguments = every installed component)
zb_update_components() {
  local only=0 rb ax; [ "${1:-}" = "--only" ] && { only=1; shift; }
  local sel=("$@")
  want_c() { if [ "$only" = 0 ]; then return 0; fi; local x; for x in "${sel[@]}"; do [ "$x" = "$1" ] && return 0; done; return 1; }
  log "ZenithBoard $ZB_VERSION: updating installed components"
  ! want_c fr24 || [ -z "$(fr24_source_file)" ] || fr24_repair_key || warn "Flightradar24 signing key not refreshed (see above)."
  apt-get update -qq
  if want_c readsb && is_readsb; then
    log "readsb"; rb=$(zb_tmp readsb-install.sh) && fetch "$READSB_INSTALL_URL" "$rb" && bash "$rb" || warn "readsb update failed"
  fi
  want_c dump1090 && is_dump1090 && { log "dump1090-fa"; apt_install --only-upgrade dump1090-fa || warn "dump1090-fa update failed"; }
  if want_c adsbx && is_adsbx; then
    log "ADSB Exchange"; ax=$(zb_tmp axupdate.sh) && fetch "$ADSBX_UPDATE_URL" "$ax" && bash "$ax" || warn "ADSB Exchange update failed"
    if is_adsbx_stats; then log "ADSB Exchange stats"; adsbx_stats_update; fi
  fi
  want_c piaware && is_piaware && { log "piaware"; apt_install --only-upgrade piaware || warn "piaware update failed"; }
  want_c fr24 && is_fr24 && { log "fr24feed"; apt_install --only-upgrade fr24feed || warn "fr24feed update failed"; }
  if want_c planefinder && is_planefinder; then
    log "Plane Finder"; install_planefinder || warn "Plane Finder update failed (check lib/versions.sh)"
  fi
  if want_c flightinfo && is_flightinfo; then
    log "FlightInfo"; ensure_zb_user          # also repairs the folder modes of older installs
    systemctl daemon-reload; install -m 644 "$ZB_HOME/systemd/zenithboard-flightinfo.service" /etc/systemd/system/; systemctl daemon-reload; restart_flightinfo
    graphs_look_keep      # 0.53.8: graphs1090's page keeps its own copy of the catalogues and the language list; `update quick` left it on the old ones
    data_refresh_apply
    [ "$(cfg_get AUTO_DATA_REFRESH 1)" != 1 ] || data_refresh_now || warn "aircraft data refresh failed (kept the previous data)"
  fi
  if want_c graphs1090 && is_graphs; then log "graphs1090"; graphs_update; fi
  acars_notice      # 0.30.0: ACARS and Grafana left by an older version are said, never removed by an update

  zb_refresh_units
  if [ -f /etc/systemd/system/zenithboard-wifi.service ]; then wifi_install_unit; fi
  if [ "$(cfg_get DDNS_PROVIDER none)" != none ]; then ddns_install_units; fi
  if [ "$(cfg_get LOG_AUTOCLEAN 0)" = 1 ]; then logs_auto_on; fi
  if [ "$(cfg_get NETWATCH 0)" = 1 ]; then netwatch_install_units; fi
  if [ "$(cfg_get GAINLOG 0)" = 1 ]; then gain_log_install_units; fi
  if [ "$(cfg_get STATS 0)" = 1 ]; then stats_install_units; fi
  if [ "$(cfg_get CONSOLE 0)" = 1 ]; then console_prepare_dirs; console_install_units; fi
  zb_retired_colours
  social_migrate
  if [ "$(cfg_get SOCIAL 0)" = 1 ]; then social_install_units; fi
  zb_mlat_guard
  zb_wall_check
  zb_update_verdict
}

# 0.53.7: an update whose code pull failed used to end "Update finished", exit 0, and the console toasted "done": the
# first screen after it was the old version. The components were still updated, so it says that, and exits 1.
zb_update_verdict() {
  if [ -n "${ZB_CODE_NOT_UPDATED:-}" ]; then
    warn "Update NOT complete: the components were updated, but the ZenithBoard code was not (still version $ZB_CODE_NOT_UPDATED). Read what is said above, fix it, and run the update again."
    return 1
  fi
  log "Update finished. Check:  zenithboard status"
}

# 0.23.0: the dark blue (#0404e2) is gone from the wall and the posts. A setting the owner made is never changed by
# an update: the wall shows amber meanwhile (the server and the tablet fall back by themselves), and the update says
# so with the command. The same for a preset that carries it.
zb_retired_colours() {
  local p n v
  if [ "$(cfg_get THEME amber)" = blue ]; then
    warn "The wall's colour is set to blue, which was taken out in 0.23.0: the wall shows amber meanwhile. Choose one:  sudo zenithboard color turquoise  (or amber, green, red, white)"
  fi
  # the command given is the whole preset with turquoise in place of blue: "preset add" replaces a preset, so a
  # command with theme=turquoise alone would drop its other settings
  for p in $(grep -E '^PRESET_[A-Z0-9]+="?([^"]* )?theme=blue( |"|$)' "$ZB_CONFIG" 2>/dev/null | cut -d= -f1); do
    n=$(printf '%s' "${p#PRESET_}" | tr '[:upper:]' '[:lower:]')
    v=$(cfg_get "$p" "" | sed -E ':a; s/(^| )theme=blue( |$)/\1theme=turquoise\2/; ta')
    warn "The preset $n sets theme=blue, taken out in 0.23.0: that tablet shows the wall's colour meanwhile. Set it again (turquoise, or another colour):  sudo zenithboard preset add $n $v"
  done
  return 0
}

# The wall server is a running python process: new files on disk change nothing until it is restarted. An update
# that did not pass through the FlightInfo step therefore left the wall answering the old version while the menu
# already showed the new one (seen on a real Pi: menu 0.17.2, gear panel 0.17.1, after `update only zenithboard`).
# Rather than trusting the flow to have restarted it, ask the wall what it is running and put it right if it is not
# the version that is now installed. The wall answers on the loopback, so this says nothing to anyone outside.
zb_wall_version() {
  local port; port=$(cfg_get PORT 8080)
  curl -fsS --max-time 5 "http://127.0.0.1:${port}/api/config" 2>/dev/null |
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("version",""))' 2>/dev/null
}

zb_wall_check() {
  is_flightinfo || return 0
  local v; v=$(zb_wall_version)
  [ "$v" != "$ZB_VERSION" ] || { log "Wall: running $v"; return 0; }
  if [ -z "$v" ]; then
    warn "The wall did not answer on port $(cfg_get PORT 8080): check  zenithboard logs flightinfo"
    return 0
  fi
  log "The wall is still running $v: restarting it on $ZB_VERSION"
  restart_flightinfo
  sleep 2
  v=$(zb_wall_version)
  [ "$v" = "$ZB_VERSION" ] && log "Wall: running $v" ||
    warn "The wall answers $v, not $ZB_VERSION. Try:  sudo systemctl restart zenithboard-flightinfo"
}

# This menu is a running script: after an update it still holds the OLD code in memory. Start it again so the very next
# screen is the new version (the same menu, freshly loaded). Starting again is only possible from the real installer.
update_menu_reload() {
  read -rp "Press Enter to reopen the menu on the new version..." _
  local me="${ROOT:-$ZB_HOME}/install.sh"
  [ -x "$me" ] && exec "$me"
  return 0
}

# Menu 5 Updates: ZenithBoard alone, everything, or picked components; and Debian's daily security fixes (0.44.0:
# moved here from Reliability, an update being what they are).
update_menu() {
  local c items=() sel x names=()
  while true; do
    c=$(wt_menu "Updates\n\nZenithBoard $ZB_VERSION. Your settings are never touched: an update says so when one of them should change." \
      quick "1  ZenithBoard and the wall only, in seconds" \
      all "2  Everything: ZenithBoard, decoder, feeders (minutes)" \
      pick "3  Choose what to update (tick them)" \
      list "4  What is installed, and its version" \
      patches "5  Debian's security fixes, daily by themselves: $(patches_state)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      quick) clear; "$ZB_HOME/bin/zenithboard" update quick; update_menu_reload ;;
      all) clear; "$ZB_HOME/bin/zenithboard" update; update_menu_reload ;;
      list) clear; zb_update_list; echo; read -rp "Press Enter..." _ ;;
      patches)
        if [ "$(patches_state)" = on ]; then wt_yesno "Debian security patches are ON.\n\nTurn them OFF?" 8 && { clear; patches_off; read -rp "Press Enter to continue..." _; }
        else wt_yesno "Install Debian's security fixes by themselves, once a day?\n\nOnly the Debian security channel: openssl, the kernel, curl, python and the like. The ADS-B feeders come from other repositories and are never touched, and the Pi is never rebooted by it. ZenithBoard and the feeders still move only with 'zenithboard update'." 14 && { clear; patches_on; read -rp "Press Enter to continue..." _; }; fi ;;

      pick)
        items=(); for x in $ZB_COMPONENTS; do
          zb_component_installed "$x" || continue
          items+=("$x" "$(zb_component_label "$x")$( v=$(zb_component_version "$x"); [ -n "$v" ] && printf '  (%s)' "$v")" OFF)
        done
        sel=$(whiptail --title "$WT_TITLE" --checklist "Tick what to update (Space = tick, Enter = go).\nNothing ticked = nothing happens." 20 76 10 "${items[@]}" 3>&1 1>&2 2>&3) || continue
        eval "names=($sel)"
        [ "${#names[@]}" -gt 0 ] || { wt_msg "Nothing ticked, nothing updated." 7; continue; }
        clear; "$ZB_HOME/bin/zenithboard" update only "${names[@]}"; update_menu_reload ;;
      *) return 0 ;;
    esac
  done
}
