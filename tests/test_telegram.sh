#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_telegram.sh
# Telegram messages (0.99.6), the terminal's side, with stand-ins for systemctl (no network, no root): the token stays
# in its own file (root:zenithboard 0640), never in config.env, a backup or a command line; on needs the bot and the
# chat, off takes the service away; each setting is checked; the owner's templates are kept with a .bak and refused when
# unusable; the console offers the settings and never the token; the service's unit is sandboxed like the others.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" ZENITHBOARD_HOME="$PWD" ZB_SYSTEMD_DIR="$t/units" ZENITHBOARD_TELEGRAM_DIR="$t/data/telegram" \
  ZENITHBOARD_CONFIG="$t/etc/config.env" ZB_SKIP_SERVICES=1
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/units"; touch "$ZENITHBOARD_ETC/config.env"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"; chmod +x "$t/bin/systemctl"
export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/social.sh
. lib/social.sh
# shellcheck source=lib/telegram.sh
. lib/telegram.sh
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }
TOKEN="123456789:AAH0123456789abcdefghijklmnopqrstuv"

# ---- the token's file
check "a bot token looks like one"                          'telegram_valid_token "$TOKEN" && ! telegram_valid_token "123:abc" && ! telegram_valid_token "$TOKEN extra"'
check "a chat id is digits, a group's negative"             'telegram_valid_chat -1001234567890 && telegram_valid_chat 42 && ! telegram_valid_chat "@group"'
telegram_secrets_write "TELEGRAM_BOT_TOKEN=$TOKEN" "TELEGRAM_CHAT_ID=-1009" "TELEGRAM_CHAT_TITLE=Avions"
check "written whole, mode 0640"                             '[ "$(stat -c %a "$TELEGRAM_SECRETS")" = 640 ] && [ "$(telegram_secret_get TELEGRAM_CHAT_ID)" = -1009 ] && [ "$(telegram_chat)" = Avions ]'
check "never in config.env"                                  '! grep -q "$TOKEN\|TELEGRAM_BOT_TOKEN\|TELEGRAM_CHAT_ID" "$ZB_CONFIG"'
check "never on a command line: the code reads the file"     '! grep -n "telegram_py [a-z-]* .*TOKEN\|python3 .*telegram.py.*TELEGRAM_BOT_TOKEN" lib/*.sh bin/zenithboard'
check "the settings' export takes no token"                   'grep -q "TOKEN" lib/settings.sh'

# ---- on and off
rm -f "$TELEGRAM_SECRETS"
check "on without a bot: refused, said, nothing changed"     '! telegram_on >"$t/out" 2>&1 && grep -q "telegram setup" "$t/out" && [ "$(telegram_state)" = off ]'
telegram_secrets_write "TELEGRAM_BOT_TOKEN=$TOKEN" "TELEGRAM_CHAT_ID=-1009" "TELEGRAM_CHAT_TITLE=Avions"
telegram_on > "$t/out" 2>&1
check "on: the unit installed and started, the switch set"   '[ "$(telegram_state)" = on ] && [ -f "$t/units/zenithboard-telegram.service" ] && grep -q "restart zenithboard-telegram.service" "$t/systemctl.log" && [ -d "$t/data/telegram" ]'
check "on says where and what"                                'grep -q "Avions" "$t/out" && grep -q "emergency squawks" "$t/out"'
telegram_off > /dev/null
check "off: the unit gone, the bot kept"                      '[ "$(telegram_state)" = off ] && [ ! -f "$t/units/zenithboard-telegram.service" ] && [ -f "$TELEGRAM_SECRETS" ]'

# ---- the settings, one at a time
telegram_set_rules "military,heavy" >/dev/null
check "rules: some, in their order"                           '[ "$(cfg_get TELEGRAM_RULES)" = military,heavy ]'
check "rules: rare needs history, refused"                    '! telegram_set_rules rare 2>/dev/null && [ "$(cfg_get TELEGRAM_RULES)" = military,heavy ]'
telegram_set_rules all >/dev/null
check "rules: all"                                            '[ "$(cfg_get TELEGRAM_RULES)" = all ]'
telegram_set_switch TELEGRAM_SQUAWKS "Emergency squawks" off >/dev/null
check "squawks off, then on"                                  '[ "$(cfg_get TELEGRAM_SQUAWKS)" = 0 ] && telegram_set_switch TELEGRAM_SQUAWKS x on >/dev/null && [ "$(cfg_get TELEGRAM_SQUAWKS)" = 1 ]'
check "a switch takes on or off only"                         '! telegram_set_switch TELEGRAM_CROSSINGS x maybe 2>/dev/null'
check "units: aviation, then the posts' again"                'telegram_set_units aviation >/dev/null && [ "$(cfg_get TELEGRAM_UNITS)" = aviation ] && telegram_set_units posts >/dev/null && [ -z "$(cfg_get TELEGRAM_UNITS "")" ]'
check "language: one with a catalogue, or the posts'"         'telegram_set_lang fr >/dev/null && [ "$(cfg_get TELEGRAM_LANG)" = fr ] && ! telegram_set_lang xx 2>/dev/null && telegram_set_lang posts >/dev/null && [ -z "$(cfg_get TELEGRAM_LANG "")" ]'
check "the summary line says both kinds"                       '[ "$(telegram_words)" = "the aircraft crossing 15 km (every crossing), and the emergency squawks anywhere in range" ]'

