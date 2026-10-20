# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Social sharing (menu 4 Settings -> 6 Social sharing, and `zenithboard social ...`).
#
# Posts the aircraft overhead to Bluesky as a picture of the wall, with a short text. Off by default. The work is
# done by flightinfo/social.py, running as a service under the wall's user; this file is the setup wizard, the
# switch, and the commands. Two looks for the picture, each beside a map of the track: the dot-matrix wall (drawn by
# tools/social-render.js, which needs Node, about 30 MB) or the split-flap board; the maps are laid by
# flightinfo/social_card.py, which needs Pillow and the DejaVu fonts, a few MB. Both are installed from Debian when
# they are first needed. The dots-only look (the track drawn in dots, no map) was taken out in 0.24.0. Bluesky only since 0.19.0: Mastodon was taken out.
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
SOCIAL_THEMES="amber green red white turquoise"           # the wall's colours; the dark blue went in 0.23.0
SOCIAL_MAPS="normal night satellite terrain none rotate"

# ---- the service
social_install_units() {
  [ -f "$ZB_HOME/systemd/$SOCIAL_UNIT.service" ] || return 0
  install -d -m 755 "$SOCIAL_UNIT_DIR"
  install -m 644 "$ZB_HOME/systemd/$SOCIAL_UNIT.service" "$SOCIAL_UNIT_DIR/"
  systemctl daemon-reload; systemctl enable "$SOCIAL_UNIT.service" >/dev/null 2>&1 || true
  # restart, not "enable --now": a running service keeps the code it started with, and an update that only
  # enabled it left the Pi posting with the old code for hours (seen on the real Pi, 0.19.3)
  systemctl restart "$SOCIAL_UNIT.service" >/dev/null 2>&1 || true
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
social_need_pil() {      # the map looks (dotmap, flap): Pillow paints the map and the board, in the DejaVu font
  python3 -c 'import PIL' >/dev/null 2>&1 && [ -f /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf ] && return 0
  log "Installing Pillow and the DejaVu fonts (draw the map pictures, dotmap and flap; a few MB)"
  apt_install python3-pil fonts-dejavu-core >/dev/null || { err "Pillow could not be installed: the map pictures (dotmap, flap) cannot be drawn without it."; return 1; }
}
social_need_tools() {    # what every look needs since 0.24.0: Node (the dots, the flap board's rows), Pillow (the map)
  social_need_node && social_need_pil
}
# The look as it is drawn: "dots" was taken out in 0.24.0 and is read as dotmap, like anything unknown
social_look() { local l; l=$(cfg_get SOCIAL_STYLE dotmap); social_valid_in "$l" dotmap flap alternate && printf '%s' "$l" || printf dotmap; }

# 0.19.0 took Mastodon out. A Pi set up before that keeps its Bluesky account; the Mastodon token and the list of
# networks are dropped, so no secret stays behind for a feature that is gone. Run by every update; does nothing twice.
social_migrate() {
  if grep -q '^SOCIAL_NETWORKS=' "$ZB_CONFIG" 2>/dev/null; then cfg_del SOCIAL_NETWORKS; fi
  if [ -f "$SOCIAL_SECRETS" ] && grep -q '^MASTODON_' "$SOCIAL_SECRETS" 2>/dev/null; then
    local h p
    h=$(social_secret_get BLUESKY_HANDLE); p=$(social_secret_get BLUESKY_APP_PASSWORD)
    if [ -n "$h" ]; then social_secrets_write "BLUESKY_HANDLE=$h" "BLUESKY_APP_PASSWORD=$p"
    else rm -f "$SOCIAL_SECRETS"; cfg_set SOCIAL 0; social_remove_units; log "Social sharing switched off: no Bluesky account. Set one up with  sudo zenithboard social setup"; fi
    log "Social sharing: Mastodon is no longer supported; its token was removed from $SOCIAL_SECRETS (revoke it on your instance too)."
  fi
  # 0.23.0: the dark blue is gone. A picture colour set to it is the owner's and is not changed: the posts take the
  # wall's colour meanwhile, and the update says so with the command
  if [ "$(cfg_get SOCIAL_THEME "")" = blue ]; then
    log "Social sharing: the dark blue was taken out in 0.23.0. Your picture colour is still set to it, so the posts take the wall's colour ($(wall_theme)). Choose one:  sudo zenithboard social colour turquoise  (or wall, rotate)"
  fi
  # 0.24.0: the dots-only look is gone, at the owner's word. A setting still on it is kept; the posts are dotmap
  if [ "$(cfg_get SOCIAL_STYLE "")" = dots ]; then
    log "Social sharing: the dots-only picture was taken out in 0.24.0. Your look is still set to it, so the posts are drawn as dotmap (the dot-matrix wall beside a map). Choose one:  sudo zenithboard social look dotmap  (or flap, alternate)"
  fi
  # 0.20.0: no gap by default, every crossing posted once. A gap set before is the owner's and is kept; say it.
  if [ "$(cfg_get SOCIAL 0)" = 1 ] && [ "$(social_gap_words)" != "none, every crossing" ]; then
    log "Social sharing: since 0.20.0 every crossing of the radius is posted, once, with no gap by default. Yours is still $(social_gap_words) between posts: sudo zenithboard social gap 0  to post every crossing."
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

# The gap as words: 0 (the default since 0.20.0) is no gap at all, every crossing posted.
social_gap_words() {
  local g; g=$(cfg_get SOCIAL_GAP_MIN 0)
  if awk -v g="$g" 'BEGIN { exit !(g + 0 <= 0) }'; then echo "none, every crossing"; else echo "$g min"; fi
}

# The words of the posts: the area named in them (the owner's words, never derived from the antenna's position),
# the radius, the gap, the rules.
social_setup_words() {
  local area radius gap rules
  area=$(wt_input "Where is this, in two or three words, as the posts should say it? A town name (Trémery) reads \"above Trémery\"; your own words (near Metz) are kept.\nLeave empty for no place at all. The receiver's position is never used." "$(cfg_get SOCIAL_AREA "")") || return 1
  cfg_set SOCIAL_AREA "$area"
  radius=$(wt_input "Sharing radius in km: an aircraft is a candidate while it is inside it. This is separate from the wall's radius." "$(cfg_get SOCIAL_RADIUS_KM 15)") || return 1
  is_number "$radius" && cfg_set SOCIAL_RADIUS_KM "$radius"
  gap=$(wt_input "Minimum minutes between two posts. 0 = none: every aircraft crossing the radius is posted once, as it happens.\nThe same crossing is never posted twice; the return flight or the next day is a new crossing." "$(cfg_get SOCIAL_GAP_MIN 0)") || return 1
  is_number "$gap" && cfg_set SOCIAL_GAP_MIN "$gap"
  local tags
  while true; do
    tags=$(wt_input "Hashtags at the end of each post, separated by spaces (the # is optional). none for no hashtags.\n#avgeek becomes #helicopter or #military when one of those is posted." "$(cfg_get SOCIAL_HASHTAGS "$SOCIAL_TAGS_DEFAULT")") || return 1
    if [ "$tags" = none ]; then cfg_set SOCIAL_HASHTAGS none; break; fi
    local said
    if said=$(social_hashtags_clean "$tags" 2>&1); then cfg_set SOCIAL_HASHTAGS "$said"; break; fi
    wt_msg "$said" 8
  done
  rules=$(whiptail --title "$WT_TITLE" --checklist "What is worth a post? Tick the special aircraft you want, or ALL (Space = tick, Enter = go).\n\nALL posts everything that crosses the radius, once per crossing, the special aircraft first when there is one. Ticking ALL alone is the same as ticking every line." 20 76 6 \
      military "military" "$(social_rule_on military)" \
      helicopter "a helicopter" "$(social_rule_on helicopter)" \
      heavy "an A380, 747, Beluga, Antonov, C-17 and the like" "$(social_rule_on heavy)" \
      rare "a type seen twice or less in thirty days (after 3 days of history)" "$(social_rule_on rare)" \
      farthest "a range record for 30 days, over 50 km (after 3 days of history)" "$(social_rule_on farthest)" \
      all "ALL: everything that flies over, the special ones included" "$(social_rule_on all)" 3>&1 1>&2 2>&3) || return 1
  rules=${rules//\"/}
  case " $rules " in *" all "*) rules=all ;; esac       # ALL stands for every line: saved as the one word
  cfg_set SOCIAL_RULES "${rules// /,}"
}

# ---- the hashtags (0.19.7): `social hashtags ADSB avgeek ZenithBoard`, with or without the #, which an unquoted
# shell word would otherwise take for the start of a comment. "none" for no hashtags at all, "default" for the three.
SOCIAL_TAGS_DEFAULT="#ADSB #avgeek #ZenithBoard"
social_hashtags_clean() {   # words -> "#a #b" on stdout; returns 1 with the reason on stderr when a word will not do
  local w arg parts found=() n=0
  for arg in "$@"; do
    read -r -a parts <<< "$arg"             # a quoted "#a #b" is split like separate words; read does no globbing
    for w in "${parts[@]}"; do
      w=${w##\#}; w=${w##\#}
      [ -n "$w" ] || continue
      if ! [[ $w =~ ^[A-Za-z0-9_]{1,40}$ ]] || ! [[ $w =~ [A-Za-z] ]]; then
        echo "Not a hashtag: $w (letters, digits and _ only, at least one letter, 40 at most)" >&2; return 1
      fi
      found+=("#$w"); n=$((n + 1))
    done
  done
  [ "$n" -gt 0 ] || { echo "No hashtag given" >&2; return 1; }
  [ "$n" -le 8 ] || { echo "$n hashtags: 8 at most (a post has 300 characters)" >&2; return 1; }
  w="${found[*]}"
  [ "${#w}" -le 100 ] || { echo "${#w} characters of hashtags: 100 at most (a post has 300)" >&2; return 1; }
  printf '%s' "$w"
}
social_set_hashtags() {
  local tags
  case "${1:-}" in
    "") echo "Hashtags: $(cfg_get SOCIAL_HASHTAGS "$SOCIAL_TAGS_DEFAULT")"
        echo "Change:  sudo zenithboard social hashtags ADSB avgeek ZenithBoard   (the # is optional), none, or default"; return 0 ;;
    none) cfg_set SOCIAL_HASHTAGS none; echo "Hashtags: none. The posts end with the text (and the map's credit)."; return 0 ;;
    default) cfg_set SOCIAL_HASHTAGS "$SOCIAL_TAGS_DEFAULT"; echo "Hashtags: $SOCIAL_TAGS_DEFAULT"; return 0 ;;
  esac
  tags=$(social_hashtags_clean "$@") || return 1
  cfg_set SOCIAL_HASHTAGS "$tags"
  echo "Hashtags: $tags"
  case " $tags " in *" #avgeek "*) echo "(#avgeek becomes #helicopter or #military when one of those is posted.)" ;; esac
}

