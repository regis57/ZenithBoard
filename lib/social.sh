# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Social sharing (menu 7 Options -> 3 Bluesky, and `zenithboard social ...`).
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
# 0.51.0: the owner's own post templates, one per line (no secret in it; the service reads it, root writes it)
SOCIAL_TEMPLATES="${ZENITHBOARD_SOCIAL_TEMPLATES:-${ZB_ETC:-/etc/zenithboard}/social-templates.txt}"
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
  # The audit of 22-23 October 2026: each answer used to be written as it came, so an Esc at the third question kept
  # the first two. Now nothing is written before the last answer; Esc anywhere leaves the settings as they were.
  local area radius gap tags rules said
  while true; do
    area=$(wt_input "Where is this, in two or three words, as the posts should say it? A town name (Trémery) reads \"above Trémery\"; your own words (near Metz) are kept.\nLeave empty for no place at all. The receiver's position is never used.\nThe posts are public: a town or a region says enough, not your village." "$(cfg_get SOCIAL_AREA "")") || return 1
    if [ -z "${area//[[:space:]]/}" ] || [ "$(social_area_clean "$area")" = none ]; then area=""; break; fi
    if said=$(social_area_clean "$area"); then area=$said; break; fi
    wt_msg "Letters, digits, spaces and ' - . , only, 40 characters at most." 8
  done
  # 0.53.7: the same rules as the commands (social radius, social gap), asked again with the reason
  while true; do
    radius=$(wt_input "Sharing radius in km: an aircraft is a candidate while it is inside it. This is separate from the wall's radius." "$(cfg_get SOCIAL_RADIUS_KM 15)") || return 1
    if said=$(social_valid_radius "$radius" 2>&1); then break; fi
    wt_msg "$said" 8
  done
  while true; do
    gap=$(wt_input "Minimum minutes between two posts. 0 = none: every aircraft crossing the radius is posted once, as it happens.\nThe same crossing is never posted twice; the return flight or the next day is a new crossing." "$(cfg_get SOCIAL_GAP_MIN 0)") || return 1
    if said=$(social_valid_gap "$gap" 2>&1); then break; fi
    wt_msg "$said" 8
  done
  while true; do
    tags=$(wt_input "Hashtags at the end of each post, separated by spaces (the # is optional). none for no hashtags.\n#avgeek becomes #helicopter or #military when one of those is posted." "$(cfg_get SOCIAL_HASHTAGS "$SOCIAL_TAGS_DEFAULT")") || return 1
    [ "$tags" = none ] && break
    if said=$(social_hashtags_clean "$tags" 2>&1); then tags=$said; break; fi
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
  cfg_set SOCIAL_AREA "$area"
  social_set_radius "$radius" >/dev/null
  social_set_gap "$gap" >/dev/null
  cfg_set SOCIAL_HASHTAGS "$tags"
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

