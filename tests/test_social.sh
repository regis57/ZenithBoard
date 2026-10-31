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
# review B14 (T7): the picture folder in /run as well, which social_prepare_dir makes when the suite runs as root
export ZENITHBOARD_SOCIAL_RUN="$t/run/social"
# 0.54.13: the Python side reads its own paths; without these, on the Pi, `social.py check` below would have used the
# real account and signed in to Bluesky from a test
export ZENITHBOARD_CONFIG="$ZENITHBOARD_ETC/config.env" ZENITHBOARD_SOCIAL_SECRETS="$ZENITHBOARD_ETC/social.env" ZENITHBOARD_SOCIAL_TEMPLATES="$ZENITHBOARD_ETC/social-templates.txt"
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
check "weekly summary: off by default, on says what it needs, off (0.33.0)" '[ "$(cfg_get SOCIAL_WEEKLY 0)" = 0 ] && cfg_set STATS 0 && social_set_weekly on | grep -q "statistics, which are OFF" && [ "$(cfg_get SOCIAL_WEEKLY)" = 1 ] && ! social_set_weekly maybe >/dev/null && social_set_weekly off | grep -q "weekly   off" && [ "$(cfg_get SOCIAL_WEEKLY)" = 0 ]'
check "summaries (0.38.0): times checked, kept tidy"   'social_summary daily at 21:30 >/dev/null && [ "$(cfg_get SOCIAL_DAILY_AT)" = "21:30" ] && social_summary weekly at "Saturday 08:05" >/dev/null && [ "$(cfg_get SOCIAL_WEEKLY_AT)" = "sat 08:05" ] && social_summary monthly at "28 23:59" >/dev/null && ! social_summary monthly at "31 09:00" >/dev/null && ! social_summary daily at 25:00 >/dev/null && ! social_summary weekly at "21:00" >/dev/null && ! social_summary daily at "mon 21:00" >/dev/null && [ "$(cfg_get SOCIAL_MONTHLY_AT)" = "28 23:59" ]'
check "summaries: the posts picked, the first always"  'social_summary weekly parts 3,2 >/dev/null && [ "$(cfg_get SOCIAL_WEEKLY_PARTS)" = "1,2,3" ] && social_summary daily parts all >/dev/null && [ "$(cfg_get SOCIAL_DAILY_PARTS)" = "1,2,3,4" ] && ! social_summary daily parts 5 >/dev/null && ! social_summary daily parts "1;rm" >/dev/null && [ "$(cfg_get SOCIAL_DAILY_PARTS)" = "1,2,3,4" ]'
check "summaries: why (0.49.0) says what each needs and points nowhere else" 'social_summary why > "$t/why" 2>&1; grep -q "Summaries, as set" "$t/why" && grep -q "Statistics:" "$t/why" && grep -q "Social sharing:" "$t/why" && grep -q "lines about the summaries" "$t/why" && social_summary | grep -q "social summary why"'
# 0.49.1: seen on the real Pi on 22 October 2026: the files 0.49.0, the service still 0.47.0 from 00:11, and a day of
# updates in its journal. `why` says the service runs older code, with the command, and keeps the summary lines
mkdir -p "$t/whybin"
printf '#!/bin/bash\ncat "%s/tests/fixtures/social-journal-why.txt"\n' "$PWD" > "$t/whybin/journalctl"
printf '#!/bin/bash\ncase "$*" in *is-active*) echo active ;; *ActiveEnterTimestamp*) echo "${WHY_SINCE:-Thu 2026-10-22 00:11:33 UTC}" ;; esac\n' > "$t/whybin/systemctl"
chmod +x "$t"/whybin/*
why_run() { PATH="$t/whybin:$PATH" ZB_VERSION=$1 WHY_SINCE=$2 social_summary why; }
why_run 0.49.1 "Thu 2026-10-22 00:11:33 UTC" > "$t/why-old" 2>&1
check "why (0.49.1): the service on older code said, with the restart"    'grep -q "It runs: ZenithBoard 0.47.0   (this copy: 0.49.1)" "$t/why-old" && grep -q "from before the last update" "$t/why-old" && grep -q "sudo systemctl restart zenithboard-social" "$t/why-old"'
check "why: the summary lines kept however many starts, the starts apart" 'grep -q "posted the daily summary, post 1" "$t/why-old" && grep -q "no daily summary, post 4" "$t/why-old" && grep -q "could not post EWG14A" "$t/why-old" && grep -q "^  Oct 22 00:11  0.47.0$" "$t/why-old" && [ "$(sed -n "/^Its starts/,\$p" "$t/why-old" | grep -c "^  Oct")" = 12 ] && ! grep -q "posted AB0" "$t/why-old"'
why_run 0.47.0 "Fri 2099-01-01 00:00:00 UTC" > "$t/why-same" 2>&1
check "why: the same version, started after the code: nothing to restart"  'grep -q "It runs: ZenithBoard 0.47.0   (this copy: 0.47.0)" "$t/why-same" && ! grep -q "Restart it" "$t/why-same"'
# 0.50.0: the wizard's answers one by one (for the web console)
check "area: the owner's words tidied, how a post ends with them, none" 'social_set_area "  near   Metz " | grep -q "the posts say: near Metz" && [ "$(cfg_get SOCIAL_AREA)" = "near Metz" ] && social_set_area Trémery | grep -q "above Trémery" && social_set_area none >/dev/null && [ -z "$(cfg_get SOCIAL_AREA)" ] && social_set_area Metz >/dev/null && social_set_area " none " >/dev/null && [ -z "$(cfg_get SOCIAL_AREA)" ]'
check "area: quotes, dollars, a 41st character refused, the old one kept" 'social_set_area Metz >/dev/null && ! social_set_area "a\"b" 2>/dev/null && ! social_set_area "x\$(id)" 2>/dev/null && ! social_set_area "$(printf "a%.0s" {1..41})" 2>/dev/null && [ "$(cfg_get SOCIAL_AREA)" = Metz ]'
check "radius: whole kilometres, 1 to 200"           'social_set_radius 25 >/dev/null && [ "$(cfg_get SOCIAL_RADIUS_KM)" = 25 ] && ! social_set_radius 0 2>/dev/null && ! social_set_radius 201 2>/dev/null && ! social_set_radius 2.5 2>/dev/null && [ "$(cfg_get SOCIAL_RADIUS_KM)" = 25 ]'
check "rules: all, or the special ones in their order, nothing else, never none" 'social_set_rules rare,military,rare >/dev/null && [ "$(cfg_get SOCIAL_RULES)" = military,rare ] && social_set_rules rare,all >/dev/null && [ "$(cfg_get SOCIAL_RULES)" = all ] && ! social_set_rules drones 2>/dev/null && ! social_set_rules , 2>/dev/null && ! social_set_rules " " 2>/dev/null && [ "$(cfg_get SOCIAL_RULES)" = all ]'
check "area, radius, rules: commands; no written post (0.51.0, the owner)" 'grep -q "area)   \[" bin/zenithboard && grep -q "rules)  \[" bin/zenithboard && ! grep -q "social_say\|say)" bin/zenithboard lib/social.sh'
# 0.51.0: the posts' language and the owner's own templates
export ZENITHBOARD_SOCIAL_TEMPLATES="$t/etc/social-templates.txt"; SOCIAL_TEMPLATES="$ZENITHBOARD_SOCIAL_TEMPLATES"
check "lang: English until set; a language with a catalogue, Swahili too (0.53.1); none other" 'social_set_lang | grep -q "Language of the posts: en" && social_set_lang fr >/dev/null && [ "$(cfg_get SOCIAL_LANG)" = fr ] && ! social_set_lang xx 2>/dev/null && social_set_lang sw >/dev/null && [ "$(cfg_get SOCIAL_LANG)" = sw ] && social_set_lang en >/dev/null'
check "template: none yet, added, a broken one refused, listed, tried, deleted, emptied (.bak kept)" 'social_template | grep -q "No template yet" && social_template add "{airline} {flight}[, {from} → {to}] at {altitude}." >/dev/null && ! social_template add "{airline} {distance}" >/dev/null 2>&1 && social_template add "{flag} {airline}" >/dev/null && [ "$(grep -c . "$SOCIAL_TEMPLATES")" = 2 ] && social_template | grep -q "2. {flag} {airline}" && social_template del 1 >/dev/null && [ "$(cat "$SOCIAL_TEMPLATES")" = "{flag} {airline}" ] && [ -f "$SOCIAL_TEMPLATES.bak" ] && social_template set none >/dev/null && [ ! -s "$SOCIAL_TEMPLATES" ]'
check "template set: several lines at once, each checked" 'social_template set "$(printf "{airline}\n\n  {type} at {altitude}  ")" >/dev/null && [ "$(cat "$SOCIAL_TEMPLATES")" = "$(printf "{airline}\n{type} at {altitude}")" ] && ! social_template set "$(printf "{airline}\n{x}")" >/dev/null 2>&1 && [ "$(grep -c . "$SOCIAL_TEMPLATES")" = 2 ]'
# 0.53.3: delete them all (the console's button runs set none), then put them back, then back again
printf '{airline}\n{type} at {altitude}\n' > "$SOCIAL_TEMPLATES"
check "template set none: all deleted, kept as .bak"     'social_template set none >/dev/null && [ ! -s "$SOCIAL_TEMPLATES" ] && [ "$(grep -c . "$SOCIAL_TEMPLATES.bak")" = 2 ]'
check "template undo: the ones before back, today's as .bak" 'social_template undo | grep -q "put back: 2" && [ "$(grep -c . "$SOCIAL_TEMPLATES")" = 2 ] && [ ! -s "$SOCIAL_TEMPLATES.bak" ]'
check "template undo again: nothing to put back is said"  '! social_template undo >/dev/null 2>&1 && [ "$(grep -c . "$SOCIAL_TEMPLATES")" = 2 ]'
check "menu: delete them all (asked first) and put back"  'grep -q "clear \"4  Delete them all\"" lib/social.sh && grep -q "undo \"5  Put back" lib/social.sh && grep -q "Delete all your templates?" lib/social.sh'
check "template test: on a sample when nothing flies over, posts nothing" 'social_template test > "$t/tt" 2>&1; grep -q "on a sample" "$t/tt" && grep -q "Nothing posted" "$t/tt"'
check "words of a post: custom accepted"            'social_set_sentence factual,custom | grep -q "factual,custom" && social_set_sentence factual >/dev/null'
check "lang and template: commands and menu"        'grep -q "lang)   \[" bin/zenithboard && grep -q "template|templates)" bin/zenithboard && grep -q "lang \"3  Language of the posts" lib/social.sh && grep -q "template \"4  Your own templates" lib/social.sh'
check "summaries: the overview and a wrong period"     'social_summary | grep -q "daily" && social_summary | grep -q "monthly" && ! social_summary yearly on >/dev/null'
check "summaries: command and menu"                 'grep -q "summary-test" bin/zenithboard && grep -q "set -- social summary weekly" bin/zenithboard && grep -q "weekly \"5  Summaries" lib/social.sh && grep -q "^summary_menu()" lib/social.sh && grep -q "remove \"2  Remove" lib/social.sh'
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

# ---- the words wizard (0.53.7): the commands' own rules, asked again until they are met, never "Saved." after a refusal
printf '%s\n' "" abc 0 500 -5 20 x -5 1500 10 none > "$t/answers"; : > "$t/msgs.log"
(       # a subshell: the stand-ins for the screens are not left behind for the checks below
  wt_input() { local a; a=$(head -1 "$t/answers"); sed -i 1d "$t/answers"; printf '%s' "$a"; }
  wt_msg() { printf '%s\n' "$1" >> "$t/msgs.log"; }
  whiptail() { echo '"military"' >&2; }       # the rules checklist answers on stderr, as whiptail does
  social_setup_words
)
check "wizard: a bad radius is asked again, then kept"   '[ "$(cfg_get SOCIAL_RADIUS_KM)" = 20 ] && [ "$(grep -c "whole kilometres" "$t/msgs.log")" = 4 ]'
check "wizard: a bad gap is asked again, then kept"      '[ "$(cfg_get SOCIAL_GAP_MIN)" = 10 ] && [ "$(grep -c "whole minutes" "$t/msgs.log")" = 3 ]'
# 0.54.9 (the audit of 22-23 October 2026): an Esc in the middle keeps nothing of the answers before it
printf '%s\n' "Somewhere Else" 42 > "$t/answers"
(
  wt_input() { local a; a=$(head -1 "$t/answers") || return 1; [ -n "$a" ] || return 1; sed -i 1d "$t/answers"; printf '%s' "$a"; }
  wt_msg() { :; }
  social_setup_words
)
check "wizard: Esc at the gap keeps the place and radius as they were" '[ "$(cfg_get SOCIAL_RADIUS_KM)" = 20 ] && [ "$(cfg_get SOCIAL_AREA "")" != "Somewhere Else" ]'
# 0.54.9: seven entries and Return at most, in the Bluesky menu and its sub-menus (it had fourteen, Return under the fold)
for f in social_menu social_look_menu; do
  n=$(sed -n "/^$f() {/,/^}/p" lib/social.sh | grep -cE '^      [a-z]+ "[0-9]+  ')
  check "$f: seven entries at most ($n), and Return" '[ "$n" -ge 3 ] && [ "$n" -le 7 ] && sed -n "/^$f() {/,/^}/p" lib/social.sh | grep -q "back \"Return to the previous menu\""'
done
check "menu: Remove is not the entry just above Return" '! sed -n "/^social_menu() {/,/^}/p" lib/social.sh | grep -A1 "remove \"" | grep -q "back \""'
check "menu: the posts' language is chosen by name"     'grep -q "^social_lang_menu()" lib/social.sh && grep -q "lang) social_lang_menu" lib/social.sh'

# 0.54.16: a new app password for an account already there does not replay the two wizards
printf 'BLUESKY_HANDLE=zb.bsky.social\nBLUESKY_APP_PASSWORD=old\n' > "$SOCIAL_SECRETS"
out=$(
  wt_input() { echo zb.bsky.social; }; whiptail() { echo "new-pass-word" >&2; }; wt_msg() { echo "MSG $1"; }
  social_setup_words() { echo WORDS-WIZARD; }; social_setup_picture() { echo PICTURE-WIZARD; }
  python3() { echo "bluesky: ok, signed in as zb.bsky.social"; }
  social_setup 2>&1 < /dev/null
)
check "setup: a new app password, the wizards not replayed" 'printf "%s" "$out" | grep -q "saved and checked" && ! printf "%s" "$out" | grep -q "WORDS-WIZARD"'
# ---- on / off / remove
social_try_account() { echo "bluesky: ok, signed in as zb.bsky.social"; }      # Bluesky itself is not reached from a test
out=$(social_on)
check "on: setting, service enabled, says the rules" '[ "$(cfg_get SOCIAL)" = 1 ] && grep -q "enable zenithboard-social.service" "$t/systemctl.log" && printf "%s" "$out" | grep -q "rules:" && printf "%s" "$out" | grep -q "@zb.bsky.social"'
: > "$t/systemctl.log"; social_install_units
check "update: the running service is restarted, not just enabled" 'grep -q "restart zenithboard-social.service" "$t/systemctl.log"'
check "on: unit installed, state folder made"      '[ -f "$t/sysd/zenithboard-social.service" ] && [ -d "$ZENITHBOARD_SOCIAL_DIR" ]'
check "on: node present, apt not called"           '[ ! -f "$t/apt.log" ]'
social_off >/dev/null
# 0.53.7: the account is tried before sharing is switched on
social_try_account() { echo "bluesky: FAILED: 401 {\"error\":\"AuthenticationRequired\"}"; }
out=$(social_on 2>&1); rc=$?
check "on: a refused account is not switched on"   '[ "$rc" = 1 ] && [ "$(cfg_get SOCIAL 0)" = 0 ] && printf "%s" "$out" | grep -q "refused this account, so sharing was NOT switched on"'
social_try_account() { echo "bluesky: FAILED: <urlopen error [Errno -3] Temporary failure in name resolution>"; }
out=$(social_on 2>&1); rc=$?
check "on: an unreachable Bluesky is said, and sharing goes on" '[ "$rc" = 0 ] && [ "$(cfg_get SOCIAL)" = 1 ] && printf "%s" "$out" | grep -q "could not be reached just now"'
social_off >/dev/null
social_try_account() { echo "bluesky: ok, signed in as zb.bsky.social"; }
check "off: setting, unit gone, secrets kept"      '[ "$(cfg_get SOCIAL)" = 0 ] && [ ! -f "$t/sysd/zenithboard-social.service" ] && [ -f "$SOCIAL_SECRETS" ]'
out=$(echo no | social_remove 2>&1); rc=$?
check "remove: anything but the typed word changes nothing" '[ "$rc" = 1 ] && [ -f "$SOCIAL_SECRETS" ] && printf "%s" "$out" | grep -q "Nothing was changed"'
echo remove | social_remove >/dev/null
check "remove: secrets and state gone"             '[ ! -f "$SOCIAL_SECRETS" ] && [ -z "$(social_account)" ] && [ ! -d "$ZENITHBOARD_SOCIAL_DIR" ]'

# ---- node is installed on demand
# 0.54.13: node is hidden from `command -v` itself; a PATH without /opt only worked where node was not in /usr/bin (the
# Pi has it there, so the test failed on the very machine it is about)
( command() { [ "$*" = "-v node" ] && return 1; builtin command "$@"; }; social_need_node >/dev/null 2>&1 ) || true
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
check "status says the summaries"                  'python3 "$SOCIAL_PY" status | grep -q "Summary, weekly: off" && python3 "$SOCIAL_PY" status | grep -q "Summary, monthly"'
# 0.54.13: two of the command line's answers the console reads had no test
check "summary-when --facts: the three summaries, last and next, as KEY=value" '[ "$(python3 "$SOCIAL_PY" summary-when --facts | grep -c "^sum_\(daily\|weekly\|monthly\)_\(last\|next\)=")" = 6 ]'
check "template-tags: the tags, the [part] and |cap"   'python3 "$SOCIAL_PY" template-tags > "$t/tags" && grep -q "{airline}" "$t/tags" && grep -q "\[ ... \]" "$t/tags" && grep -q "{tag|cap}" "$t/tags"'
check "week-test with no statistics says so"       'ZENITHBOARD_STATS_DIR="$t/nostats" python3 "$SOCIAL_PY" week-test | grep -q "Nothing to sum up"'
check "check with no account says so"              'rm -f "$SOCIAL_SECRETS"; python3 "$SOCIAL_PY" check | grep -q "No account configured"'
exit $fail
