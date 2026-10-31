#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_stats.sh   The statistics collector, against a fake decoder: what one sample writes, how
# the day's aircraft are counted, what pruning keeps, what the terminal shows, and that off leaves the files.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/run/readsb" "$t/sysd"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_STATS_OUT_DIR="$t/stats" ZB_STATS_DIR="$t/run" ZB_SYSTEMD_DIR="$t/sysd" ZB_HOME="$PWD"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/systemctl.log"\n' "$t" > "$t/bin/systemctl"
printf '#!/bin/bash\necho 192.168.1.50\n' > "$t/bin/hostname"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/stats.sh
. lib/stats.sh
ZB_HOME="$PWD"          # common.sh points it at /opt; the units are read from the checkout here
cfg_set DECODER readsb
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---- the decoder's two files, as readsb writes them
cat > "$t/run/readsb/stats.json" <<'J'
{"last15min":{"messages":2412,"max_distance":311900,"local":{"accepted":[2400,12],"strong_signals":60}},"total":{"messages":99}}
J
cat > "$t/run/readsb/aircraft.json" <<'J'
{"now":1,"aircraft":[{"hex":"3c6444","lat":49.1,"lon":6.2,"flight":"DLH4YK  ","alt_baro":36000,"t":"A320"},{"hex":"4ca123","lat":49.3,"lon":6.0,"flight":"RYR5ZK","alt_baro":"ground"},{"hex":"a1b2c3"},{"hex":"~2a0001","lat":48.9,"lon":6.1}]}
J

check "off at first"                              '[ "$(stats_state)" = off ]'
out=$(stats_on)
check "on: setting, timer enabled, says where"    '[ "$(cfg_get STATS)" = 1 ] && grep -q "enable --now zenithboard-stats.timer" "$t/systemctl.log" && printf "%s" "$out" | grep -q "/stats"'
check "on: units installed"                       '[ -f "$t/sysd/zenithboard-stats.service" ] && [ -f "$t/sysd/zenithboard-stats.timer" ]'
check "on: the CSV exists with its header"        '[ "$(head -1 "$STATS_FILE")" = "$STATS_HEADER" ]'

stats_run
today=$(date '+%Y-%m-%d')
row=$(tail -1 "$STATS_FILE")
check "one sample: one line"                      '[ "$(grep -c . "$STATS_FILE")" = 2 ]'
check "sample: 2412 messages"                     '[ "$(cut -d, -f2 <<<"$row")" = 2412 ]'
check "sample: farthest 312 km (rounded from m)"  '[ "$(cut -d, -f3 <<<"$row")" = 312 ]'
check "sample: 2 aircraft with a position (the ~ one is not real)" '[ "$(cut -d, -f4 <<<"$row")" = 2 ]'
check "sample: 3 aircraft seen today"             '[ "$(cut -d, -f5 <<<"$row")" = 3 ]'
check "day file: three real hex codes, sorted"    '[ "$(tr "\n" " " < "$(stats_day_file "$today")")" = "3c6444 4ca123 a1b2c3 " ]'

check "fleet file (0.31.0): callsign, altitude, type; no ~ address" '[ "$(grep -c . "$(stats_fleet_file "$today")")" = 3 ] && grep -q "^3c6444	DLH4YK	36000	A320			[0-9][0-9][0-9][0-9]$" "$(stats_fleet_file "$today")" && grep -q "^4ca123	RYR5ZK					[0-9][0-9][0-9][0-9]$" "$(stats_fleet_file "$today")"'

# a second sample with one new aircraft and one gone: the day's count only grows
cat > "$t/run/readsb/aircraft.json" <<'J'
{"aircraft":[{"hex":"3c6444","lat":49.1,"lon":6.2,"alt_baro":12000},{"hex":"ff0001","lat":49.5,"lon":6.5}]}
J
stats_run
check "fleet: a blank keeps what was known, the altitude is the latest" 'grep -q "^3c6444	DLH4YK	12000	A320			[0-9][0-9][0-9][0-9]$" "$(stats_fleet_file "$today")" && [ "$(grep -c . "$(stats_fleet_file "$today")")" = 4 ]'
check "second sample: 4 distinct aircraft today"  '[ "$(tail -1 "$STATS_FILE" | cut -d, -f5)" = 4 ]'
check "second sample: 2 with a position now"      '[ "$(tail -1 "$STATS_FILE" | cut -d, -f4)" = 2 ]'