# ---- 0.50.0: the wizard's other answers one by one, so the web console can set them (the owner, 22 October 2026)
# The place name: the owner's words ("Trémery" reads "above Trémery"; "near Metz" is kept), never the position.
social_area_clean() {   # TEXT -> the name with its spaces tidied, or returns 1
  python3 -c 'import re, sys
v = " ".join(sys.argv[1].split())
if not re.fullmatch(r"[^\W_][\w \x27\u2019.,-]{0,39}", v):
    sys.exit(1)
print(v)' "$1"
}
social_area_reads() {   # NAME -> how a post ends with it, by social.py's own rule
  python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import social; print(social.area_words({"SOCIAL_AREA": sys.argv[2]}))' "$ZB_HOME/flightinfo" "$1" 2>/dev/null
}
social_set_area() {     # social_set_area [WORDS...|none]
  local v="$*"
  v="${v#"${v%%[![:space:]]*}"}"; v="${v%"${v##*[![:space:]]}"}"      # trimmed, so " none " is none
  if [ -z "$v" ]; then
    echo "Place name: $(or_text "$(cfg_get SOCIAL_AREA "")" "(none)")"
    echo "Change:  sudo zenithboard social area Trémery   (or near Metz: two or three words, as the posts say it), or none. The posts are public: a town or a region, not your village"; return 0
  fi
  if [ "$v" = none ]; then cfg_set SOCIAL_AREA ""; echo "Place name: none. The posts name no place."; return 0; fi
  v=$(social_area_clean "$v") || { echo "Place name: letters, digits, spaces and ' - . , only, 40 characters at most, starting with a letter or a digit" >&2; return 1; }
  cfg_set SOCIAL_AREA "$v"
  echo "Place name: $v   (the posts say: $(social_area_reads "$v"))"
}
social_valid_radius() { [[ ${1:-} =~ ^[0-9]{1,3}$ ]] && [ "$((10#$1))" -ge 1 ] && [ "$((10#$1))" -le 200 ] || { echo "Sharing radius: whole kilometres, 1 to 200" >&2; return 1; }; }
social_valid_gap() { [[ ${1:-} =~ ^[0-9]{1,4}$ ]] && [ "$((10#$1))" -le 1440 ] || { echo "Gap: whole minutes, 0 to 1440 (0 = none)" >&2; return 1; }; }
social_set_radius() {   # social_set_radius [KM]: an aircraft inside it is a candidate; not the wall's radius
  if [ -z "${1:-}" ]; then
    echo "Sharing radius: $(cfg_get SOCIAL_RADIUS_KM 15) km"
    echo "Change:  sudo zenithboard social radius KM   (1 to 200 km; separate from the wall's radius)"; return 0
  fi
  social_valid_radius "$1" || return 1
  cfg_set SOCIAL_RADIUS_KM "$((10#$1))"
  echo "Sharing radius: $((10#$1)) km. The service takes it at its next look, no restart needed."
}
SOCIAL_RULE_WORDS="military helicopter heavy rare farthest"
social_set_rules() {    # social_set_rules [all|LIST]: what is worth a post, as the wizard's ticks
  local w out=() seen=" "
  if [ -z "${1:-}" ]; then
    echo "What is worth a post: $(cfg_get SOCIAL_RULES rare,military,helicopter,heavy,farthest)"
    echo "Change:  sudo zenithboard social rules all   (every crossing), or some of: ${SOCIAL_RULE_WORDS// /,}"; return 0
  fi
  [[ ${1//[, ]/} ]] || { echo "Rules: all, or one or more of ${SOCIAL_RULE_WORDS// /, }, separated by commas" >&2; return 1; }
  for w in ${1//,/ }; do
    [ "$w" = all ] && { cfg_set SOCIAL_RULES all; echo "What is worth a post: all (every crossing, the special ones first). The service takes it at its next look."; return 0; }
    social_valid_in "$w" $SOCIAL_RULE_WORDS || { echo "Rules: all, or one or more of ${SOCIAL_RULE_WORDS// /, }, separated by commas" >&2; return 1; }
    seen+="$w "
  done
  for w in $SOCIAL_RULE_WORDS; do case "$seen" in *" $w "*) out+=("$w") ;; esac; done
  cfg_set SOCIAL_RULES "$(IFS=,; echo "${out[*]}")"
  echo "What is worth a post: $(IFS=,; echo "${out[*]}"). The service takes it at its next look."
}

# ---- 0.51.0: the posts' language (SOCIAL_LANG), English until it is set: every post, the summaries' words included
social_py() { if [ "$(id -u)" -eq 0 ] && id "$ZB_USER" >/dev/null 2>&1 && [ "$ZB_USER" != root ]; then runuser -u "$ZB_USER" -- python3 "$SOCIAL_PY" "$@"; else python3 "$SOCIAL_PY" "$@"; fi; }
social_set_lang() {     # social_set_lang [CODE]
  local langs; langs=$(ZENITHBOARD_SOCIAL_TEMPLATES="$SOCIAL_TEMPLATES" python3 "$SOCIAL_PY" langs 2>/dev/null)
  if [ -z "${1:-}" ]; then
    echo "Language of the posts: $(cfg_get SOCIAL_LANG en)"
    echo "Change:  sudo zenithboard social lang CODE   (one of: ${langs:-en})"; return 0
  fi
  case " ${langs:-en} " in *" $1 "*) ;; *) echo "Language of the posts: one of  ${langs:-en}" >&2; return 1 ;; esac
  cfg_set SOCIAL_LANG "$1"
  echo "Language of the posts: $1. The aircraft posts and the summaries' words from the next post; the pictures keep English. See one:  sudo zenithboard social test"
}

# ---- 0.51.0: the owner's own templates, the "custom" style: tags ZenithBoard fills in, [parts] left out when empty
social_template() {     # social_template [list|tags|add TEXT|del N|set TEXT|undo|test [TEXT]]
  local what=${1:-list} n tmp
  [ $# -eq 0 ] || shift
  [ "${1:-}" != -- ] || shift
  case "$what" in
    list|"")
      if [ ! -s "$SOCIAL_TEMPLATES" ]; then
        echo "No template yet. Add one:  sudo zenithboard social template add '{airline} {flight}[, {from} → {to}] at {altitude}. {why}'"
        echo "The tags:  zenithboard social template tags"; return 0
      fi
      echo "Your templates ($SOCIAL_TEMPLATES), one drawn at each post when \"custom\" is among the words of a post ($(cfg_get SOCIAL_SENTENCE factual)):"
      n=0; while IFS= read -r line; do [ -n "${line//[[:space:]]/}" ] || continue; n=$((n + 1)); printf '  %d. %s\n' "$n" "$line"; done < "$SOCIAL_TEMPLATES"
      ZENITHBOARD_SOCIAL_TEMPLATES="$SOCIAL_TEMPLATES" python3 "$SOCIAL_PY" template-check -- "$(cat "$SOCIAL_TEMPLATES")" | grep -v ' usable\.$' || true
      echo "Try them:  sudo zenithboard social template test" ;;
    tags) python3 "$SOCIAL_PY" template-tags ;;
    add|set)
      local text="$*"
      [ -n "${text//[[:space:]]/}" ] || { echo "No template given." >&2; return 1; }
      if [ "$what" = set ] && [ "$text" = none ]; then text=""; fi
      if [ -n "$text" ]; then ZENITHBOARD_SOCIAL_TEMPLATES="$SOCIAL_TEMPLATES" python3 "$SOCIAL_PY" template-check -- "$text" || return 1; fi
      install -d -m 755 "$(dirname "$SOCIAL_TEMPLATES")"
      [ ! -f "$SOCIAL_TEMPLATES" ] || cp -p "$SOCIAL_TEMPLATES" "$SOCIAL_TEMPLATES.bak"
      tmp=$(mktemp "$SOCIAL_TEMPLATES.XXXXXX") || return 1
      { if [ "$what" = add ] && [ -f "$SOCIAL_TEMPLATES" ]; then grep -v '^[[:space:]]*$' "$SOCIAL_TEMPLATES" || true; fi
        [ -z "$text" ] || printf '%s\n' "$text" | grep -v '^[[:space:]]*$' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//'; } > "$tmp"
      chmod 644 "$tmp"; mv -f "$tmp" "$SOCIAL_TEMPLATES"
      echo "Templates: $(grep -c . "$SOCIAL_TEMPLATES" || true). The one before is kept as $SOCIAL_TEMPLATES.bak."
      case ",$(cfg_get SOCIAL_SENTENCE factual)," in *,custom,*|*,random,*) ;; *) echo "To use them, add custom to the words of a post:  sudo zenithboard social sentence $(cfg_get SOCIAL_SENTENCE factual),custom" ;; esac ;;
    del)
      [[ ${1:-} =~ ^[0-9]{1,2}$ ]] && [ -s "$SOCIAL_TEMPLATES" ] || { echo "Which one? The numbers:  zenithboard social template" >&2; return 1; }
      n=$(grep -vc '^[[:space:]]*$' "$SOCIAL_TEMPLATES" || true)
      [ "$1" -ge 1 ] && [ "$1" -le "$n" ] || { echo "There are $n template(s)." >&2; return 1; }
      cp -p "$SOCIAL_TEMPLATES" "$SOCIAL_TEMPLATES.bak"
      tmp=$(mktemp "$SOCIAL_TEMPLATES.XXXXXX") || return 1
      grep -v '^[[:space:]]*$' "$SOCIAL_TEMPLATES" | sed "${1}d" > "$tmp" || true
      chmod 644 "$tmp"; mv -f "$tmp" "$SOCIAL_TEMPLATES"
      echo "Template $1 deleted; $((n - 1)) left. The file before is kept as $SOCIAL_TEMPLATES.bak." ;;
    undo)                           # 0.53.3: the templates before the last change come back; today's become the .bak
      [ -s "$SOCIAL_TEMPLATES.bak" ] || { echo "Nothing to put back: no earlier templates kept ($SOCIAL_TEMPLATES.bak)." >&2; return 1; }
      tmp=$(mktemp "$SOCIAL_TEMPLATES.XXXXXX") || return 1
      if [ -f "$SOCIAL_TEMPLATES" ]; then cp -p "$SOCIAL_TEMPLATES" "$tmp"; else : > "$tmp"; fi
      cp -p "$SOCIAL_TEMPLATES.bak" "$SOCIAL_TEMPLATES"; chmod 644 "$SOCIAL_TEMPLATES"
      chmod 644 "$tmp"; mv -f "$tmp" "$SOCIAL_TEMPLATES.bak"
      echo "Templates put back: $(grep -c . "$SOCIAL_TEMPLATES" || true). The ones they replaced are kept as $SOCIAL_TEMPLATES.bak (undo again to swap back)." ;;
    test) ZENITHBOARD_SOCIAL_TEMPLATES="$SOCIAL_TEMPLATES" social_py template-test -- "$*" ;;
    *) echo "Usage: zenithboard social template [list|tags|add TEXT|del N|set TEXT|undo|test [TEXT]]" >&2; return 1 ;;
  esac
}