# ---- the gap (0.20.0): none by default, every crossing posted once; `social gap 30` for half an hour at least
social_set_gap() {
  if [ -z "${1:-}" ]; then
    echo "Gap between posts: $(social_gap_words)"
    echo "Change:  sudo zenithboard social gap MINUTES   (0 = none: every crossing of the radius is posted, once)"; return 0
  fi
  [[ $1 =~ ^[0-9]{1,4}$ ]] && [ "$((10#$1))" -le 1440 ] || { echo "Gap: whole minutes, 0 to 1440 (0 = none)" >&2; return 1; }
  cfg_set SOCIAL_GAP_MIN "$((10#$1))"
  echo "Gap between posts: $(social_gap_words). The service takes it at its next look, no restart needed."
}

# ---- the picture: the look, its colour, the map (the looks with a map: dotmap and flap)
social_valid_in() { local v=$1; shift; [[ $v =~ ^[a-z]+$ ]] && [[ " $* " == *" $v "* ]]; }   # exactly one of the words
social_set_look() {
  social_valid_in "${1:-}" dotmap flap alternate || { echo "Look: dotmap (the dot-matrix wall and a map), flap (the split-flap board and a map), or alternate (the two in turn)"; return 1; }
  social_need_pil || return 1                           # install first: a look that cannot be drawn is not saved
  cfg_set SOCIAL_STYLE "$1"
  echo "Picture: $1. Try it:  sudo zenithboard social test"
}
social_set_colour() {
  local c=${1:-}
  [ -n "$c" ] || { echo "Colour: $SOCIAL_THEMES, rotate (in turn), or wall (the wall's own, $(wall_theme))"; return 1; }
  [ "$c" != wall ] || c=""
  [ -z "$c" ] || social_valid_in "$c" $SOCIAL_THEMES rotate || { echo "Colour: $SOCIAL_THEMES, rotate (in turn), or wall (the wall's own, $(wall_theme))"; return 1; }
  cfg_set SOCIAL_THEME "$c"
  case "$c" in
    rotate) echo "Picture colour: the colours in turn, one step per post." ;;
    *) echo "Picture colour: $(or_text "$c" "the wall's ($(wall_theme))")." ;;
  esac
}
social_set_units() {     # 0.24.3: the posts in metric or imperial, or the wall's own units (empty)
  local u=${1:-}
  social_valid_in "$u" metric imperial wall || { echo "Units: metric (m, km/h, km), imperial (ft, knots, mi), or wall (the wall's own, $(cfg_get UNITS metric))"; return 1; }
  [ "$u" != wall ] || u=""
  cfg_set SOCIAL_UNITS "$u"
  echo "Post units: $(or_text "$u" "the wall's ($(cfg_get UNITS metric))")."
}
# 0.25.0: a last line in each post, "Photo: NAME / Planespotters", linking to the aircraft's photo page. The link only:
# Planespotters' photo API terms forbid posting or storing the picture. Off by default.
social_set_photolink() {
  case "${1:-}" in
    on)  cfg_set SOCIAL_PHOTOLINK 1 ;;
    off) cfg_set SOCIAL_PHOTOLINK 0 ;;
    "")  ;;
    *)   echo "Photo link: on or off"; return 1 ;;
  esac
  if [ "$(cfg_get SOCIAL_PHOTOLINK 0)" = 1 ]; then
    echo "Photo link: ON. A post ends with \"Photo: NAME / Planespotters\", a link to the photo page, when the wall has a photo of that aircraft (photos on). The picture itself is never posted."
  else
    echo "Photo link: OFF. Posts carry no link to a photo."
  fi
}
# 0.27.0: the town names of the maps from the region's own list, made here from GeoNames' country files: every
# populated place within 400 km, ranked by population or, where GeoNames knows none, by rank (capital, province seat,
# district seat, village). The shipped lists name the places whose population GeoNames knows: a map over a region
# where it knows few (Indonesia) was left almost bare. Off by default; on downloads the files once (about 20 MB
# around Metz) and keeps a few hundred kilobytes; on again makes it again; off deletes it.
SOCIAL_PLACES_FILE="places-local.tsv.gz"
social_set_places() {
  local f="$SOCIAL_DIR/$SOCIAL_PLACES_FILE" lat lon
  case "${1:-}" in
    on)
      lat=$(cfg_get LAT 0); lon=$(cfg_get LON 0)
      if [ "$lat" = 0 ] && [ "$lon" = 0 ]; then echo "Set the antenna's position first (sudo zenithboard location LAT LON)."; return 1; fi
      social_prepare_dir || return 1
      echo "Making the region's list of places from GeoNames (the country files around this Pi; a few minutes on a Pi 3B)..."
      python3 "$ZB_HOME/tools/make_local_places.py" "$lat" "$lon" "$f" "$(cfg_get SOCIAL_PLACES_KM 400)" || return 1
      chown "$ZB_USER:$ZB_USER" "$f" 2>/dev/null || true
      cfg_set SOCIAL_PLACES 1 ;;
    off)
      cfg_set SOCIAL_PLACES 0; rm -f "$f" ;;
    "") ;;
    *) echo "Town names: on (make the region's list, or make it again) or off (back to the shipped lists)"; return 1 ;;
  esac
  [ -z "${1:-}" ] || systemctl try-restart "$SOCIAL_UNIT.service" 2>/dev/null || true
  if [ "$(cfg_get SOCIAL_PLACES 0)" = 1 ] && [ -f "$f" ]; then
    echo "Town names: the region's own list ($f). Make it again after moving the antenna: sudo zenithboard social places on. Back to the shipped lists: sudo zenithboard social places off"
  else
    echo "Town names: the lists shipped with ZenithBoard (towns of 5 000 or more, villages when a map is short). The region's own list: sudo zenithboard social places on"
  fi
}
social_set_map() {
  social_valid_in "${1:-}" $SOCIAL_MAPS || { echo "Map: $SOCIAL_MAPS (rotate: the four maps in turn)"; return 1; }
  cfg_set SOCIAL_MAP "$1"
  echo "Map: $1."
}
social_setup_picture() {
  local look col map cur on units
  cur=$(social_look)
  look=$(wt_radio "The picture each post carries. (Space = choose, Enter = go)" \
      dotmap "Dot-matrix wall, a map with the track beside it" "$( [ "$cur" = dotmap ] && echo ON || echo OFF )" \
      flap "Split-flap board, a map with the track beside it" "$( [ "$cur" = flap ] && echo ON || echo OFF )" \
      alternate "Dot-matrix and split-flap with a map, in turn" "$( [ "$cur" = alternate ] && echo ON || echo OFF )") || return 1
  cur=$(cfg_get SOCIAL_THEME "")
  social_valid_in "$cur" $SOCIAL_THEMES rotate || cur=wall    # empty, or the blue taken out in 0.23.0: the wall's
  local items=(wall "The wall's own colour ($(wall_theme))" "$( [ "$cur" = wall ] && echo ON || echo OFF )")
  for c in $SOCIAL_THEMES; do on=OFF; [ "$cur" = "$c" ] && on=ON; items+=("$c" "${c^}" "$on"); done
  items+=(rotate "In turn, one step per post" "$( [ "$cur" = rotate ] && echo ON || echo OFF )")
  col=$(wt_radio "Colour of the letters and the track" "${items[@]}") || return 1
  cur=$(cfg_get SOCIAL_UNITS ""); [ -n "$cur" ] || cur=wall
  units=$(wt_radio "Units of the posts: the picture and the text" \
      wall "The wall's own ($(cfg_get UNITS metric))" "$( [ "$cur" = wall ] && echo ON || echo OFF )" \
      metric "Metric: m, km/h, km" "$( [ "$cur" = metric ] && echo ON || echo OFF )" \
      imperial "Imperial: ft, knots, mi" "$( [ "$cur" = imperial ] && echo ON || echo OFF )") || return 1
  cur=$(cfg_get SOCIAL_MAP normal)
  map=$(wt_radio "The map beside the wall or the board (from EOX's map service, credited on every post)" \
      normal "OpenStreetMap" "$( [ "$cur" = normal ] && echo ON || echo OFF )" \
      night "OpenStreetMap, darkened" "$( [ "$cur" = night ] && echo ON || echo OFF )" \
      satellite "Satellite (Sentinel-2 cloudless, non-commercial use)" "$( [ "$cur" = satellite ] && echo ON || echo OFF )" \
      terrain "Terrain: relief, forests, rivers" "$( [ "$cur" = terrain ] && echo ON || echo OFF )" \
      none "No map: the track on black, nothing fetched" "$( [ "$cur" = none ] && echo ON || echo OFF )" \
      rotate "The four maps in turn (not none)" "$( [ "$cur" = rotate ] && echo ON || echo OFF )") || return 1
  social_set_map "$map" >/dev/null
  clear
  social_set_colour "$col" >/dev/null || return 1
  social_set_units "$units" >/dev/null || return 1
  social_set_look "$look" >/dev/null || { read -rp "Press Enter to continue..." _; return 1; }
  wt_msg "Saved. Picture: $look, $(or_text "$(cfg_get SOCIAL_THEME "")" "the wall's colour ($(wall_theme))"), $(cfg_get SOCIAL_MAP normal) map.\n\nNext:  sudo zenithboard social test   draws the picture and shows the text, posts nothing.\nThen:  sudo zenithboard social on     starts posting." 12
}
social_rule_on() { [ "$1" = all ] && case ",$(cfg_get SOCIAL_RULES "")," in *",all,"*|*",any,"*) echo ON; return ;; esac; case ",$(cfg_get SOCIAL_RULES "$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import social; print(social.DEFAULTS["SOCIAL_RULES"])' "$ZB_HOME/flightinfo")")," in *",$1,"*) echo ON ;; *) echo OFF ;; esac; }

