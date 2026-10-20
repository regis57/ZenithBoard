#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_social.sh   The shell side of social sharing: the secrets file (owner, mode, what it holds
# and never shows), on/off/remove and what each leaves behind, the validators, and the security audit's line.
# The Python side (words, choice, networks, picture) is tests/test_social.py.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/sysd" "$t/state"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_SYSTEMD_DIR="$t/sysd" ZENITHBOARD_SOCIAL_DIR="$t/state/social"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"
printf '#!/bin/bash\nexit 0\n' > "$t/bin/node"                      # "node is installed"
printf '#!/bin/bash\necho "apt $*" >> "%s/apt.log"\n' "$t" > "$t/bin/apt-get"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/social.sh
. lib/social.sh
ZB_HOME="$PWD"; SOCIAL_PY="$PWD/flightinfo/social.py"
ZB_USER=$(id -un)                   # chown to the wall's user is for a real Pi; here the file keeps the tester's group
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

check "off at first, no account"                   '[ "$(social_state)" = off ] && [ -z "$(social_account)" ]'
check "on without an account refuses"              '! social_on >/dev/null 2>&1 && [ "$(cfg_get SOCIAL 0)" = 0 ]'

# ---- the secrets file
social_secrets_write "BLUESKY_HANDLE=zb.bsky.social" "BLUESKY_APP_PASSWORD=aaaa-bbbb-cccc-dddd"
check "secrets: file written with mode 640"        '[ "$(stat -c %a "$SOCIAL_SECRETS")" = 640 ]'
check "secrets: values quoted, read back"          '[ "$(social_secret_get BLUESKY_APP_PASSWORD)" = aaaa-bbbb-cccc-dddd ] && [ "$(social_account)" = zb.bsky.social ]'
check "secrets: not in config.env"                 '! grep -q "aaaa-bbbb" "$ZENITHBOARD_ETC/config.env"'
social_secrets_write "BLUESKY_HANDLE=other.bsky.social" "BLUESKY_APP_PASSWORD=eeee-ffff-gggg-hhhh"
check "secrets: rewritten whole, the old one gone" '[ "$(social_account)" = other.bsky.social ] && ! grep -q aaaa "$SOCIAL_SECRETS"'

