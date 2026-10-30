# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Telegram messages (0.99.6, asked for by the owner on 30 October 2026): menu 7 Options -> 5 Telegram, and
# `zenithboard telegram ...`; its finer settings in the web console (Sharing).
#
# Text messages to one private chat, the owner's or his group's: each aircraft crossing the sharing radius (the Bluesky
# posts' radius and their rule, once per crossing), and each emergency squawk (7500, 7600, 7700) the antenna hears,
# anywhere in its range, once per flight and code. Off by default. The work is done by flightinfo/telegram.py, run as a
# service under the wall's user; this file is the setup wizard, the switch, and the commands.
#
# The bot's token (from Telegram's @BotFather) and the chat's id live in $ZB_ETC/telegram.env, owned by root, readable
# by the zenithboard group (the service runs as that user), mode 0640. Never in config.env, never in a log, never on a
# command line, never typed into the console. `telegram remove` deletes that file. The owner's own templates are his
# words, no secret: $ZB_ETC/telegram-crossing.txt and telegram-squawk.txt.
TELEGRAM_SECRETS="${ZENITHBOARD_TELEGRAM_SECRETS:-${ZB_ETC:-/etc/zenithboard}/telegram.env}"
TELEGRAM_DIR="${ZENITHBOARD_TELEGRAM_DIR:-/var/lib/zenithboard/telegram}"
TELEGRAM_UNIT=zenithboard-telegram
TELEGRAM_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
TELEGRAM_PY="$ZB_HOME/flightinfo/telegram.py"
TELEGRAM_KINDS="crossing squawk"
TELEGRAM_RULE_WORDS="military helicopter heavy"

telegram_state() { [ "$(cfg_get TELEGRAM 0)" = 1 ] && echo on || echo off; }
telegram_secret_get() { [ -r "$TELEGRAM_SECRETS" ] || return 0; sed -n -E "s/^$1=\"?([^\"]*)\"?$/\1/p" "$TELEGRAM_SECRETS" | head -1; }
telegram_chat() { telegram_secret_get TELEGRAM_CHAT_TITLE; }
telegram_ready() { [ -n "$(telegram_secret_get TELEGRAM_BOT_TOKEN)" ] && [ -n "$(telegram_secret_get TELEGRAM_CHAT_ID)" ]; }
telegram_valid_token() { [[ ${1:-} =~ ^[0-9]{5,15}:[A-Za-z0-9_-]{30,60}$ ]]; }
telegram_valid_chat() { [[ ${1:-} =~ ^-?[0-9]{1,20}$ ]]; }
telegram_template_file() { echo "${ZB_ETC:-/etc/zenithboard}/telegram-$1.txt"; }
# the service's code, with this Pi's paths (a test points them elsewhere)
telegram_py() {
  ZENITHBOARD_TELEGRAM_SECRETS="$TELEGRAM_SECRETS" ZENITHBOARD_TELEGRAM_DIR="$TELEGRAM_DIR" ZENITHBOARD_ETC="${ZB_ETC:-/etc/zenithboard}" \
    python3 "$TELEGRAM_PY" "$@"
}

# ---- the secrets file: written whole, never appended to, never world-readable
telegram_secrets_write() {   # telegram_secrets_write KEY=VALUE...  (every key; what is not given is dropped)
  local old tmp
  old=$(umask); umask 077
  install -d -m 755 "$(dirname "$TELEGRAM_SECRETS")" 2>/dev/null
  tmp=$(mktemp "${TELEGRAM_SECRETS}.XXXXXX") || { umask "$old"; return 1; }
  printf '# ZenithBoard Telegram messages: the bot token and the chat. root:%s, mode 0640. Never in config.env, never in a log.\n' "$ZB_USER" > "$tmp"
  printf '%s\n' "$@" | sed -E 's/^([A-Z_]+)=(.*)$/\1="\2"/' >> "$tmp"
  umask "$old"
  chown "root:$ZB_USER" "$tmp" 2>/dev/null || true; chmod 640 "$tmp"
  mv "$tmp" "$TELEGRAM_SECRETS"
}