social_on() {
  [ -n "$(social_account)" ] || { echo "No Bluesky account yet: run  sudo zenithboard social setup  first."; return 1; }
  social_need_tools || return 1
  social_prepare_dir || { echo "Could not make $SOCIAL_DIR"; return 1; }
  cfg_set SOCIAL 1; social_install_units
  echo "Social sharing is ON: Bluesky @$(social_account), radius $(cfg_get SOCIAL_RADIUS_KM) km, once per crossing, gap between posts: $(social_gap_words), rules: $(cfg_get SOCIAL_RULES)."
  echo "Watch it:  zenithboard logs social      Stop it:  sudo zenithboard social off"
}
social_off() { cfg_set SOCIAL 0; social_remove_units; echo "Social sharing is OFF. The accounts are kept (remove them: sudo zenithboard social remove)."; }
social_remove() {
  social_off >/dev/null
  rm -f "$SOCIAL_SECRETS"; rm -rf "$SOCIAL_DIR"
  echo "Social sharing removed: the account secret, the state, the map tiles and the service are gone. Node and Pillow stay (apt remove nodejs python3-pil to drop them)."
}
# Run as root, the status is read as the service's own user, who can read the account file and the state folder.
# It ends with the service itself: since when it runs, and whether it runs the code installed now.
social_status() {
  if [ "$(id -u)" -eq 0 ] && id "$ZB_USER" >/dev/null 2>&1 && [ "$ZB_USER" != root ]; then
    runuser -u "$ZB_USER" -- python3 "$SOCIAL_PY" status
  else
    python3 "$SOCIAL_PY" status
  fi
  [ -f "$SOCIAL_UNIT_DIR/$SOCIAL_UNIT.service" ] || return 0
  local st since started code
  st=$(systemctl is-active "$SOCIAL_UNIT" 2>/dev/null || echo unknown)
  since=$(systemctl show -p ActiveEnterTimestamp --value "$SOCIAL_UNIT" 2>/dev/null || true)
  if [ "$st" = active ] && [ -n "$since" ]; then
    started=$(date -d "$since" +%s 2>/dev/null || echo 0)
    code=$(stat -c %Y "$SOCIAL_PY" "$ZB_HOME/flightinfo/social_card.py" "$ZB_HOME/tools/social-render.js" "$ZB_HOME/flightinfo/static/format.js" 2>/dev/null | sort -n | tail -1)
    echo "Service: active since $since"
    if [ "${code:-0}" -gt "${started:-0}" ] && [ "${started:-0}" -gt 0 ]; then
      echo "  It runs the code from before the last update. Restart it:  sudo systemctl restart $SOCIAL_UNIT"
    fi
  else
    echo "Service: $st"
  fi
}