# ---- the gap (0.20.0): none by default, every crossing posted once; `social gap 30` for half an hour at least
social_set_gap() {
  if [ -z "${1:-}" ]; then
    echo "Gap between posts: $(social_gap_words)"
    echo "Change:  sudo zenithboard social gap MINUTES   (0 = none: every crossing of the radius is posted, once)"; return 0
  fi
  social_valid_gap "$1" || return 1
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
# 0.33.0: a summary of the week, posted by the service on Sundays from 19:00: aircraft, messages, the busiest day and
# hour, the airlines and type most seen, the posts made. From the statistics' files: never a distance or a direction.
social_set_weekly() { social_summary weekly "${1:-}"; }   # 0.33.0's command, kept

# 0.38.0: three summaries, each on or off, at its own day and time on the Pi's clock, with the posts picked for it:
#   1 the period (aircraft, messages, busiest times, airlines and models), 2 cargo airlines and business jets,
#   3 military aircraft by country, 4 general aviation. The service puts them in one queue, two minutes apart.
SUMMARY_PERIODS="daily weekly monthly"
summary_key() { case "$1" in daily) echo SOCIAL_DAILY ;; weekly) echo SOCIAL_WEEKLY ;; monthly) echo SOCIAL_MONTHLY ;; esac; }
summary_default_at() { case "$1" in daily) echo "21:00" ;; weekly) echo "sun 19:00" ;; monthly) echo "1 09:00" ;; esac; }
summary_default_parts() { case "$1" in daily) echo "1" ;; *) echo "1,2,3,4" ;; esac; }
summary_word() { case "$1" in daily) echo "the last 24 hours" ;; weekly) echo "the week" ;; monthly) echo "the last 30 days" ;; esac; }
# the time a summary is set for, checked: daily HH:MM, weekly DAY HH:MM (mon..sun), monthly D HH:MM (1-28)
summary_valid_at() {   # summary_valid_at PERIOD VALUE -> the value tidied, or non-zero
  local p=$1 v hhmm='([01]?[0-9]|2[0-3]):[0-5][0-9]'
  v=$(printf '%s' "$2" | tr 'A-Z' 'a-z' | tr -s ' ' | sed 's/^ //; s/ $//')
  case "$p" in
    daily)   [[ "$v" =~ ^$hhmm$ ]] || return 1 ;;
    weekly)  [[ "$v" =~ ^(mon|tue|wed|thu|fri|sat|sun)[a-z]*\ $hhmm$ ]] || return 1; v="${v:0:3} ${v##* }" ;;
    monthly) [[ "$v" =~ ^([1-9]|1[0-9]|2[0-8])\ $hhmm$ ]] || return 1 ;;
    *) return 1 ;;
  esac
  printf '%s' "$v"
}
summary_valid_parts() {   # "all", or 1 to 4 comma-separated -> "1,3"; non-zero otherwise
  local v; v=$(printf '%s' "$1" | tr -d ' ' | tr 'A-Z' 'a-z')
  [ "$v" = all ] && { echo "1,2,3,4"; return 0; }
  [[ "$v" =~ ^[1-4](,[1-4])*$ ]] || return 1
  printf '%s' "$v" | tr ',' '\n' | sort -u | paste -sd, -
}
# 0.48.0: when each summary last went out and when it goes next, read from the service's state (root or the service's
# user only: the state folder is theirs). One per day, week or month: a time moved later on a day whose summary
# already went out applies from the next one, and this says so (the owner, 21 October: 21:00 then 23:35, nothing).
summary_when() {   # summary_when [PERIOD] -> "last: ...   next: ..." (all three, and the queue, without PERIOD)
  local out
  [ "$(id -u)" -eq 0 ] || [ "$(id -un)" = "$ZB_USER" ] || return 0
  out=$(python3 "$SOCIAL_PY" summary-when 2>/dev/null) || return 0
  if [ -n "${1:-}" ]; then printf '%s\n' "$out" | sed -n "s/^$1 //p"; else printf '%s\n' "$out"; fi
}
# 0.49.0: why a summary did not go out, in one place (the owner, 22 October: `logs social` shows the last hundred
# lines only, and nothing there said anything about the summaries): each summary as set, when it last went and goes
# next, what it needs (statistics on, sharing on, an account), the service and the code it runs, and its journal lines
# about the summaries and any error, the last two days
summary_why() {
  local p v since
  echo "Summaries, as set and as the service sees them:"
  for p in $SUMMARY_PERIODS; do
    echo "  $(summary_line "$p")"
    v=$(summary_when "$p"); [ -z "$v" ] || echo "           $v"
  done
  v=$(summary_when | sed -n 's/^queue //p'); echo "  In the queue: ${v:-nothing}"
  [ "$(cfg_get STATS 0)" = 1 ] && echo "  Statistics: on" || echo "  Statistics: OFF: no summary can be made (sudo zenithboard stats on)"
  [ "$(social_state)" = on ] && echo "  Social sharing: on" || echo "  Social sharing: OFF: nothing is posted (sudo zenithboard social on)"
  [ -n "$(social_account)" ] && echo "  Bluesky: @$(social_account)" || echo "  Bluesky: no account (sudo zenithboard social setup)"
  since=$(systemctl show -p ActiveEnterTimestamp --value "$SOCIAL_UNIT" 2>/dev/null || true)
  echo "  Service: $(systemctl is-active "$SOCIAL_UNIT" 2>/dev/null || echo unknown)${since:+, since $since}"
  v=$(social_running_version)
  [ -z "$v" ] || echo "  It runs: ZenithBoard $v   (this copy: $ZB_VERSION)"
  if social_runs_old_code; then
    echo "  It still runs the code it started with, from before the last update: the summaries follow its rules, not this copy's."
    echo "  Restart it:  sudo systemctl restart $SOCIAL_UNIT"
  fi
  echo
  # 0.49.1: the starts apart, so that a day of updates (twenty-four starts on 21 October 2026: thirty-two of the forty lines `why` showed) does not push the summary lines out
  local j
  j=$(journalctl -u "$SOCIAL_UNIT" --since "-2 days" --no-pager 2>/dev/null || true)
  echo "The service's lines about the summaries and its errors, the last two days:"
  v=$(grep -iE 'summar|Traceback|Error|could not' <<<"$j" | grep -v 'running ZenithBoard' | tail -30 || true)
  if [ -n "$v" ]; then sed 's/^/  /' <<<"$v"; else echo "  none"; fi
  echo "Its starts, the last two days (each update restarts it):"
  v=$(sed -nE 's/^([A-Z][a-z]{2} +[0-9]+ [0-9]{2}:[0-9]{2}):[0-9]{2} .*running ZenithBoard ([0-9]+[0-9.]*[0-9]).*/\1  \2/p' <<<"$j" | tail -12)
  if [ -n "$v" ]; then sed 's/^/  /' <<<"$v"; else echo "  none"; fi
  [ "$(id -u)" -eq 0 ] || echo "(with sudo: the service's state and its whole journal)"
}
summary_line() {   # one line: the summary, on or off, when and which posts
  local p=$1 k; k=$(summary_key "$p")
  if [ "$(cfg_get "$k" 0)" = 1 ]; then
    printf '%-8s ON   %-10s posts %s\n' "$p" "$(cfg_get "${k}_AT" "$(summary_default_at "$p")")" "$(cfg_get "${k}_PARTS" "$(summary_default_parts "$p")")"
  else
    printf '%-8s off  (%s, posts %s when on)\n' "$p" "$(cfg_get "${k}_AT" "$(summary_default_at "$p")")" "$(cfg_get "${k}_PARTS" "$(summary_default_parts "$p")")"
  fi
}
social_summary() {   # social_summary [PERIOD [on|off|at VALUE|parts LIST]]
  local p=${1:-} what=${2:-} k v
  if [ -z "$p" ]; then
    echo "Summaries (times on this Pi's clock; posts: 1 the period, 2 cargo and business jets, 3 military, 4 general aviation):"
    for p in $SUMMARY_PERIODS; do
      echo "  $(summary_line "$p")"
      v=$(summary_when "$p"); [ -z "$v" ] || echo "           $v"
    done
    v=$(summary_when | sed -n 's/^queue //p'); [ -z "$v" ] || echo "  In the queue: $v"
    [ "$(id -u)" -eq 0 ] || echo "  (with sudo: when each last went out and when it goes next)"
    echo "Each goes once at its time: moved to later today, it goes today; set to a time already past, from the next one."
    echo "Why one did not go out:  sudo zenithboard social summary why"
    echo "Change:  sudo zenithboard social summary daily|weekly|monthly on|off|at TIME|parts LIST|test|post"
    return 0
  fi
  [ "$p" = why ] && { summary_why; return; }
  k=$(summary_key "$p"); [ -n "$k" ] || { echo "A summary is daily, weekly or monthly."; return 1; }
  case "$what" in
    on)  cfg_set "$k" 1 ;;
    off) cfg_set "$k" 0 ;;
    at)
      v=$(summary_valid_at "$p" "${*:3}") || {
        case "$p" in daily) echo "The time: HH:MM, e.g. 21:00" ;; weekly) echo "The day and time: mon..sun HH:MM, e.g. sun 19:00" ;;
          monthly) echo "The day of the month and time: 1 to 28 and HH:MM, e.g. 1 09:00 (29 to 31 are not in every month)" ;; esac
        return 1; }
      cfg_set "${k}_AT" "$v" ;;
    parts)
      v=$(summary_valid_parts "${3:-}") || { echo "The posts: all, or some of 1 2 3 4 comma-separated, e.g. 1,3"; return 1; }
      case ",$v," in *,1,*) ;; *) v="1,$v" ;; esac          # the others follow the first: it is always among them
      cfg_set "${k}_PARTS" "$v" ;;
    "") ;;
    *) echo "Usage: zenithboard social summary $p on|off|at TIME|parts LIST|test|post[2-4]"; return 1 ;;
  esac
  echo "Summary of $(summary_word "$p"): $(summary_line "$p")"
  v=$(summary_when "$p"); [ -z "$v" ] || echo "  $v"
  if [ "$(cfg_get "$k" 0)" = 1 ]; then
    [ "$(cfg_get STATS 0)" = 1 ] || echo "It is made from the statistics, which are OFF: nothing will be posted until  sudo zenithboard stats on"
    [ "$(social_state)" = on ] || echo "Social sharing itself is OFF: the service that posts it starts with  sudo zenithboard social on"
    echo "See it first, nothing posted:  sudo zenithboard social summary $p test"
  fi
}
summary_menu() {
  local c p a v picks
  while true; do
    c=$(wt_menu "Summaries, from the statistics, at their time on this Pi's clock. Posts: 1 the period, 2 cargo and business jets, 3 military, 4 general aviation; two minutes apart. Never a distance or a direction." \
      daily "24 hours: $(summary_line daily | cut -c10-)" weekly "The week: $(summary_line weekly | cut -c10-)" monthly "30 days:  $(summary_line monthly | cut -c10-)" \
      back "Return to the previous menu") || return 0
    case "$c" in daily|weekly|monthly) p=$c ;; *) return 0 ;; esac
    a=$(wt_menu "Summary of $(summary_word "$p").\n\n$(summary_line "$p")" \
      toggle "Switch it $( [ "$(cfg_get "$(summary_key "$p")" 0)" = 1 ] && echo OFF || echo ON )" \
      at "When: $(cfg_get "$(summary_key "$p")_AT" "$(summary_default_at "$p")")" \
      parts "Which posts: $(cfg_get "$(summary_key "$p")_PARTS" "$(summary_default_parts "$p")")" \
      test "See its posts now: draw them and show the texts, post nothing" \
      back "Return to the previous menu") || continue
    case "$a" in
      toggle) if [ "$(cfg_get "$(summary_key "$p")" 0)" = 1 ]; then social_summary "$p" off >/dev/null; else wt_msg "$(social_summary "$p" on)" 14; fi ;;
      at)
        v=$(wt_input "When, on this Pi's clock. $(case "$p" in daily) echo "HH:MM, e.g. 21:00" ;; weekly) echo "A day and a time, e.g. sun 19:00" ;; monthly) echo "A day of the month, 1 to 28, and a time, e.g. 1 09:00" ;; esac)" "$(cfg_get "$(summary_key "$p")_AT" "$(summary_default_at "$p")")") || continue
        wt_msg "$(social_summary "$p" at "$v")" 9 ;;
      parts)
        picks=$(wt_check "Which posts for the summary of $(summary_word "$p") (Space = tick). The first always goes; the others follow it, two minutes apart." \
          1 "The period: aircraft, messages, busiest times, airlines and models" ON \
          2 "Cargo airlines and business jets, with their countries" "$(case ",$(cfg_get "$(summary_key "$p")_PARTS" "$(summary_default_parts "$p")")," in *,2,*) echo ON ;; *) echo OFF ;; esac)" \
          3 "Military aircraft by country" "$(case ",$(cfg_get "$(summary_key "$p")_PARTS" "$(summary_default_parts "$p")")," in *,3,*) echo ON ;; *) echo OFF ;; esac)" \
          4 "General aviation: helicopters, light aircraft, gliders, drones" "$(case ",$(cfg_get "$(summary_key "$p")_PARTS" "$(summary_default_parts "$p")")," in *,4,*) echo ON ;; *) echo OFF ;; esac)") || continue
        picks=$(printf '%s' "$picks" | tr -d '"' | tr ' ' ',')
        wt_msg "$(social_summary "$p" parts "${picks:-1}")" 9 ;;
      test) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" summary-test "$p"; read -rp "Press Enter to continue..." _ ;;
    esac
  done
}
# 0.29.0: the shape of the post's words: factual (as before), story, board, spotter, lookup; several, comma-separated,
# or random: one is drawn at each post. Templates filled from the flight's data; never the distance or direction.
SOCIAL_SENTENCES="factual story board spotter lookup custom"   # custom: the owner's templates (0.51.0)
social_ticked() { case ",$(cfg_get SOCIAL_SENTENCE factual)," in *",$1,"*|*",random,"*) echo ON ;; *) echo OFF ;; esac; }
social_set_sentence() {
  local v=${1:-} w ok=1
  if [ -n "$v" ]; then
    v=$(printf '%s' "$v" | tr 'A-Z ' 'a-z,' | tr -s ',' | sed 's/^,//; s/,$//')
    if [ "$v" != random ]; then
      for w in ${v//,/ }; do case " $SOCIAL_SENTENCES " in *" $w "*) ;; *) ok=0 ;; esac; done
    fi
    [ "$ok" = 1 ] || { echo "Sentence: one or more of  $SOCIAL_SENTENCES  (comma-separated), or random"; return 1; }
    cfg_set SOCIAL_SENTENCE "$v"
    systemctl try-restart "$SOCIAL_UNIT.service" 2>/dev/null || true
  fi
  echo "Post sentence: $(cfg_get SOCIAL_SENTENCE factual)$(case "$(cfg_get SOCIAL_SENTENCE factual)" in *,*|random) echo "  (one drawn at each post)" ;; esac)"
}
# 0.27.0: the town names of the maps from the region's own list, made here from GeoNames' country files: every
# populated place within 400 km, ranked by population or, where GeoNames knows none, by rank (capital, province seat,
# district seat, village). The shipped lists name the places whose population GeoNames knows: a map over a region
# where it knows few (Indonesia) was left almost bare. Off by default; on downloads the files once (about 24 MB
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
      chown "$ZB_USER:$ZB_USER" "$f" 2>/dev/null || true; chmod 600 "$f" 2>/dev/null || true
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
  wt_msg "Saved. Picture: $look, $(or_text "$(cfg_get SOCIAL_THEME "")" "the wall's colour ($(wall_theme))"), $(cfg_get SOCIAL_MAP normal) map.\n\nNext: 6 Try it, or post now -> 1 Try it (or  sudo zenithboard social test): draws the picture and shows the text, posts nothing.\nThen: 1 Switch sharing ON (or  sudo zenithboard social on): starts posting." 13
}
social_rule_on() { [ "$1" = all ] && case ",$(cfg_get SOCIAL_RULES "")," in *",all,"*|*",any,"*) echo ON; return ;; esac; case ",$(cfg_get SOCIAL_RULES "$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); import social; print(social.DEFAULTS["SOCIAL_RULES"])' "$ZB_HOME/flightinfo")")," in *",$1,"*) echo ON ;; *) echo OFF ;; esac; }

