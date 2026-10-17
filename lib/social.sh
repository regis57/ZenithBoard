# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Social sharing (menu 4 Settings -> 6 Social sharing, and `zenithboard social ...`).
#
# Posts the aircraft overhead to Bluesky and/or Mastodon as a picture of the wall, with a short text. Off by
# default. The work is done by flightinfo/social.py, running as a service under the wall's user; this file is the
# setup wizard, the switch, and the commands. The picture is drawn by tools/social-render.js, which needs Node,
# installed from Debian when sharing is switched on (about 30 MB; the only thing the feature adds to the Pi).
#
# Secrets (a Bluesky app password, a Mastodon access token) live in $ZB_ETC/social.env, owned by root, readable by
# the zenithboard group (the service runs as that user), mode 0640. Never in config.env, never in a log, never
# shown by `zenithboard config`. `social remove` deletes that file.
SOCIAL_SECRETS="${ZENITHBOARD_SOCIAL_SECRETS:-${ZB_ETC:-/etc/zenithboard}/social.env}"
SOCIAL_DIR="${ZENITHBOARD_SOCIAL_DIR:-/var/lib/zenithboard/social}"
SOCIAL_UNIT=zenithboard-social
SOCIAL_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
SOCIAL_PY="$ZB_HOME/flightinfo/social.py"

social_state() { [ "$(cfg_get SOCIAL 0)" = 1 ] && echo on || echo off; }
social_networks() { cfg_get SOCIAL_NETWORKS ""; }

# ---- the service
social_install_units() {
  [ -f "$ZB_HOME/systemd/$SOCIAL_UNIT.service" ] || return 0
  install -d -m 755 "$SOCIAL_UNIT_DIR"
  install -m 644 "$ZB_HOME/systemd/$SOCIAL_UNIT.service" "$SOCIAL_UNIT_DIR/"
  systemctl daemon-reload; systemctl enable --now "$SOCIAL_UNIT.service" >/dev/null 2>&1 || true
}
social_remove_units() {
  systemctl disable --now "$SOCIAL_UNIT.service" >/dev/null 2>&1 || true
  rm -f "$SOCIAL_UNIT_DIR/$SOCIAL_UNIT.service"; systemctl daemon-reload 2>/dev/null || true
}
social_prepare_dir() {
  [ -d "$SOCIAL_DIR" ] || install -d -m 750 "$SOCIAL_DIR" 2>/dev/null || return 1
  [ "$(id -u)" -ne 0 ] || chown "$ZB_USER:$ZB_USER" "$SOCIAL_DIR" 2>/dev/null || true
  # the picture's folder in /run: systemd makes it for the service; `test` and `post` from the command line need it too
  [ "$(id -u)" -ne 0 ] || install -d -m 700 -o "$ZB_USER" -g "$ZB_USER" "${ZENITHBOARD_SOCIAL_RUN:-/run/zenithboard/social}" 2>/dev/null || true
}
social_need_node() {
  command -v node >/dev/null 2>&1 && return 0
  log "Installing Node (draws the picture; about 30 MB)"
  apt_install nodejs >/dev/null || { err "Node could not be installed: the picture cannot be drawn without it."; return 1; }
}