# ---- the menu
social_menu() {
  local c
  while true; do
    c=$(wt_menu "Social sharing: $(social_state)    Bluesky: $(or_text "$(social_account)" "no account")    Picture: $(social_look)\nRadius: $(cfg_get SOCIAL_RADIUS_KM 15) km    Gap: $(social_gap_words)    Area: $(or_text "$(cfg_get SOCIAL_AREA "")" "(none)")\nRules: $(cfg_get SOCIAL_RULES rare,military,helicopter,heavy,farthest)\n\nPosts a picture of the wall and a short text when something worth it flies over. Nothing leaves the Pi until you switch it on." \
      setup "1  Set up or change the Bluesky account" \
      words "2  Words and rules: place name, radius, gap, what is worth a post" \
      picture "3  The picture: dot-matrix or split-flap, colour, map" \
      photolink "4  Link to the Planespotters photo page: $( [ "$(cfg_get SOCIAL_PHOTOLINK 0)" = 1 ] && echo ON || echo OFF )" \
      places "5  Town names from the region's own list (GeoNames, downloaded once): $( [ "$(cfg_get SOCIAL_PLACES 0)" = 1 ] && echo ON || echo OFF )" \
      test "6  Try it: draw the picture and show the text, post nothing" \
      toggle "7  Switch sharing $( [ "$(social_state)" = on ] && echo OFF || echo ON )" \
      post "8  Post now, once" \
      status "9  Status" \
      remove "10 Remove: account, state and service" \
      back "Return to the previous menu") || return 0
    case "$c" in
      setup) social_setup || true ;;
      words) social_setup_words && wt_msg "Saved." 7 || true ;;
      picture) social_setup_picture || true ;;
      photolink) social_set_photolink "$( [ "$(cfg_get SOCIAL_PHOTOLINK 0)" = 1 ] && echo off || echo on )" >/dev/null; wt_msg "$(social_set_photolink)" 10 ;;
      places)
        if [ "$(cfg_get SOCIAL_PLACES 0)" = 1 ]; then
          wt_yesno "Town names come from the region's own list.\n\nGo back to the lists shipped with ZenithBoard (and delete the region's list)?" 10 && social_set_places off >/dev/null
        elif wt_yesno "Name the towns on the maps from the region's own list?\n\nThe Pi downloads GeoNames' files of the countries within 400 km (about 20 MB around Metz, once) and keeps every populated place, ranked by population or, where it is unknown, by rank (capital, province seat, village). Useful where the shipped lists know few towns. Nothing about this Pi is sent." 14; then
          clear; social_set_places on; read -rp "Press Enter to continue..." _
        fi ;;
      test) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" test; read -rp "Press Enter to continue..." _ ;;
      toggle) clear; if [ "$(social_state)" = on ]; then social_off; else social_on; fi; read -rp "Press Enter to continue..." _ ;;
      post) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" post; read -rp "Press Enter to continue..." _ ;;
      status) clear; social_status; read -rp "Press Enter to continue..." _ ;;
      remove) if wt_yesno "Remove social sharing: the account secret, the state and the service?" 8; then clear; social_remove; read -rp "Press Enter to continue..." _; fi ;;
      *) return 0 ;;
    esac
  done
}