# ---- the service
telegram_install_units() {
  [ -f "$ZB_HOME/systemd/$TELEGRAM_UNIT.service" ] || return 0
  install -d -m 755 "$TELEGRAM_UNIT_DIR"
  install -m 644 "$ZB_HOME/systemd/$TELEGRAM_UNIT.service" "$TELEGRAM_UNIT_DIR/"
  systemctl daemon-reload; systemctl enable "$TELEGRAM_UNIT.service" >/dev/null 2>&1 || true
  systemctl restart "$TELEGRAM_UNIT.service" >/dev/null 2>&1 || true      # restart: the code just installed, not the old
}
telegram_remove_units() {
  systemctl disable --now "$TELEGRAM_UNIT.service" >/dev/null 2>&1 || true
  rm -f "$TELEGRAM_UNIT_DIR/$TELEGRAM_UNIT.service"; systemctl daemon-reload 2>/dev/null || true
}
telegram_prepare_dir() {
  [ -d "$TELEGRAM_DIR" ] || install -d -m 750 "$TELEGRAM_DIR" 2>/dev/null || return 1
  [ "$(id -u)" -ne 0 ] || chown "$ZB_USER:$ZB_USER" "$TELEGRAM_DIR" 2>/dev/null || true
}

telegram_on() {
  telegram_ready || { echo "No Telegram bot or chat yet: run  sudo zenithboard telegram setup  first."; return 1; }
  telegram_prepare_dir || { echo "Could not make $TELEGRAM_DIR"; return 1; }
  cfg_set TELEGRAM 1; telegram_install_units
  echo "Telegram messages are ON, to $(or_text "$(telegram_chat)" "the chat set up"): $(telegram_words)."
  echo "Watch it:  zenithboard logs telegram      Stop it:  sudo zenithboard telegram off"
}
telegram_off() { cfg_set TELEGRAM 0; telegram_remove_units; echo "Telegram messages are OFF. The bot and the chat are kept (forget them: sudo zenithboard telegram remove)."; }
telegram_remove() {     # telegram_remove [--yes]: the token, the chat, the state and the service, after a typed word
  local w
  if [ "${1:-}" != --yes ]; then
    echo "This forgets the Telegram bot's token and the chat on this Pi, stops the service and deletes what it remembers"
    echo "(the crossings and squawks already written about). Your bot and your chat stay in Telegram; your templates stay here."
    read -r -p "Type remove to go on: " w || w=""
    [ "$w" = remove ] || { echo "Nothing was changed."; return 1; }
  fi
  telegram_off >/dev/null
  rm -f "$TELEGRAM_SECRETS"; rm -rf "$TELEGRAM_DIR"
  echo "Telegram messages removed: the token, the chat, the state and the service are gone. To revoke the token itself: @BotFather, /revoke."
}
# what goes out, in one line
telegram_words() {
  local a="" b="" r; r=$(cfg_get TELEGRAM_RULES all)
  [ "$(cfg_get TELEGRAM_CROSSINGS 1)" = 1 ] && a="the aircraft crossing $(cfg_get SOCIAL_RADIUS_KM 15) km ($( [ "$r" = all ] && echo "every crossing" || echo "${r//,/, }"))"
  [ "$(cfg_get TELEGRAM_SQUAWKS 1)" = 1 ] && b="the emergency squawks anywhere in range"
  if [ -n "$a" ] && [ -n "$b" ]; then echo "$a, and $b"; elif [ -n "$a$b" ]; then echo "$a$b"; else echo "nothing: crossings and squawks are both off"; fi
}

# ---- the wizard: the token, tried; then the chat, chosen among those that wrote to the bot; a first message
telegram_setup() {
  local tok have r
  have=$(telegram_secret_get TELEGRAM_BOT_TOKEN)
  wt_msg "Telegram messages need a bot of your own, made in Telegram in a minute:\n\n  1. In Telegram, open @BotFather and send  /newbot\n  2. Give it a name, then a username ending in bot\n  3. BotFather answers with the bot's TOKEN (123456789:AA...)\n\nThe next screen asks for that token. It stays on this Pi only (root, never in a log); the web console never asks for it." 16 || return 1
  tok=$(whiptail --title "$WT_TITLE" --passwordbox "The bot's token, as @BotFather gave it (digits, a colon, then letters).$( [ -n "$have" ] && printf '\n\nLeave empty to keep the one saved.')" 12 76 3>&1 1>&2 2>&3) || return 1
  tok=$(printf '%s' "$tok" | tr -d '[:space:]')
  [ -n "$tok" ] || tok="$have"
  telegram_valid_token "$tok" || { wt_msg "That does not look like a bot token (digits, a colon, then about 35 letters, digits, - or _). Nothing was saved." 9; return 1; }
  telegram_secrets_write "TELEGRAM_BOT_TOKEN=$tok" "TELEGRAM_CHAT_ID=$(telegram_secret_get TELEGRAM_CHAT_ID)" "TELEGRAM_CHAT_TITLE=$(telegram_secret_get TELEGRAM_CHAT_TITLE)" \
    || { wt_msg "Could not write $TELEGRAM_SECRETS" 8; return 1; }
  clear; echo "Trying the bot..."; echo
  r=$(telegram_py check 2>&1); echo "$r"; echo
  if printf '%s' "$r" | grep -q FAILED; then
    echo "Telegram refused this token. It is saved; fix it with  sudo zenithboard telegram setup  and try again."
    read -rp "Press Enter to continue..." _; return 1
  fi
  telegram_choose_chat "$(printf '%s' "$r" | sed -n 's/^OK: the bot \(@[A-Za-z0-9_]*\).*/\1/p')" || return 1
  clear; telegram_py hello; echo
  if [ "$(telegram_state)" = on ]; then
    systemctl restart "$TELEGRAM_UNIT.service" >/dev/null 2>&1 || true
    read -rp "The service takes the new chat now. Press Enter to continue..." _
  elif wt_yesno "The bot wrote to $(telegram_chat).\n\nSwitch the messages on now? $(telegram_words).\n\nThe finer settings (which crossings, the language, your own templates) are in the web console, Sharing." 13; then
    clear; telegram_on; read -rp "Press Enter to continue..." _
  fi
  return 0
}
# The chat: a private one (the owner sent /start to the bot) or a group (the bot added, /start@bot sent in it). The bot
# only sees what was written to it since; the list is read from Telegram, never typed.
telegram_choose_chat() {   # telegram_choose_chat [@BOTNAME]
  local bot="${1:-your bot}" list items=() id kind name c i
  while true; do
    wt_msg "Now the chat the messages go to.\n\n  - Just you: in Telegram, open $bot and send it  /start\n  - A group: add $bot to the group, then send  /start$( [ "$bot" = "your bot" ] || echo "$bot" )  in it\n\nThen press OK: the next screen lists the chats that wrote to the bot." 14 || return 1
    list=$(telegram_py chats 2>/dev/null)
    items=()
    while IFS=$'\t' read -r id kind name; do
      telegram_valid_chat "$id" || continue
      items+=("$id" "$( [ "$kind" = private ] && echo "you: $name" || echo "$kind: $name")")
    done <<< "$list"
    if [ "${#items[@]}" -eq 0 ]; then
      wt_yesno "No chat has written to the bot yet (or Telegram could not be reached).\n\nLook again?" 10 || return 1
      continue
    fi
    c=$(wt_menu "Which chat gets the messages?" "${items[@]}" again "Look again (wrote to the bot just now)") || return 1
    [ "$c" = again ] && continue
    for ((i = 0; i < ${#items[@]}; i += 2)); do [ "${items[i]}" = "$c" ] && name="${items[i+1]#*: }"; done
    telegram_secrets_write "TELEGRAM_BOT_TOKEN=$(telegram_secret_get TELEGRAM_BOT_TOKEN)" "TELEGRAM_CHAT_ID=$c" "TELEGRAM_CHAT_TITLE=${name//\"/}" || return 1
    return 0
  done
}

# ---- one setting at a time (the console's controls run these)
telegram_set_switch() {   # telegram_set_switch KEY WORDS on|off
  case "${3:-}" in
    on)  cfg_set "$1" 1 ;;
    off) cfg_set "$1" 0 ;;
    "")  echo "$2: $( [ "$(cfg_get "$1" 1)" = 1 ] && echo on || echo off)"; return 0 ;;
    *)   echo "Usage: zenithboard telegram ${1#TELEGRAM_} on|off" | tr '[:upper:]' '[:lower:]' >&2; return 1 ;;
  esac
  echo "$2: $3. The service takes it at its next look."
}
telegram_set_rules() {    # telegram_set_rules [all|LIST]
  local w seen=" " out=()
  if [ -z "${1:-}" ]; then echo "Which crossings: $(cfg_get TELEGRAM_RULES all)   (all, or some of ${TELEGRAM_RULE_WORDS// /,})"; return 0; fi
  for w in ${1//,/ }; do
    [ "$w" = all ] && { cfg_set TELEGRAM_RULES all; echo "Which crossings: all, every crossing of the sharing radius."; return 0; }
    case " $TELEGRAM_RULE_WORDS " in *" $w "*) seen+="$w " ;; *) echo "Which crossings: all, or one or more of ${TELEGRAM_RULE_WORDS// /, }, separated by commas" >&2; return 1 ;; esac
  done
  for w in $TELEGRAM_RULE_WORDS; do case "$seen" in *" $w "*) out+=("$w") ;; esac; done
  cfg_set TELEGRAM_RULES "$(IFS=,; echo "${out[*]}")"
  echo "Which crossings: $(cfg_get TELEGRAM_RULES all)."
}
telegram_set_lang() {     # telegram_set_lang [CODE|posts]
  local langs; langs=$(python3 "$SOCIAL_PY" langs 2>/dev/null)
  if [ -z "${1:-}" ]; then echo "Language of the messages: $(or_text "$(cfg_get TELEGRAM_LANG "")" "the posts' ($(cfg_get SOCIAL_LANG en))")"; return 0; fi
  if [ "$1" = posts ]; then cfg_set TELEGRAM_LANG ""; echo "Language of the messages: the posts' ($(cfg_get SOCIAL_LANG en))."; return 0; fi
  case " $langs " in *" $1 "*) ;; *) echo "Language: posts (the posts' own), or one of: $langs" >&2; return 1 ;; esac
  cfg_set TELEGRAM_LANG "$1"; echo "Language of the messages: $1."
}
telegram_set_units() {    # telegram_set_units [metric|imperial|aviation|posts]
  case "${1:-}" in
    "") echo "Units of the messages: $(or_text "$(cfg_get TELEGRAM_UNITS "")" "the posts'")" ;;
    posts) cfg_set TELEGRAM_UNITS ""; echo "Units of the messages: the posts'." ;;
    metric|imperial|aviation) cfg_set TELEGRAM_UNITS "$1"; echo "Units of the messages: $1." ;;
    *) echo "Units: metric, imperial, aviation, or posts (the posts' own)" >&2; return 1 ;;
  esac
}
# The owner's own template for each kind of message: a whole message, lines kept. Saving keeps the one before as .bak.
telegram_template() {     # telegram_template KIND [show|default|tags|set TEXT|test [TEXT]|undo]
  local kind="${1:-}" what="${2:-show}" f tmp text
  case " $TELEGRAM_KINDS " in *" $kind "*) ;; *) echo "Which template? crossing or squawk" >&2; return 1 ;; esac
  f=$(telegram_template_file "$kind"); shift 2 2>/dev/null || shift $#
  [ "${1:-}" = "--" ] && shift
  case "$what" in
    show)
      if [ -s "$f" ]; then echo "Your $kind template ($f):"; cat "$f"; echo; telegram_py template-check "$kind" -- "$(cat "$f")" | grep -v '^Usable' || true
      else echo "No $kind template of your own: the default is used. See it:  zenithboard telegram template $kind default"; fi ;;
    default) telegram_py template-default "$kind" ;;
    tags) telegram_py template-tags ;;
    test) telegram_py template-test "$kind" -- "$*" ;;
    set)
      text="$*"
      if [ -n "$text" ] && [ "$text" != none ]; then telegram_py template-check "$kind" -- "$text" || return 1; fi
      install -d -m 755 "$(dirname "$f")"
      [ ! -f "$f" ] || cp -p "$f" "$f.bak"
      if [ -z "$text" ] || [ "$text" = none ]; then rm -f "$f"; echo "Your $kind template is deleted: the default is used. The one before is kept as $f.bak (undo puts it back)."; return 0; fi
      tmp=$(mktemp "$f.XXXXXX") || return 1
      printf '%s\n' "$text" > "$tmp"; chmod 644 "$tmp"; mv -f "$tmp" "$f"
      echo "Your $kind template is saved. The one before is kept as $f.bak (undo puts it back)." ;;
    undo)
      [ -e "$f.bak" ] || { echo "Nothing to put back: no earlier $kind template kept ($f.bak)." >&2; return 1; }
      tmp=$(mktemp "$f.XXXXXX") || return 1
      if [ -f "$f" ]; then cp -p "$f" "$tmp"; else : > "$tmp"; fi
      cp -p "$f.bak" "$f"; chmod 644 "$f"; mv -f "$tmp" "$f.bak"; [ -s "$f" ] || rm -f "$f"
      echo "Your previous $kind template is back$( [ -s "$f" ] || echo " (none: the default)"). The one it replaced is kept as $f.bak." ;;
    *) echo "Usage: zenithboard telegram template crossing|squawk [show|default|tags|set TEXT|test [TEXT]|undo]" >&2; return 1 ;;
  esac
}

