# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Social sharing (menu 4 Settings -> 6 Social sharing, and `zenithboard social ...`).
#
# Posts the aircraft overhead to Bluesky as a picture of the wall, with a short text. Off by default. The work is
# done by flightinfo/social.py, running as a service under the wall's user; this file is the setup wizard, the
# switch, and the commands. Two looks for the picture: the dot-matrix wall with the track in dots (drawn by
# tools/social-render.js, which needs Node, about 30 MB), or the split-flap board beside a map (drawn by
# flightinfo/social_card.py, which needs Pillow and the DejaVu fonts, a few MB). Each is installed from Debian
# when it is first needed. Bluesky only since 0.19.0: Mastodon was taken out.
#
# The secret (a Bluesky app password, never the real one) lives in $ZB_ETC/social.env, owned by root, readable by
# the zenithboard group (the service runs as that user), mode 0640. Never in config.env, never in a log, never
# shown by `zenithboard config`. `social remove` deletes that file.
SOCIAL_SECRETS="${ZENITHBOARD_SOCIAL_SECRETS:-${ZB_ETC:-/etc/zenithboard}/social.env}"
SOCIAL_DIR="${ZENITHBOARD_SOCIAL_DIR:-/var/lib/zenithboard/social}"
SOCIAL_UNIT=zenithboard-social
SOCIAL_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
SOCIAL_PY="$ZB_HOME/flightinfo/social.py"