# ---- the secrets file: written whole, never appended to, never world-readable
social_secret_get() { [ -r "$SOCIAL_SECRETS" ] || return 0; sed -n -E "s/^$1=\"?([^\"]*)\"?$/\1/p" "$SOCIAL_SECRETS" | head -1; }
social_secrets_write() {   # social_secrets_write KEY=VALUE...  (every key; what is not given is dropped)
  local old tmp
  old=$(umask); umask 077
  tmp=$(mktemp "${SOCIAL_SECRETS}.XXXXXX") || { umask "$old"; return 1; }
  printf '# ZenithBoard social sharing: account secrets. root:%s, mode 0640. Never in config.env, never in a log.\n' "$ZB_USER" > "$tmp"
  printf '%s\n' "$@" | sed -E 's/^([A-Z_]+)=(.*)$/\1="\2"/' >> "$tmp"
  umask "$old"
  chown "root:$ZB_USER" "$tmp" 2>/dev/null || true; chmod 640 "$tmp"
  mv "$tmp" "$SOCIAL_SECRETS"
}
social_valid_handle() { [[ $1 =~ ^[a-z0-9][a-z0-9.-]{2,}\.[a-z]{2,}$ ]]; }
social_valid_url() { [[ $1 =~ ^https://[a-z0-9.-]+(:[0-9]+)?/?$ ]]; }

# ---- the wizard. Asks only what each network needs, tries the account before saving anything else.
social_setup() {
  local net handle pw url tok have_b have_m keep=() chosen=() r
  have_b=$(social_secret_get BLUESKY_HANDLE); have_m=$(social_secret_get MASTODON_URL)
  net=$(whiptail --title "$WT_TITLE" --checklist "Share the aircraft overhead on which networks? (Space = tick, Enter = go)\n\nEach needs one secret you create on the network's own site; the next screens say where. Nothing is posted until you switch sharing on." 16 76 2 \
      bluesky "Bluesky  (an app password)" "$( [ -n "$have_b" ] && echo ON || echo OFF )" \
      mastodon "Mastodon (an access token)" "$( [ -n "$have_m" ] && echo ON || echo OFF )" 3>&1 1>&2 2>&3) || return 1
  net=${net//\"/}
  if [[ " $net " == *" bluesky "* ]]; then
    handle=$(wt_input "Bluesky handle, without @ (for example zenithboard.bsky.social)." "${have_b}") || return 1
    handle=${handle#@}; handle=$(echo "$handle" | tr '[:upper:]' '[:lower:]')
    social_valid_handle "$handle" || { wt_msg "That does not look like a Bluesky handle: $handle" 8; return 1; }
    pw=$(whiptail --title "$WT_TITLE" --passwordbox "Bluesky APP password for that account (not your real password).\n\nMake one at bsky.app: Settings -> Privacy and Security -> App Passwords -> Add App Password. It looks like xxxx-xxxx-xxxx-xxxx and is shown once." 14 76 3>&1 1>&2 2>&3) || return 1
    [ -n "$pw" ] || pw=$(social_secret_get BLUESKY_APP_PASSWORD)
    [ -n "$pw" ] || { wt_msg "No app password given." 7; return 1; }
    keep+=("BLUESKY_HANDLE=$handle" "BLUESKY_APP_PASSWORD=$pw"); chosen+=(bluesky)
  fi
  if [[ " $net " == *" mastodon "* ]]; then
    url=$(wt_input "Your Mastodon instance, with https:// (for example https://mastodon.social)." "${have_m:-https://mastodon.social}") || return 1
    url=${url%/}
    social_valid_url "$url" || { wt_msg "That does not look like an instance address: $url" 8; return 1; }
    tok=$(whiptail --title "$WT_TITLE" --passwordbox "Mastodon access token.\n\nOn your instance: Preferences -> Development -> New application. Name it ZenithBoard, tick only write:media and write:statuses, save, open it and copy 'Your access token'." 14 76 3>&1 1>&2 2>&3) || return 1
    [ -n "$tok" ] || tok=$(social_secret_get MASTODON_TOKEN)
    [ -n "$tok" ] || { wt_msg "No token given." 7; return 1; }
    keep+=("MASTODON_URL=$url" "MASTODON_TOKEN=$tok"); chosen+=(mastodon)
  fi
  [ "${#chosen[@]}" -gt 0 ] || { wt_msg "Nothing chosen, nothing changed." 7; return 1; }
  social_secrets_write "${keep[@]}" || { wt_msg "Could not write $SOCIAL_SECRETS" 8; return 1; }
  cfg_set SOCIAL_NETWORKS "$(IFS=,; echo "${chosen[*]}")"
  clear; echo "Trying the accounts..."; echo
  r=$(python3 "$SOCIAL_PY" check 2>&1); echo "$r"; echo
  if echo "$r" | grep -q FAILED; then
    echo "At least one account refused. The secrets are saved; fix them with  sudo zenithboard social setup  and try again."
    read -rp "Press Enter to continue..." _; return 1
  fi
  social_setup_words
}

# The words of the posts: the area named in them (the owner's words, never derived from the antenna's position),
# the radius, the gap, the rules.
social_setup_words() {
  local area radius gap rules
  area=$(wt_input "Where is this, in two or three words, as the posts should say it? A town name (Trémery) reads \"above Trémery\"; your own words (near Metz) are kept.\nLeave empty for no place at all. The receiver's position is never used." "$(cfg_get SOCIAL_AREA "")") || return 1
  cfg_set SOCIAL_AREA "$area"
  radius=$(wt_input "Sharing radius in km: an aircraft is a candidate while it is inside it. This is separate from the wall's radius." "$(cfg_get SOCIAL_RADIUS_KM 15)") || return 1
  is_number "$radius" && cfg_set SOCIAL_RADIUS_KM "$radius"
  gap=$(wt_input "Minimum minutes between two posts (so the account is not flooded)." "$(cfg_get SOCIAL_GAP_MIN 120)") || return 1
  is_number "$gap" && cfg_set SOCIAL_GAP_MIN "$gap"
  rules=$(whiptail --title "$WT_TITLE" --checklist "Post an aircraft when it is... (Space = tick)" 16 76 6 \
      rare "a type seen twice or less in thirty days" "$(social_rule_on rare)" \
      military "military" "$(social_rule_on military)" \
      helicopter "a helicopter" "$(social_rule_on helicopter)" \
      heavy "an A380, 747, Beluga, Antonov, C-17 and the like" "$(social_rule_on heavy)" \
      farthest "the farthest of the day (over 50 km)" "$(social_rule_on farthest)" \
      any "anything at all (one post per gap, the best-known aircraft)" "$(social_rule_on any)" 3>&1 1>&2 2>&3) || return 1
  rules=${rules//\"/}; cfg_set SOCIAL_RULES "${rules// /,}"
  wt_msg "Saved.\n\nNext:  sudo zenithboard social test   draws the picture and shows the text, posts nothing.\nThen:  sudo zenithboard social on     starts posting under these rules." 11
}
social_rule_on() { case ",$(cfg_get SOCIAL_RULES "$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import social; print(social.DEFAULTS["SOCIAL_RULES"])' "$ZB_HOME/flightinfo")")," in *",$1,"*) echo ON ;; *) echo OFF ;; esac; }

social_on() {
  [ -n "$(social_networks)" ] && [ -r "$SOCIAL_SECRETS" ] || { echo "No account yet: run  sudo zenithboard social setup  first."; return 1; }
  social_need_node || return 1
  social_prepare_dir || { echo "Could not make $SOCIAL_DIR"; return 1; }
  cfg_set SOCIAL 1; social_install_units
  echo "Social sharing is ON: $(social_networks), radius $(cfg_get SOCIAL_RADIUS_KM) km, at most one post every $(cfg_get SOCIAL_GAP_MIN) min, rules: $(cfg_get SOCIAL_RULES)."
  echo "Watch it:  zenithboard logs social      Stop it:  sudo zenithboard social off"
}
social_off() { cfg_set SOCIAL 0; social_remove_units; echo "Social sharing is OFF. The accounts are kept (remove them: sudo zenithboard social remove)."; }
social_remove() {
  social_off >/dev/null
  rm -f "$SOCIAL_SECRETS"; cfg_set SOCIAL_NETWORKS ""; rm -rf "$SOCIAL_DIR"
  echo "Social sharing removed: the account secrets, the state and the service are gone. Node stays (apt remove nodejs to drop it)."
}
social_status() {
  python3 "$SOCIAL_PY" status
  if [ -f "$SOCIAL_UNIT_DIR/$SOCIAL_UNIT.service" ]; then echo "Service: $(systemctl is-active "$SOCIAL_UNIT" 2>/dev/null || echo unknown)"; fi
}

# ---- the menu
social_menu() {
  local c
  while true; do
    c=$(wt_menu "Social sharing: $(social_state)    Networks: $(social_networks | sed 's/^$/none/')\nRadius: $(cfg_get SOCIAL_RADIUS_KM 15) km    Gap: $(cfg_get SOCIAL_GAP_MIN 120) min    Area: $(cfg_get SOCIAL_AREA "" | sed 's/^$/(none)/')\nRules: $(cfg_get SOCIAL_RULES rare,military,helicopter,heavy,farthest)\n\nPosts a picture of the wall and a short text when something worth it flies over. Nothing leaves the Pi until you switch it on." \
      setup "1  Set up or change the accounts (Bluesky, Mastodon)" \
      words "2  Words and rules: place name, radius, gap, what is worth a post" \
      test "3  Try it: draw the picture and show the text, post nothing" \
      toggle "4  Switch sharing $( [ "$(social_state)" = on ] && echo OFF || echo ON )" \
      post "5  Post now, once" \
      status "6  Status" \
      remove "7  Remove: accounts, state and service" \
      back "Return to the previous menu") || return 0
    case "$c" in
      setup) social_setup || true ;;
      words) social_setup_words || true ;;
      test) clear; social_need_node && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" test; read -rp "Press Enter to continue..." _ ;;
      toggle) clear; if [ "$(social_state)" = on ]; then social_off; else social_on; fi; read -rp "Press Enter to continue..." _ ;;
      post) clear; social_need_node && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" post; read -rp "Press Enter to continue..." _ ;;
      status) clear; social_status; read -rp "Press Enter to continue..." _ ;;
      remove) if wt_yesno "Remove social sharing: the account secrets, the state and the service?" 8; then clear; social_remove; read -rp "Press Enter to continue..." _; fi ;;
      *) return 0 ;;
    esac
  done
}