# tar1090's database, with `data localdb on` (0.31.0): an aircraft new to the day with no type from the decoder gets
# the database's; one already in the file is not looked up again
mkdir -p "$t/db"
python3 -c 'import gzip, json, sys; open(sys.argv[1], "wb").write(gzip.compress(json.dumps({"D2087": ["9H-EWG", "A320", "00", "AIRBUS A-320"], "6A8E": ["G-EZUH", "A319", "00", ""]}).encode()))' "$t/db/4.js"
cfg_set LOCAL_DB 1; cfg_set LOCAL_DB_DIR "$t/db"
cat > "$t/run/readsb/aircraft.json" <<'J'
{"aircraft":[{"hex":"4d2087","flight":"EWG8QR","alt_baro":32000},{"hex":"ff0001","alt_baro":5000},{"hex":"4d9999"}]}
J
stats_run
f=$(stats_fleet_file "$today")
check "localdb: a new aircraft gets its type from tar1090's database" 'grep -q "^4d2087	EWG8QR	32000	A320			[0-9][0-9][0-9][0-9]$" "$f"'
check "localdb: one not in it stays without; one already known is not looked up" 'grep -q "^4d9999						[0-9][0-9][0-9][0-9]$" "$f" && grep -q "^ff0001		5000				[0-9][0-9][0-9][0-9]$" "$f"'
cfg_set LOCAL_DB_DIR "$t/none"
cat > "$t/run/readsb/aircraft.json" <<'J'
{"aircraft":[{"hex":"4d6a8e","alt_baro":1000}]}
J
stats_run
check "localdb: a missing folder is no error, the sample is written" 'grep -q "^4d6a8e		1000				[0-9][0-9][0-9][0-9]$" "$f" && [ "$(tail -1 "$STATS_FILE" | cut -d, -f5)" = 7 ]'
# 0.36.0: the emitter category and the military mark, from the decoder or from tar1090's database ("10")
python3 -c 'import gzip, json, sys; open(sys.argv[1], "wb").write(gzip.compress(json.dumps({"D2087": ["9H-EWG", "A320", "00", ""], "6A8E": ["G-EZUH", "A319", "00", ""], "0F001": ["", "A400", "10", ""]}).encode()))' "$t/db/4.js"
python3 -c 'import gzip, json, sys; open(sys.argv[1], "wb").write(gzip.compress(json.dumps({"F001": ["ZZ001", "C30J", "10", ""]}).encode()))' "$t/db/3.js"
cfg_set LOCAL_DB_DIR "$t/db"
printf '%s\t%s\t%s\t%s\n' 3b0001 OLDFMT 1000 C172 >> "$f"                          # a line of 0.31.0, four columns
cat > "$t/run/readsb/aircraft.json" <<'J'
{"aircraft":[{"hex":"40f001","flight":"RRR4321","alt_baro":24000,"category":"A5"},{"hex":"3f001a","category":"B6"},{"hex":"ae1234","dbFlags":1,"t":"K35R","category":"A5"},{"hex":"3b0001","category":"A1"}]}
J
stats_run
check "category and military: from the database's flags"        'grep -q "^40f001	RRR4321	24000	A400	A5	1	[0-9][0-9][0-9][0-9]$" "$f"'
check "category and military: from the decoder's dbFlags"      'grep -q "^ae1234			K35R	A5	1	[0-9][0-9][0-9][0-9]$" "$f"'
check "a drone's category is kept"                              'grep -q "^3f001a				B6		[0-9][0-9][0-9][0-9]$" "$f"'
check "a line of 0.31.0 is read, and filled in"                 'grep -q "^3b0001	OLDFMT	1000	C172	A1		[0-9][0-9][0-9][0-9]$" "$f"'
cfg_set LOCAL_DB 0

# dump1090-fa: no top-level messages count, accepted is a list
cat > "$t/run/readsb/stats.json" <<'J'
{"last15min":{"local":{"accepted":[1500,20]},"max_distance":0}}
J
stats_run
check "dump1090-style: messages from accepted, farthest 0" '[ "$(tail -1 "$STATS_FILE" | cut -d, -f2,3)" = "1520,0" ]'

# nothing to read: nothing written, no error
rm "$t/run/readsb/stats.json"; n=$(grep -c . "$STATS_FILE")
stats_run; r=$?
check "decoder down: silent, nothing added"       '[ $r -eq 0 ] && [ "$(grep -c . "$STATS_FILE")" = "$n" ]'