# ---- the owner's templates
telegram_template squawk set -- "$(printf 'SOS {squawk}: {meaning}\n[{near}]')" > /dev/null
f=$(telegram_template_file squawk)
check "a template saved, lines kept, readable"                '[ "$(sed -n 2p "$f")" = "[{near}]" ] && [ "$(stat -c %a "$f")" = 644 ]'
check "an unusable one refused, the saved one kept"           '! telegram_template squawk set -- "SOS {distance}" >"$t/out" 2>&1 && grep -q "unknown tag" "$t/out" && grep -q "^SOS {squawk}" "$f"'
telegram_template squawk set -- "Second {flight}" > /dev/null
check "the one before kept as .bak"                           'grep -q "^SOS" "$f.bak" && grep -q "^Second" "$f"'
telegram_template squawk undo > /dev/null
check "undo: the previous one back, and swapped"              'grep -q "^SOS" "$f" && grep -q "^Second" "$f.bak"'
telegram_template squawk set -- none > /dev/null
check "none: the default again, the last kept"                '[ ! -e "$f" ] && grep -q "^SOS" "$f.bak"'
check "the default is shown in the messages' language"        'telegram_template squawk default | head -1 | grep -q "Squawk {squawk}: {meaning}"'
check "a kind that does not exist"                             '! telegram_template sunset show 2>/dev/null'

# ---- remove
telegram_on >/dev/null 2>&1
telegram_remove --yes > /dev/null
check "remove: token, chat, state and unit gone"              '[ ! -e "$TELEGRAM_SECRETS" ] && [ ! -d "$t/data/telegram" ] && [ "$(telegram_state)" = off ] && [ ! -f "$t/units/zenithboard-telegram.service" ]'

# ---- the console: the settings, never the token
console_ok() { python3 -c 'import sys, json; sys.path.insert(0, "flightinfo"); import console_actions as a; print(json.dumps(a.build(sys.argv[1], json.loads(sys.argv[2]))))' "$@" 2>/dev/null; }
check "console: on, the rules, the language, a template"      '[ "$(console_ok telegram "{\"value\":\"on\"}")" = "[\"telegram\", \"on\"]" ] && console_ok telegram-rules "{\"value\":\"military\"}" >/dev/null && console_ok telegram-lang "{\"value\":\"posts\"}" >/dev/null && console_ok telegram-template "{\"kind\":\"squawk\",\"text\":\"SOS {squawk}\"}" >/dev/null'
check "console: no action takes a token or sets the chat"     'python3 -c "import sys; sys.path.insert(0, \"flightinfo\"); import console_actions as a; sys.exit(any(\"setup\" in (s[2] or []) or \"chat\" in (s[2] or []) or \"token\" in str(s[3]).lower() for n, s in a.ACTIONS.items() if n.startswith(\"telegram\")))"'
check "console: rare refused, a kind that does not exist too" '[ -z "$(console_ok telegram-rules "{\"value\":\"rare\"}")" ] && [ -z "$(console_ok telegram-template-default "{\"kind\":\"sunset\"}")" ]'
check "console: its settings shown, the chat by name only"    'grep -q "\"TELEGRAM_RULES\": \"all\"" flightinfo/console.py && grep -q "telegram_chat=" lib/console.sh && ! grep -q "TELEGRAM_CHAT_ID\|TELEGRAM_BOT_TOKEN" flightinfo/console.py flightinfo/static/console.js'

# ---- the unit, sandboxed as the Bluesky one; the menu and the command
u=systemd/zenithboard-telegram.service
check "the unit runs as the wall user, writes its folder only" 'grep -qx "User=zenithboard" "$u" && grep -qx "ReadWritePaths=/var/lib/zenithboard/telegram" "$u" && grep -qx "CapabilityBoundingSet=" "$u" && grep -qx "NoNewPrivileges=true" "$u"'
check "menu 7 Options has it, and its menu one way out"       'grep -q "telegram \"5  Telegram" lib/menus.sh && [ "$(sed -n "/^telegram_menu()/,/^}/p" lib/telegram.sh | grep -c "back \"Return to the previous menu\"")" = 1 ]'
check "uninstall switches it off; an update restarts it"      'grep -q "telegram_off" install.sh && grep -q "telegram_install_units" lib/update.sh'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