or_text() { if [ -n "$1" ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }   # a value, or what to say when it is empty
social_state() { [ "$(cfg_get SOCIAL 0)" = 1 ] && echo on || echo off; }
social_account() { social_secret_get BLUESKY_HANDLE; }
SOCIAL_THEMES="amber green red white turquoise blue"
SOCIAL_MAPS="normal night satellite terrain none"

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
social_need_pil() {      # the split-flap look: Pillow paints the board and the map, in the DejaVu font
  python3 -c 'import PIL' >/dev/null 2>&1 && [ -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ] && return 0
  log "Installing Pillow and the DejaVu fonts (draw the split-flap picture; a few MB)"
  apt_install python3-pil fonts-dejavu-core >/dev/null || { err "Pillow could not be installed: the split-flap picture cannot be drawn without it."; return 1; }
}
social_need_tools() {    # what the chosen look needs: Node always (the dot-matrix picture, and the flap board's rows), Pillow for flap
  social_need_node || return 1
  [ "$(cfg_get SOCIAL_STYLE dots)" != flap ] || social_need_pil
}

# 0.19.0 took Mastodon out. A Pi set up before that keeps its Bluesky account; the Mastodon token and the list of
# networks are dropped, so no secret stays behind for a feature that is gone. Run by every update; does nothing twice.
social_migrate() {
  if grep -q '^SOCIAL_NETWORKS=' "$ZB_CONFIG" 2>/dev/null; then cfg_del SOCIAL_NETWORKS; fi
  if [ -f "$SOCIAL_SECRETS" ] && grep -q '^MASTODON_' "$SOCIAL_SECRETS" 2>/dev/null; then
    local h p
    h=$(social_secret_get BLUESKY_HANDLE); p=$(social_secret_get BLUESKY_APP_PASSWORD)
    if [ -n "$h" ]; then social_secrets_write "BLUESKY_HANDLE=$h" "BLUESKY_APP_PASSWORD=$p"; else rm -f "$SOCIAL_SECRETS"; fi
    log "Social sharing: Mastodon is no longer supported; its token was removed from $SOCIAL_SECRETS (revoke it on your instance too)."
  fi
  return 0
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

# ---- the wizard: the Bluesky account, tried before anything else is asked
social_setup() {
  local handle pw have r
  have=$(social_secret_get BLUESKY_HANDLE)
  handle=$(wt_input "Bluesky handle, without @ (for example zenithboard.bsky.social).\n\nThe account should be declared as automated: on bsky.app, Settings -> Account -> Automation label." "${have}") || return 1
  handle=${handle#@}; handle=$(echo "$handle" | tr '[:upper:]' '[:lower:]')
  social_valid_handle "$handle" || { wt_msg "That does not look like a Bluesky handle: $handle" 8; return 1; }
  pw=$(whiptail --title "$WT_TITLE" --passwordbox "Bluesky APP password for that account (not your real password).\n\nMake one at bsky.app: Settings -> Privacy and Security -> App Passwords -> Add App Password. It looks like xxxx-xxxx-xxxx-xxxx and is shown once.$( [ -n "$have" ] && printf '\n\nLeave empty to keep the one saved.')" 15 76 3>&1 1>&2 2>&3) || return 1
  [ -n "$pw" ] || pw=$(social_secret_get BLUESKY_APP_PASSWORD)
  [ -n "$pw" ] || { wt_msg "No app password given." 7; return 1; }
  social_secrets_write "BLUESKY_HANDLE=$handle" "BLUESKY_APP_PASSWORD=$pw" || { wt_msg "Could not write $SOCIAL_SECRETS" 8; return 1; }
  clear; echo "Trying the account..."; echo
  r=$(python3 "$SOCIAL_PY" check 2>&1); echo "$r"; echo
  if echo "$r" | grep -q FAILED; then
    echo "Bluesky refused. The handle and app password are saved; fix them with  sudo zenithboard social setup  and try again."
    read -rp "Press Enter to continue..." _; return 1
  fi
  social_setup_words && social_setup_picture
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
      farthest "a range record for 30 days (over 50 km)" "$(social_rule_on farthest)" \
      any "anything at all (one post per gap, the best-known aircraft)" "$(social_rule_on any)" 3>&1 1>&2 2>&3) || return 1
  rules=${rules//\"/}; cfg_set SOCIAL_RULES "${rules// /,}"
}

# ---- the picture: the look, its colour, the map (the flap look only)
social_valid_in() { local v=$1; shift; [[ " $* " == *" $v "* ]]; }
social_set_look() {
  social_valid_in "$1" dots flap || { echo "Look: dots or flap"; return 1; }
  cfg_set SOCIAL_STYLE "$1"
  [ "$1" != flap ] || social_need_pil || return 1
  echo "Picture: $1. Try it:  sudo zenithboard social test"
}
social_set_colour() {
  local c=$1; [ "$c" != wall ] || c=""
  [ -z "$c" ] || social_valid_in "$c" $SOCIAL_THEMES || { echo "Colour: $SOCIAL_THEMES, or wall (the wall's own, $(cfg_get THEME amber))"; return 1; }
  cfg_set SOCIAL_THEME "$c"
  echo "Picture colour: $(or_text "$c" "the wall's ($(cfg_get THEME amber))")."
}
social_set_map() {
  social_valid_in "$1" $SOCIAL_MAPS || { echo "Map: $SOCIAL_MAPS"; return 1; }
  cfg_set SOCIAL_MAP "$1"
  echo "Map: $1 (the split-flap look). $( [ "$(cfg_get SOCIAL_STYLE dots)" = flap ] || echo 'The picture is the dot-matrix look now; switch with  sudo zenithboard social look flap')"
}
social_setup_picture() {
  local look col map cur on
  cur=$(cfg_get SOCIAL_STYLE dots)
  look=$(wt_radio "The picture each post carries. (Space = choose, Enter = go)" \
      dots "Dot-matrix wall, the track drawn in dots beside it" "$( [ "$cur" = dots ] && echo ON || echo OFF )" \
      flap "Split-flap board, a map with the track beside it" "$( [ "$cur" = flap ] && echo ON || echo OFF )") || return 1
  cur=$(cfg_get SOCIAL_THEME ""); [ -n "$cur" ] || cur=wall
  local items=(wall "The wall's own colour ($(cfg_get THEME amber))" "$( [ "$cur" = wall ] && echo ON || echo OFF )")
  for c in $SOCIAL_THEMES; do on=OFF; [ "$cur" = "$c" ] && on=ON; items+=("$c" "${c^}" "$on"); done
  col=$(wt_radio "Colour of the letters and the track" "${items[@]}") || return 1
  if [ "$look" = flap ]; then
    cur=$(cfg_get SOCIAL_MAP normal)
    map=$(wt_radio "The map beside the board (from EOX's map service, credited on every post)" \
        normal "OpenStreetMap" "$( [ "$cur" = normal ] && echo ON || echo OFF )" \
        night "OpenStreetMap, darkened" "$( [ "$cur" = night ] && echo ON || echo OFF )" \
        satellite "Satellite (Sentinel-2 cloudless, non-commercial use)" "$( [ "$cur" = satellite ] && echo ON || echo OFF )" \
        terrain "Terrain: relief, forests, rivers" "$( [ "$cur" = terrain ] && echo ON || echo OFF )" \
        none "No map: the track on black, nothing fetched" "$( [ "$cur" = none ] && echo ON || echo OFF )") || return 1
    social_set_map "$map" >/dev/null
  fi
  clear
  social_set_colour "$col" >/dev/null
  social_set_look "$look" >/dev/null || { read -rp "Press Enter to continue..." _; return 1; }
  wt_msg "Saved. Picture: $look, $(or_text "$(cfg_get SOCIAL_THEME "")" "the wall's colour")$( [ "$look" = flap ] && echo ", $(cfg_get SOCIAL_MAP normal) map").\n\nNext:  sudo zenithboard social test   draws the picture and shows the text, posts nothing.\nThen:  sudo zenithboard social on     starts posting." 12
}
social_rule_on() { case ",$(cfg_get SOCIAL_RULES "$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import social; print(social.DEFAULTS["SOCIAL_RULES"])' "$ZB_HOME/flightinfo")")," in *",$1,"*) echo ON ;; *) echo OFF ;; esac; }

social_on() {
  [ -n "$(social_account)" ] || { echo "No Bluesky account yet: run  sudo zenithboard social setup  first."; return 1; }
  social_need_tools || return 1
  social_prepare_dir || { echo "Could not make $SOCIAL_DIR"; return 1; }
  cfg_set SOCIAL 1; social_install_units
  echo "Social sharing is ON: Bluesky @$(social_account), radius $(cfg_get SOCIAL_RADIUS_KM) km, at most one post every $(cfg_get SOCIAL_GAP_MIN) min, rules: $(cfg_get SOCIAL_RULES)."
  echo "Watch it:  zenithboard logs social      Stop it:  sudo zenithboard social off"
}
social_off() { cfg_set SOCIAL 0; social_remove_units; echo "Social sharing is OFF. The accounts are kept (remove them: sudo zenithboard social remove)."; }
social_remove() {
  social_off >/dev/null
  rm -f "$SOCIAL_SECRETS"; rm -rf "$SOCIAL_DIR"
  echo "Social sharing removed: the account secret, the state, the map tiles and the service are gone. Node and Pillow stay (apt remove nodejs python3-pil to drop them)."
}
social_status() {
  python3 "$SOCIAL_PY" status
  if [ -f "$SOCIAL_UNIT_DIR/$SOCIAL_UNIT.service" ]; then echo "Service: $(systemctl is-active "$SOCIAL_UNIT" 2>/dev/null || echo unknown)"; fi
}

# ---- the menu
social_menu() {
  local c
  while true; do
    c=$(wt_menu "Social sharing: $(social_state)    Bluesky: $(or_text "$(social_account)" "no account")    Picture: $(cfg_get SOCIAL_STYLE dots)\nRadius: $(cfg_get SOCIAL_RADIUS_KM 15) km    Gap: $(cfg_get SOCIAL_GAP_MIN 120) min    Area: $(or_text "$(cfg_get SOCIAL_AREA "")" "(none)")\nRules: $(cfg_get SOCIAL_RULES rare,military,helicopter,heavy,farthest)\n\nPosts a picture of the wall and a short text when something worth it flies over. Nothing leaves the Pi until you switch it on." \
      setup "1  Set up or change the Bluesky account" \
      words "2  Words and rules: place name, radius, gap, what is worth a post" \
      picture "3  The picture: dot-matrix or split-flap, colour, map" \
      test "4  Try it: draw the picture and show the text, post nothing" \
      toggle "5  Switch sharing $( [ "$(social_state)" = on ] && echo OFF || echo ON )" \
      post "6  Post now, once" \
      status "7  Status" \
      remove "8  Remove: account, state and service" \
      back "Return to the previous menu") || return 0
    case "$c" in
      setup) social_setup || true ;;
      words) social_setup_words && wt_msg "Saved." 7 || true ;;
      picture) social_setup_picture || true ;;
      test) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" test; read -rp "Press Enter to continue..." _ ;;
      toggle) clear; if [ "$(social_state)" = on ]; then social_off; else social_on; fi; read -rp "Press Enter to continue..." _ ;;
      post) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" post; read -rp "Press Enter to continue..." _ ;;
      status) clear; social_status; read -rp "Press Enter to continue..." _ ;;
      remove) if wt_yesno "Remove social sharing: the account secret, the state and the service?" 8; then clear; social_remove; read -rp "Press Enter to continue..." _; fi ;;
      *) return 0 ;;
    esac
  done
}