# ---- pruning: old lines and old day files go, recent ones stay
old=$(date -d "40 days ago" '+%Y-%m-%d'); recent=$(date -d "3 days ago" '+%Y-%m-%d')
printf '%s 10:00,5,100,1,1\n%s 10:00,6,110,1,1\n' "$old" "$recent" >> "$STATS_FILE"
touch "$(stats_day_file "$old")" "$(stats_day_file "$recent")"
stats_prune
check "prune: the 40-day-old line is gone, the 3-day-old stays" '! grep -q "^$old" "$STATS_FILE" && grep -q "^$recent" "$STATS_FILE"'
check "prune: the old day file is gone, the recent stays"       '[ ! -e "$(stats_day_file "$old")" ] && [ -e "$(stats_day_file "$recent")" ]'
check "prune: the header is still first"                        '[ "$(head -1 "$STATS_FILE")" = "$STATS_HEADER" ]'

# ---- the terminal view
out=$(stats_show)
# five samples of the readsb file and one of dump1090's; eleven distinct aircraft (seven from the localdb samples)
check "show: today's aircraft count is the day file"  'printf "%s" "$out" | grep -q "Today  *11 aircraft seen"'
check "show: today's messages are summed"             'printf "%s" "$out" | grep -q "$((2412 * 5 + 1520)) messages"'
check "show: farthest today"                          'printf "%s" "$out" | grep -q "farthest 312 km"'
spark=$(printf "%s\n" "$out" | grep -A1 "Messages per hour today" | tail -1)
check "show: a sparkline of 24 bars"                  '[ "$(python3 -c "import sys; print(len(sys.argv[1].strip()))" "$spark")" = 24 ]'
check "show: says the count is a floor"               'printf "%s" "$out" | grep -q "floor"'
check "spark: heights follow the values"              '[ "$(stats_spark 0 4 8)" = "▁▅█" ]'
check "spark: all zero is all low"                    '[ "$(stats_spark 0 0 0)" = "▁▁▁" ]'

# 0.99.13 (review B5, S6): Yesterday and the average are the day files' counts, as Today is; the CSV's count is the
# one at the day's last sample and misses what the wall added after it. The average covers complete days only.
yd=$(date -d yesterday '+%Y-%m-%d')
printf '%s 00:00,7,90,1,4\n%s 23:45,8,95,2,5\n' "$yd" "$yd" >> "$STATS_FILE"
printf 'b%05d\n' 1 2 3 4 5 6 7 8 9 > "$(stats_day_file "$yd")"
out=$(stats_show)
check "show: Yesterday's aircraft are its day file's (9), not the CSV's last count (5)" 'printf "%s" "$out" | grep -q "Yesterday  *9 aircraft seen"'
check "show: the average is over complete days only, and says how many" 'printf "%s" "$out" | grep -q "Average  *9 aircraft/day on average over 1 complete day "'
check "show: today and the part-sampled day stay out of the average"   '! printf "%s" "$out" | grep -q "aircraft/day on average over [2-9]"'
sed -i "/^$yd /d" "$STATS_FILE"; rm -f "$(stats_day_file "$yd")"
out=$(stats_show)
check "show: no complete day yet is said, not averaged"                 'printf "%s" "$out" | grep -q "Average  *no complete day yet"'

# 0.99.13 (review B5, S2): the unit's UMask=0077 made the files 0600, and `zenithboard stats` without sudo said
# 0 samples. A sample under umask 0077 leaves them readable, files written before are opened up, never through a link,
# and a user who cannot read them is told to use sudo.
check "unit: UMask=0022 (0077 made the files 0600)" 'grep -qx "UMask=0022" systemd/zenithboard-stats.service && ! grep -q "^UMask=0077" systemd/zenithboard-stats.service'
chmod 600 "$STATS_FILE" "$(stats_day_file "$today")" "$(stats_fleet_file "$today")"
echo secret > "$t/target"; chmod 600 "$t/target"; ln -s "$t/target" "$STATS_DIR/seen-2001-01-01"
echo '{"last15min":{"messages":5,"max_distance":1000}}' > "$t/run/readsb/stats.json"; cfg_set PORT 1     # no wall answers
( umask 0077; stats_run )
check "a sample under umask 0077: stats.csv, the day and fleet files are 644" '[ "$(stat -c %a "$STATS_FILE")" = 644 ] && [ "$(stat -c %a "$(stats_day_file "$today")")" = 644 ] && [ "$(stat -c %a "$(stats_fleet_file "$today")")" = 644 ]'
check "  a link planted in the folder: its target's mode is untouched" '[ "$(stat -c %a "$t/target")" = 600 ]'
rm -f "$STATS_DIR/seen-2001-01-01"
check "  what it wrote, new files included, is readable by others" '[ -z "$(find "$STATS_DIR" -type f ! -perm -004)" ]'
chmod 600 "$STATS_FILE"; stats_install_units
check "the update path (stats_install_units) opens up a file written before" '[ "$(stat -c %a "$STATS_FILE")" = 644 ]'
# as another user: nobody when the suite runs as root, the runner itself otherwise (a file of mode 000)
mkdir -p "$t/other/lib"; cp lib/common.sh lib/stats.sh "$t/other/lib/"; chmod -R a+rX "$t/other"; chmod 755 "$t"; chmod a+r "$ZENITHBOARD_ETC/config.env"; chmod 755 "$ZENITHBOARD_ETC"
as_other() { local c=". '$t/other/lib/common.sh'; . '$t/other/lib/stats.sh'; $1"
  if [ "$(id -u)" = 0 ]; then runuser -u nobody -- env ZENITHBOARD_ETC="$ZENITHBOARD_ETC" ZB_STATS_OUT_DIR="$STATS_DIR" PATH="$PATH" bash -c "$c"
  else bash -c "$c"; fi; }