# ---- 0.19.0: Mastodon taken out. What a 0.18 Pi had is cleaned up by the update, the Bluesky account kept
cfg_set SOCIAL_NETWORKS "bluesky,mastodon"
social_secrets_write "BLUESKY_HANDLE=zb.bsky.social" "BLUESKY_APP_PASSWORD=aaaa-bbbb-cccc-dddd" "MASTODON_URL=https://mastodon.social" "MASTODON_TOKEN=tok_123"
social_migrate >/dev/null 2>&1
check "migrate: network list gone from config.env"  '! grep -q "^SOCIAL_NETWORKS=" "$ZENITHBOARD_ETC/config.env"'
check "migrate: Mastodon token gone, Bluesky kept"  '! grep -q "MASTODON\|tok_123" "$SOCIAL_SECRETS" && [ "$(social_secret_get BLUESKY_APP_PASSWORD)" = aaaa-bbbb-cccc-dddd ] && [ "$(stat -c %a "$SOCIAL_SECRETS")" = 640 ]'
check "migrate: twice is the same as once"          'a=$(cat "$SOCIAL_SECRETS"); social_migrate >/dev/null 2>&1; [ "$(cat "$SOCIAL_SECRETS")" = "$a" ]'
# 0.23.0: a picture colour set to the dark blue is the owner's: kept, and the update says what to type
cfg_set SOCIAL_THEME blue
check "migrate: a blue picture colour is named, not changed" 'social_migrate 2>&1 | grep -q "taken out in 0.23.0.*social colour turquoise" && [ "$(cfg_get SOCIAL_THEME)" = blue ]'
# the wall blue too: the posts come out amber, and the notice says amber, not blue
cfg_set THEME blue
check "migrate: the colour the posts take is the one named" 'social_migrate 2>&1 | grep -q "the wall.s colour (amber)" && [ "$(cfg_get THEME)" = blue ]'
check "colour: the wall's colour as it shows"       '[ "$(wall_theme)" = amber ] && social_set_colour wall | grep -q "the wall.s (amber)"'
# the picture wizard on a Pi left on blue: the wall's colour ticked and named as it shows, the closing screen too.
# The stand-in whiptail answers Enter: the item ticked ON, or nothing when none is
wizard=$( wt_radio() { local t=$1 on=""; shift; echo "$t: $*" >> "$t_log"; while [ $# -ge 3 ]; do [ "$3" = ON ] && on=$1; shift 3; done; [ -n "$on" ] && echo "$on"; }
          wt_msg() { echo "MSG $1" >> "$t_log"; }; clear() { :; }; t_log="$t/wizard.log"; : > "$t_log"
          cfg_set SOCIAL_THEME blue; cfg_set SOCIAL_STYLE dots; social_setup_picture >/dev/null 2>&1; echo "rc=$?"; cat "$t_log" )
check "wizard: a blue picture colour shows the wall's ticked, as amber" 'echo "$wizard" | grep -q "^Colour.*wall The wall.s own colour (amber) ON"'
check "wizard: it saves and says the colour drawn"   'echo "$wizard" | grep -q "^rc=0" && echo "$wizard" | grep -q "MSG Saved. Picture: dotmap, the wall.s colour (amber), normal map" && [ -z "$(cfg_get SOCIAL_THEME "")" ] && [ "$(cfg_get THEME)" = blue ]'
# 0.24.0: the dots-only look is no longer offered; a Pi still set to it sees dotmap ticked, what its posts are
check "wizard: three looks, all with a map, dotmap ticked for dots" 'echo "$wizard" | grep -q "^The picture.*dotmap Dot-matrix wall, a map with the track beside it ON flap .* OFF alternate .* OFF$" && ! echo "$wizard" | grep -q " dots "'
cfg_del THEME; cfg_set SOCIAL_THEME ""; cfg_del SOCIAL_STYLE
check "migrate: no blue, no word about it"          '! social_migrate 2>&1 | grep -q "0.23.0"'
social_secrets_write "MASTODON_URL=https://mastodon.social" "MASTODON_TOKEN=tok_123"
cfg_set SOCIAL 1
social_migrate >/dev/null 2>&1
check "migrate: a Mastodon-only file is removed, sharing off" '[ ! -f "$SOCIAL_SECRETS" ] && [ "$(cfg_get SOCIAL 0)" = 0 ]'
social_secrets_write "BLUESKY_HANDLE=zb.bsky.social" "BLUESKY_APP_PASSWORD=aaaa-bbbb-cccc-dddd"

# ---- validators
check "handle: zb.bsky.social ok, no @"            'social_valid_handle zb.bsky.social && ! social_valid_handle "@zb" && ! social_valid_handle "zb"'

# ---- the picture: look, colour, map
check "look: dotmap, flap or alternate, nothing else" '! social_set_look photo >/dev/null && ! social_set_look dots >/dev/null && [ -z "$(cfg_get SOCIAL_STYLE "")" ] && [ "$(social_look)" = dotmap ]'
cfg_set SOCIAL_STYLE dots
check "look: dots, taken out in 0.24.0, is drawn as dotmap and named by the update" '[ "$(social_look)" = dotmap ] && social_migrate 2>&1 | grep -q "taken out in 0.24.0.*social look dotmap" && [ "$(cfg_get SOCIAL_STYLE)" = dots ] && [ "$(python3 -c "import sys; sys.path.insert(0, \"flightinfo\"); import social; print(social.style_of({\"SOCIAL_STYLE\": \"dots\"}))")" = dotmap ]'
cfg_del SOCIAL_STYLE
check "look: flap saved"                           'social_set_look flap >/dev/null && [ "$(cfg_get SOCIAL_STYLE)" = flap ]'
check "look: dotmap, the dots beside a map (0.23.0)" 'social_set_look dotmap >/dev/null && [ "$(cfg_get SOCIAL_STYLE)" = dotmap ] && social_set_look flap >/dev/null'
check "the shell knows the Python looks"           '[ "$(python3 -c "import sys; sys.path.insert(0, \"flightinfo\"); import social; print(\" \".join(social.STYLE_CHOICES))")" = "dotmap flap alternate" ] && social_set_look 2>&1 | grep -q "dotmap"'
cfg_set SOCIAL_THEME green
check "colour: blue is gone (0.23.0), refused"     '! social_set_colour blue >/dev/null && [ "$(cfg_get SOCIAL_THEME)" = green ]'
cfg_set SOCIAL_THEME red
check "colour: no argument is a usage line, not a reset" '! social_set_colour "" >/dev/null && [ "$(cfg_get SOCIAL_THEME)" = red ] && ! social_set_map "night satellite" >/dev/null'
cfg_set SOCIAL_THEME ""
check "colour: a wall colour, or the wall's"       'social_set_colour green >/dev/null && [ "$(cfg_get SOCIAL_THEME)" = green ] && social_set_colour wall >/dev/null && [ -z "$(cfg_get SOCIAL_THEME "")" ] && ! social_set_colour pink >/dev/null'
check "sentence: factual by default, several, random, refused (0.29.0)" '[ "$(cfg_get SOCIAL_SENTENCE factual)" = factual ] && social_set_sentence "Story, lookup" | grep -q "one drawn" && [ "$(cfg_get SOCIAL_SENTENCE)" = story,lookup ] && social_set_sentence random >/dev/null && ! social_set_sentence prose >/dev/null && [ "$(cfg_get SOCIAL_SENTENCE)" = random ] && social_set_sentence factual >/dev/null'
check "status names the sentence"                  'python3 "$SOCIAL_PY" status | grep -q "Post sentence: factual"'
check "photo link: off by default, on and off (0.25.0)" '[ "$(cfg_get SOCIAL_PHOTOLINK 0)" = 0 ] && social_set_photolink on | grep -q "ON" && [ "$(cfg_get SOCIAL_PHOTOLINK)" = 1 ] && ! social_set_photolink maybe >/dev/null && social_set_photolink off >/dev/null && [ "$(cfg_get SOCIAL_PHOTOLINK)" = 0 ]'
check "weekly summary: off by default, on says what it needs, off (0.33.0)" '[ "$(cfg_get SOCIAL_WEEKLY 0)" = 0 ] && cfg_set STATS 0 && social_set_weekly on | grep -q "statistics, which are OFF" && [ "$(cfg_get SOCIAL_WEEKLY)" = 1 ] && ! social_set_weekly maybe >/dev/null && social_set_weekly off | grep -q OFF && [ "$(cfg_get SOCIAL_WEEKLY)" = 0 ]'
check "weekly summary: command and menu"           'grep -q "week-\$3" bin/zenithboard && grep -q "weekly \"7  A summary of the week" lib/social.sh && grep -q "remove \"12 Remove" lib/social.sh'
check "units: metric, imperial or the wall's, nothing else (0.24.3)" 'social_set_units imperial >/dev/null && [ "$(cfg_get SOCIAL_UNITS)" = imperial ] && ! social_set_units feet >/dev/null && [ "$(cfg_get SOCIAL_UNITS)" = imperial ] && social_set_units wall >/dev/null && [ -z "$(cfg_get SOCIAL_UNITS "")" ]'
check "map: the five, nothing else"                'social_set_map satellite >/dev/null && [ "$(cfg_get SOCIAL_MAP)" = satellite ] && ! social_set_map google >/dev/null && [ "$(cfg_get SOCIAL_MAP)" = satellite ]'
check "the shell knows the Python lists"           'py=$(python3 -c "import sys; sys.path.insert(0, \"flightinfo\"); import social, server; print(\" \".join(social.MAP_CHOICES)); print(\" \".join(server.THEMES))"); [ "$(echo "$py" | head -1)" = "$SOCIAL_MAPS" ] && [ "$(echo "$py" | tail -1)" = "$SOCIAL_THEMES" ]'
check "variety: alternate, rotate, rotate accepted" 'social_set_look alternate >/dev/null && [ "$(cfg_get SOCIAL_STYLE)" = alternate ] && social_set_colour rotate >/dev/null && [ "$(cfg_get SOCIAL_THEME)" = rotate ] && social_set_map rotate >/dev/null && [ "$(cfg_get SOCIAL_MAP)" = rotate ]'
social_set_colour wall >/dev/null; social_set_map normal >/dev/null
cfg_del SOCIAL_STYLE

# ---- the hashtags (0.19.7): the # optional, so an unquoted shell word is not taken for a comment
check "hashtags: words become #words"              'social_set_hashtags ADSB "#avgeek" Moselle >/dev/null && [ "$(cfg_get SOCIAL_HASHTAGS)" = "#ADSB #avgeek #Moselle" ]'
check "hashtags: one quoted string works too"      'social_set_hashtags "#ADSB #Metz" >/dev/null && [ "$(cfg_get SOCIAL_HASHTAGS)" = "#ADSB #Metz" ]'
check "hashtags: a bad word changes nothing"       '! social_set_hashtags ADSB "two-words" >/dev/null 2>&1 && ! social_set_hashtags 1234 >/dev/null 2>&1 && [ "$(cfg_get SOCIAL_HASHTAGS)" = "#ADSB #Metz" ]'
check "hashtags: no glob, no injection"            'cd "$t" && touch zzz && ! social_set_hashtags "*" >/dev/null 2>&1 && ! social_set_hashtags "a;rm" >/dev/null 2>&1; cd - >/dev/null; [ "$(cfg_get SOCIAL_HASHTAGS)" = "#ADSB #Metz" ]'
check "hashtags: 8 at most"                        '! social_set_hashtags a b c d e f g h i >/dev/null 2>&1'
check "hashtags: none, then default"               'social_set_hashtags none >/dev/null && [ "$(cfg_get SOCIAL_HASHTAGS)" = none ] && social_set_hashtags default >/dev/null && [ "$(cfg_get SOCIAL_HASHTAGS)" = "#ADSB #avgeek #ZenithBoard" ]'
# ---- the gap (0.20.0): none by default, whole minutes, no floor
check "gap: none by default"                       '[ "$(social_gap_words)" = "none, every crossing" ]'
check "gap: set, shown, back to none"              'social_set_gap 30 >/dev/null && [ "$(cfg_get SOCIAL_GAP_MIN)" = 30 ] && social_set_gap | grep -q "30 min" && social_set_gap 0 >/dev/null && [ "$(social_gap_words)" = "none, every crossing" ]'
check "gap: under ten is kept (no floor)"          'social_set_gap 3 >/dev/null && [ "$(cfg_get SOCIAL_GAP_MIN)" = 3 ] && social_set_gap 08 >/dev/null && [ "$(cfg_get SOCIAL_GAP_MIN)" = 8 ]'
check "gap: nonsense changes nothing"              '! social_set_gap -5 2>/dev/null && ! social_set_gap 1.5 2>/dev/null && ! social_set_gap 99999 2>/dev/null && ! social_set_gap "1;rm" 2>/dev/null && ! social_set_gap 2000 2>/dev/null && [ "$(cfg_get SOCIAL_GAP_MIN)" = 8 ]'
check "hashtags: alone, it shows them"             'social_set_hashtags | grep -q "Hashtags: #ADSB #avgeek #ZenithBoard"'

# ---- on / off / remove
out=$(social_on)
check "on: setting, service enabled, says the rules" '[ "$(cfg_get SOCIAL)" = 1 ] && grep -q "enable zenithboard-social.service" "$t/systemctl.log" && printf "%s" "$out" | grep -q "rules:" && printf "%s" "$out" | grep -q "@zb.bsky.social"'
: > "$t/systemctl.log"; social_install_units
check "update: the running service is restarted, not just enabled" 'grep -q "restart zenithboard-social.service" "$t/systemctl.log"'
check "on: unit installed, state folder made"      '[ -f "$t/sysd/zenithboard-social.service" ] && [ -d "$ZENITHBOARD_SOCIAL_DIR" ]'
check "on: node present, apt not called"           '[ ! -f "$t/apt.log" ]'
social_off >/dev/null
check "off: setting, unit gone, secrets kept"      '[ "$(cfg_get SOCIAL)" = 0 ] && [ ! -f "$t/sysd/zenithboard-social.service" ] && [ -f "$SOCIAL_SECRETS" ]'
social_remove >/dev/null
check "remove: secrets and state gone"             '[ ! -f "$SOCIAL_SECRETS" ] && [ -z "$(social_account)" ] && [ ! -d "$ZENITHBOARD_SOCIAL_DIR" ]'

# ---- node is installed on demand
rm -f "$t/bin/node"; hash -r
PATH="$t/bin:/usr/bin:/bin" social_need_node >/dev/null 2>&1 || true   # no node anywhere on that PATH
[ -f "$t/apt.log" ] || { printf '#!/bin/bash\nexit 0\n' > "$t/bin/node"; chmod +x "$t/bin/node"; }
check "node missing: apt is asked for nodejs"      'grep -q "install -y nodejs" "$t/apt.log"'
printf '#!/bin/bash\nexit 0\n' > "$t/bin/node"; chmod +x "$t/bin/node"
printf '#!/bin/bash\n[ "$1" = -c ] && exit 1\nexec /usr/bin/python3 "$@"\n' > "$t/bin/python3"; chmod +x "$t/bin/python3"; hash -r
cfg_del SOCIAL_STYLE; social_need_tools >/dev/null 2>&1 || true     # every look has a map since 0.24.0
rm -f "$t/bin/python3"; hash -r
check "no Pillow: apt is asked for it, whatever the look"   'grep -q "install -y python3-pil fonts-dejavu-core" "$t/apt.log"'

# ---- the security audit knows the file
# shellcheck source=lib/security.sh
. lib/security.sh
DDNS_CURL="$t/none.curl"; GRAFANA_PASS_FILE="$t/none.pass"    # the other two secrets the audit looks at: absent here
social_secrets_write "BLUESKY_HANDLE=zb.bsky.social" "BLUESKY_APP_PASSWORD=t2"
chmod 644 "$SOCIAL_SECRETS"
check "audit: a world-readable social.env is a WARN" 'sec_secrets 2>/dev/null | grep -q "WARN.*social.env"'
chmod 640 "$SOCIAL_SECRETS"
if [ "$(id -u)" -eq 0 ]; then
  chown "root:$ZB_USER" "$SOCIAL_SECRETS"
  check "audit: root:group 640 is OK"              'sec_secrets 2>/dev/null | grep -q "OK.*social.env"'
else
  echo "skip audit OK line (needs root to set root:$ZB_USER)"
fi

# ---- the Python command line answers without a Pi
check "status runs without a service"              'python3 "$SOCIAL_PY" status | grep -q "Social sharing: off"'
check "status says the weekly summary"             'python3 "$SOCIAL_PY" status | grep -q "Weekly summary: off"'
check "week-test with no statistics says so"       'ZENITHBOARD_STATS_DIR="$t/nostats" python3 "$SOCIAL_PY" week-test | grep -q "Nothing to sum up"'
check "check with no account says so"              'rm -f "$SOCIAL_SECRETS"; python3 "$SOCIAL_PY" check | grep -q "No account configured"'
exit $fail