# Run as root, the status is read as the service's own user, who can read the token file and the state folder.
telegram_status() {
  if [ "$(id -u)" -eq 0 ] && id "$ZB_USER" >/dev/null 2>&1 && [ "$ZB_USER" != root ]; then
    runuser -u "$ZB_USER" -- env ZENITHBOARD_TELEGRAM_SECRETS="$TELEGRAM_SECRETS" ZENITHBOARD_TELEGRAM_DIR="$TELEGRAM_DIR" ZENITHBOARD_ETC="${ZB_ETC:-/etc/zenithboard}" python3 "$TELEGRAM_PY" status
  else
    telegram_py status
  fi
  # the chat's name from here, never from the service: what telegram.env holds stays out of its journal
  [ -z "$(telegram_chat)" ] || echo "  Chat: $(telegram_chat)"
  [ -f "$TELEGRAM_UNIT_DIR/$TELEGRAM_UNIT.service" ] || return 0
  echo "Service: $(systemctl is-active "$TELEGRAM_UNIT" 2>/dev/null || echo unknown)$(s=$(systemctl show -p ActiveEnterTimestamp --value "$TELEGRAM_UNIT" 2>/dev/null); [ -z "$s" ] || echo " since $s")"
}

telegram_menu() {
  local c
  while true; do
    c=$(wt_menu "Telegram messages: $(telegram_state)    Chat: $(or_text "$(telegram_chat)" "none yet")\n$(telegram_words)\n\nText messages to your own chat or group: the aircraft crossing the sharing radius, and the emergency squawks (7500, 7600, 7700) anywhere the antenna hears them. The finer settings are in the web console, Sharing." \
      toggle "1  Switch the messages $( [ "$(telegram_state)" = on ] && echo OFF || echo ON )" \
      setup "2  The bot and the chat: set up or change" \
      try "3  Try the messages (sends nothing), or send a test" \
      status "4  Status" \
      remove "5  Remove: token, chat and service (asks you to type remove)" \
      back "Return to the previous menu") || return 0
    case "$c" in
      toggle) clear; if [ "$(telegram_state)" = on ]; then telegram_off; else telegram_on; fi; read -rp "Press Enter to continue..." _ ;;
      setup) telegram_setup || true ;;
      try)
        if wt_yesno "Send the two messages to the chat as a test (marked as one)?\n\nNo: only show them here." 10; then clear; telegram_py test send
        else clear; telegram_py test; fi
        read -rp "Press Enter to continue..." _ ;;
      status) clear; telegram_status; read -rp "Press Enter to continue..." _ ;;
      remove) clear; telegram_remove "" || true; read -rp "Press Enter to continue..." _ ;;
      *) return 0 ;;
    esac
  done
}