chmod 000 "$STATS_FILE"
out=$(as_other stats_show 2>&1); r=$?
check "a stats file this user cannot read: 'run with sudo', never 0 samples" '[ $r -ne 0 ] && printf "%s" "$out" | grep -q "cannot read .*stats.csv. Run with sudo: sudo zenithboard stats show" && ! printf "%s" "$out" | grep -q "0 samples"'
check "  the same for stats status and stats gaps" 'as_other stats_status 2>&1 | grep -q "Run with sudo: sudo zenithboard stats status" && as_other stats_gaps 2>&1 | grep -q "Run with sudo: sudo zenithboard stats gaps"'
chmod 644 "$STATS_FILE"
check "  readable: the figures, no sudo asked"              'o=$(as_other stats_show 2>&1); printf "%s" "$o" | grep -q "Today " && ! printf "%s" "$o" | grep -q "Run with sudo"'
chmod 700 "$t"

# ---- which aircraft was the farthest (0.22.0): asked of the wall on the loopback, written to farthest-DAY.
#      A stub wall answers: first with the route still on its way, then with it; the timer waits for it.
port=$((20000 + RANDOM % 20000)); cfg_set PORT "$port"
cat > "$t/wall.py" <<'PY'
import http.server, json, sys
port, script = int(sys.argv[1]), sys.argv[2]
answers = json.load(open(script)); n = {"i": 0}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        a = answers[min(n["i"], len(answers) - 1)]; n["i"] += 1
        open(script + ".asked", "a").write(self.path + "\n")
        b = json.dumps(a).encode(); self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