social_try_account() { python3 "$SOCIAL_PY" check 2>&1; }      # "bluesky: ok, signed in as ..." or "bluesky: FAILED: ..."; a function so the tests can stand in for Bluesky

social_on() {
  [ -n "$(social_account)" ] || { echo "No Bluesky account yet: run  sudo zenithboard social setup  first."; return 1; }
  social_need_tools || return 1
  social_prepare_dir || { echo "Could not make $SOCIAL_DIR"; return 1; }
  # 0.53.7: the account is tried before it is switched on. A refused app password used to give "Social sharing is ON"
  # and only the journal knew; an unreachable Bluesky (the Pi offline for now) is said and does not stop it
  local tried; tried=$(social_try_account)
  if printf '%s' "$tried" | grep -q -E 'FAILED: (400|401|403) '; then
    echo "$tried"
    echo "Bluesky refused this account, so sharing was NOT switched on. Check the handle and the app password with  sudo zenithboard social setup  and try again."
    return 1
  elif printf '%s' "$tried" | grep -q FAILED; then
    echo "$tried"
    echo "!! Bluesky could not be reached just now, so the account was not checked. Sharing is switched on anyway: posts wait for the network."
  fi
  cfg_set SOCIAL 1; social_install_units
  echo "Social sharing is ON: Bluesky @$(social_account), radius $(cfg_get SOCIAL_RADIUS_KM) km, once per crossing, gap between posts: $(social_gap_words), rules: $(cfg_get SOCIAL_RULES)."
  echo "Watch it:  zenithboard logs social      Stop it:  sudo zenithboard social off"
}
social_off() { cfg_set SOCIAL 0; social_remove_units; echo "Social sharing is OFF. The accounts are kept (remove them: sudo zenithboard social remove)."; }
social_remove() {      # social_remove [--yes]: the account secret, the state and the service, after a typed word
  local w
  if [ "${1:-}" != --yes ]; then
    # the audit of 22-23 October 2026: a plain yes/no, one line above Return, destroyed the history with the account
    echo "This forgets the Bluesky account on this Pi (its app password), stops the service and deletes its state: the"
    echo "history behind 'rare' and 'farthest' (30 days), the posts' memory and the map tiles. Your Bluesky account stays."
    read -r -p "Type remove to go on: " w || w=""
    [ "$w" = remove ] || { echo "Nothing was changed."; return 1; }
  fi
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
  local st since
  st=$(systemctl is-active "$SOCIAL_UNIT" 2>/dev/null || echo unknown)
  since=$(systemctl show -p ActiveEnterTimestamp --value "$SOCIAL_UNIT" 2>/dev/null || true)
  if [ "$st" = active ] && [ -n "$since" ]; then
    echo "Service: active since $since"
    if social_runs_old_code; then
      echo "  It runs the code from before the last update. Restart it:  sudo systemctl restart $SOCIAL_UNIT"
    fi
  else
    echo "Service: $st"
  fi
}
# The version the service said it runs when it last started (its first journal line), or nothing.
social_running_version() {
  journalctl -u "$SOCIAL_UNIT" --since "-30 days" --no-pager 2>/dev/null | sed -nE 's/.*running ZenithBoard ([0-9]+[0-9.]*[0-9]).*/\1/p' | tail -1
}
# A running service keeps the code it started with. True when the code on disk is newer than its start, or when it
# said another version than this copy's. Seen on the real Pi on 22 October 2026: the files were 0.49.0 and the service
# still 0.47.0 from 00:11, so the summaries followed 0.47.0's rules.
social_runs_old_code() {
  local since started code v
  [ "$(systemctl is-active "$SOCIAL_UNIT" 2>/dev/null)" = active ] || return 1
  since=$(systemctl show -p ActiveEnterTimestamp --value "$SOCIAL_UNIT" 2>/dev/null || true)
  started=$(date -d "$since" +%s 2>/dev/null || echo 0)
  code=$(stat -c %Y "$SOCIAL_PY" "$ZB_HOME/flightinfo/social_week.py" "$ZB_HOME/flightinfo/social_card.py" "$ZB_HOME/tools/social-render.js" "$ZB_HOME/flightinfo/static/format.js" 2>/dev/null | sort -n | tail -1)
  if [ "${started:-0}" -gt 0 ] && [ "${code:-0}" -gt "$started" ]; then return 0; fi
  v=$(social_running_version)
  [ -n "$v" ] && [ "$v" != "$ZB_VERSION" ]
}