PY
rec() { printf '{"day":"%s","time":"14:32","hex":"406a1b","flight":"EZY1234","km":%s,"near":{"name":"Charleroi","country":"BE","km":51},"route":%s,"pending":%s}' "$1" "$2" "$3" "$4"; }
route='{"from":{"city":"Edinburgh","iata":"EDI"},"to":{"city":"Saint-Louis","iata":"BSL"}}'
wall() { printf '[%s]' "$1" > "$t/answers.json"; rm -f "$t/answers.json.asked"; python3 "$t/wall.py" "$port" "$t/answers.json" & srv=$!
  for _ in $(seq 50); do (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null && break; sleep 0.1; done; }   # 0.54.13: until it listens, not a fixed sleep (a bare connection asks nothing of it)
export ZB_FARTHEST_WAIT=0.2
wall "{\"enabled\":true,\"days\":[$(rec "$today" 318.4 null '["route"]')]},{\"enabled\":true,\"days\":[$(rec "$today" 318.4 "$route" '[]')]}"
stats_farthest_sample; kill $srv 2>/dev/null; wait $srv 2>/dev/null
ff="$STATS_DIR/farthest-$today"
check "farthest: written for the day"                    '[ -f "$ff" ] && python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d[\"km\"]==318.4 and d[\"flight\"]==\"EZY1234\"" "$ff"'
check "farthest: it waited for the route on its way"     '[ "$(grep -c farthest "$t/answers.json.asked")" = 2 ] && grep -q "Saint-Louis" "$ff" && ! grep -q pending "$ff"'
# the same record again, but the route lookup failed this time: what was known is kept
wall "{\"enabled\":true,\"days\":[$(rec "$today" 318.4 null '[]')]}"
stats_farthest_sample; kill $srv 2>/dev/null; wait $srv 2>/dev/null
check "farthest: the same record keeps the route it had"  'grep -q "Saint-Louis" "$ff"'
# the wall restarted and only knows a nearer one: the farther record stays
wall "{\"enabled\":true,\"days\":[$(rec "$today" 120.0 null '[]')]}"
stats_farthest_sample; kill $srv 2>/dev/null; wait $srv 2>/dev/null
check "farthest: a nearer one never replaces it"         'grep -q "318.4" "$ff"'
# a farther one does, and yesterday's record is written to its own file
yd=$(date -d yesterday '+%Y-%m-%d')
wall "{\"enabled\":true,\"days\":[$(rec "$yd" 250.0 null '[]'),$(rec "$today" 331.0 null '[]')]}"
stats_farthest_sample; kill $srv 2>/dev/null; wait $srv 2>/dev/null
check "farthest: a farther one replaces it, each day in its file" 'grep -q "331.0" "$ff" && grep -q "250.0" "$STATS_DIR/farthest-$yd"'
# nothing answers: nothing written, no error
rm -f "$STATS_DIR/farthest-$yd"; stats_farthest_sample; r=$?
check "farthest: wall down, silent, nothing written"     '[ $r -eq 0 ] && [ ! -e "$STATS_DIR/farthest-$yd" ]'
touch "$STATS_DIR/farthest-$old"; stats_prune
check "farthest: pruned after thirty days like the rest" '[ ! -e "$STATS_DIR/farthest-$old" ] && [ -f "$ff" ]'
check "farthest: the unit gives the sample time to wait" 'grep -q "^TimeoutStartSec=120$" systemd/zenithboard-stats.service'

# ---- 0.54.18: the wall's five-second list of the day's aircraft is added (a quarter-hour look missed 11%)
port=$((20000 + RANDOM % 20000)); cfg_set PORT "$port"
mkdir -p "$t/www/api"
yday=$(date -d yesterday '+%Y-%m-%d'); today=$(date '+%Y-%m-%d')
printf '{"enabled":true,"days":{"%s":{"aaa001":["BAW12","34000","A35K","A5","","0915"],"3c6444":["","","","","1","0920"]},"%s":{"bbb002":["","","","","","2358"]}}}' "$today" "$yday" > "$t/www/api/seen"
python3 -m http.server "$port" --bind 127.0.0.1 --directory "$t/www" >/dev/null 2>&1 & srv=$!
for _ in $(seq 1 50); do curl -s -o /dev/null "http://127.0.0.1:$port/api/seen" && break; sleep 0.1; done
echo '{"last15min":{"messages":10,"max_distance":1000}}' > "$t/run/readsb/stats.json"
printf '3c6444\n' > "$(stats_day_file "$yday")"                    # yesterday already started
stats_run
kill "$srv" 2>/dev/null; wait "$srv" 2>/dev/null
check "the wall's list: an aircraft the quarter-hour look missed is counted" 'grep -qx aaa001 "$(stats_day_file "$today")"'
check "  with its callsign, altitude, type and category in the fleet file" 'grep -q "^aaa001	BAW12	34000	A35K	A5		0915$" "$(stats_fleet_file "$today")"'
check "  a blank from the wall keeps what was known, and adds the military mark" 'grep -q "^3c6444	DLH4YK	[0-9]*	A320		1	" "$(stats_fleet_file "$today")"'
check "  yesterday's last aircraft go to yesterday's file"  'grep -qx bbb002 "$(stats_day_file "$yday")"'
check "  and to yesterday's fleet file, for the 24 hours' airlines and models (the review)" 'grep -qP "^bbb002(\t){6}2358$" "$(stats_fleet_file "$yday")"'
check "  the count in the CSV includes them" '[ "$(tail -1 "$STATS_FILE" | cut -d, -f5)" = "$(grep -c . "$(stats_day_file "$today")")" ]'
rm -f "$(stats_day_file "$yday")" "$(stats_fleet_file "$yday")"; cfg_set PORT 1
stats_run
check "wall down: the quarter-hour look alone, as before" '[ "$(tail -1 "$STATS_FILE" | cut -d, -f5)" -ge 1 ]'

# ---- off keeps the files, clear empties them
out=$(stats_off)
check "off: setting, timer disabled, files kept"  '[ "$(cfg_get STATS)" = 0 ] && grep -q "disable --now zenithboard-stats.timer" "$t/systemctl.log" && [ -f "$STATS_FILE" ] && [ ! -e "$t/sysd/zenithboard-stats.timer" ]'
stats_clear >/dev/null
check "clear: header only, no day files"          '[ "$(cat "$STATS_FILE")" = "$STATS_HEADER" ] && [ -z "$(ls "$STATS_DIR"/seen-* "$STATS_DIR"/farthest-* 2>/dev/null)" ]'
rm -f "$STATS_FILE"
out=$(stats_show); r=$?
check "show without any file: says how to turn it on" '[ $r -ne 0 ] && printf "%s" "$out" | grep -q "stats on"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