# ---- the menu
# The posts' language, by name (the audit of 22-23 October 2026: it was a code typed in a box)
social_lang_menu() {
  local c n w args=() cur; cur=$(cfg_get SOCIAL_LANG en)
  for c in $(ZENITHBOARD_SOCIAL_TEMPLATES="$SOCIAL_TEMPLATES" python3 "$SOCIAL_PY" langs 2>/dev/null || echo en); do
    n=$c; for w in $CONSOLE_LANG_NAMES; do [ "${w%%:*}" = "$c" ] && n=${w#*:}; done
    args+=("$c" "${n//_/ }$( [ "$c" = "$cur" ] && echo "  (now)")")
  done
  c=$(wt_menu "The language of the posts: the aircraft posts and the summaries' words. The pictures keep English." "${args[@]}" back "Return to the previous menu") || return 0
  [ "$c" = back ] && return 0
  wt_msg "$(social_set_lang "$c" 2>&1 || echo "Nothing was changed.")" 10
}
# 0.54.8 (the audit of 22-23 October 2026): fourteen entries and Return under the fold became seven and Return, grouped
# like the console's Sharing page; the destructive one is inside "The account", never just above Return.
social_menu() {
  local c
  while true; do
    c=$(wt_menu "Social sharing: $(social_state)    Bluesky: $(or_text "$(social_account)" "no account")    Picture: $(social_look)\nRadius: $(cfg_get SOCIAL_RADIUS_KM 15) km    Gap: $(social_gap_words)    Area: $(or_text "$(cfg_get SOCIAL_AREA "")" "(none)")\nRules: $(cfg_get SOCIAL_RULES rare,military,helicopter,heavy,farthest)\n\nPosts a picture of the wall and a short text when something worth it flies over. Nothing leaves the Pi until you switch it on." \
      toggle "1  Switch sharing $( [ "$(social_state)" = on ] && echo OFF || echo ON )" \
      account "2  The account: set up, change or remove" \
      words "3  Words and rules: place name, radius, gap, what is worth a post" \
      look "4  How a post looks: picture, words, language, templates, links" \
      weekly "5  Summaries: the day, the week, the last 30 days ($(for p in $SUMMARY_PERIODS; do [ "$(cfg_get "$(summary_key "$p")" 0)" = 1 ] && printf '%s ' "$p"; done | sed 's/ $//; s/^$/all off/'))" \
      try "6  Try it, or post now" \
      status "7  Status" \
      back "Return to the previous menu") || return 0
    case "$c" in
      toggle) clear; if [ "$(social_state)" = on ]; then social_off; else social_on; fi; read -rp "Press Enter to continue..." _ ;;
      account)
        local a
        a=$(wt_menu "The Bluesky account: $(or_text "$(social_account)" "none yet")" \
          setup "1  Set up or change the account (handle and app password)" \
          remove "2  Remove: account, history and service (asks you to type remove)" \
          status "3  Status" \
          back "Return to the previous menu") || continue
        case "$a" in
          setup) social_setup || true ;;
          remove) clear; social_remove || true; read -rp "Press Enter to continue..." _ ;;
          status) clear; social_status; read -rp "Press Enter to continue..." _ ;;
        esac ;;
      words) social_setup_words && wt_msg "Saved." 7 || true ;;
      look) social_look_menu ;;
      weekly) summary_menu ;;
      try)
        local w
        w=$(wt_menu "Try a post, or post one now." \
          test "1  Try it: draw the picture and show the text, post nothing" \
          post "2  Post now, once (on Bluesky, for real)" \
          back "Return to the previous menu") || continue
        case "$w" in
          test) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" test; read -rp "Press Enter to continue..." _ ;;
          post) clear; social_need_tools && social_prepare_dir && sudo -u "$ZB_USER" python3 "$SOCIAL_PY" post; read -rp "Press Enter to continue..." _ ;;
        esac ;;
      status) clear; social_status; read -rp "Press Enter to continue..." _ ;;
      *) return 0 ;;
    esac
  done
}
social_look_menu() {
  local c
  while true; do
    c=$(wt_menu "How a post looks." \
      picture "1  The picture: dot-matrix or split-flap, colour, map" \
      sentence "2  The words of a post: $(cfg_get SOCIAL_SENTENCE factual)" \
      lang "3  Language of the posts: $(cfg_get SOCIAL_LANG en)" \
      template "4  Your own templates: $(grep -c . "$SOCIAL_TEMPLATES" 2>/dev/null || echo 0)" \
      photolink "5  Link to the Planespotters photo page: $( [ "$(cfg_get SOCIAL_PHOTOLINK 0)" = 1 ] && echo ON || echo OFF )" \
      places "6  Town names from the region's own list (GeoNames, downloaded once): $( [ "$(cfg_get SOCIAL_PLACES 0)" = 1 ] && echo ON || echo OFF )" \
      back "Return to the previous menu") || return 0
    case "$c" in
      picture) social_setup_picture || true ;;
      photolink) social_set_photolink "$( [ "$(cfg_get SOCIAL_PHOTOLINK 0)" = 1 ] && echo off || echo on )" >/dev/null; wt_msg "$(social_set_photolink)" 10 ;;
      sentence)
        local picks
        picks=$(wt_check "The words of a post. Tick one or more (Space = tick): with several, one is drawn at each post.\n(On RYR5ZK, Brussels to Pisa, above Trémery.)" \
          factual "Flight Ryanair #RYR5ZK · Boeing 737-800 · Brussels → Pisa · altitude 10 570 m" "$(social_ticked factual)" \
          story "A Ryanair Boeing 737-800 bound for Pisa from Brussels has just crossed the sky..." "$(social_ticked story)" \
          board "✈ #RYR5ZK · EI-ENK / Brussels → Pisa / Boeing 737-800 · 10 570 m · 720 km/h" "$(social_ticked board)" \
          spotter "EI-ENK, a Ryanair Boeing 737-800, flying Brussels → Pisa as #RYR5ZK: ..." "$(social_ticked spotter)" \
          lookup "Look up, Trémery! Ryanair #RYR5ZK is passing 10.6 km overhead..." "$(social_ticked lookup)" \
          custom "Your own templates (entry 4): $(grep -c . "$SOCIAL_TEMPLATES" 2>/dev/null || echo 0)" "$(social_ticked custom)") || continue
        picks=$(printf '%s' "$picks" | tr -d '"' | tr ' ' ',')
        [ -n "$picks" ] || picks=factual
        wt_msg "$(social_set_sentence "$picks")" 8 ;;
      lang) social_lang_menu ;;
      template)
        local tc tt
        tc=$(wt_menu "Your own templates: posts in your words, with tags ZenithBoard fills in ({airline}, {from}, {to}, {altitude}...). A [part] is left out when a tag inside it is empty. Used when custom is ticked in 2 The words of a post." \
          list "1  See them" add "2  Add one" del "3  Delete one" clear "4  Delete them all" undo "5  Put back the ones before the last change" \
          test "6  Try them on an aircraft overhead (posts nothing)" tags "7  The tags" back "Return to the previous menu") || continue
        case "$tc" in
          list) clear; social_template list; read -rp "Press Enter to continue..." _ ;;
          add) tt=$(wt_input "The template, on one line. Example:
{flag} {airline} {flight}[, {from} → {to}] · {type} at {altitude}. {why}" "") || continue
               clear; social_template add "$tt"; read -rp "Press Enter to continue..." _ ;;
          del) tt=$(wt_input "The number of the template to delete (menu 1 shows them):" "") || continue
               clear; social_template del "$tt"; read -rp "Press Enter to continue..." _ ;;
          clear) wt_yesno "Delete all your templates?\n\nThe posts go on with the other words you ticked (factual when none is left). They are kept as a .bak: item 5 puts them back." 11 || continue
                 clear; social_template set none; read -rp "Press Enter to continue..." _ ;;
          undo) clear; social_template undo; read -rp "Press Enter to continue..." _ ;;
          test) clear; social_template test; read -rp "Press Enter to continue..." _ ;;
          tags) clear; social_template tags; read -rp "Press Enter to continue..." _ ;;
        esac ;;
      places)
        if [ "$(cfg_get SOCIAL_PLACES 0)" = 1 ]; then
          wt_yesno "Town names come from the region's own list.\n\nGo back to the lists shipped with ZenithBoard (and delete the region's list)?" 10 && social_set_places off >/dev/null
        elif wt_yesno "Name the towns on the maps from the region's own list?\n\nThe Pi downloads GeoNames' files of the countries within 400 km (about 24 MB around Metz, once) and keeps every populated place, ranked by population or, where it is unknown, by rank (capital, province seat, village). Useful where the shipped lists know few towns. Nothing about this Pi is sent." 14; then
          clear; social_set_places on; read -rp "Press Enter to continue..." _
        fi ;;
      *) return 0 ;;
    esac
  done
}
