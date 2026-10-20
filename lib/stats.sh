# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Statistics (menu 3 Settings -> Receiver -> Statistics, and `zenithboard stats ...`).
#
# Nothing on the Pi keeps history by itself: the decoder's stats.json holds the last fifteen minutes and the total
# since it started, and aircraft.json is the present moment. So, when switched on, a timer runs this every fifteen
# minutes on the quarter hour and writes one line: messages in those fifteen minutes, the farthest aircraft in km,
# how many aircraft had a position. It also notes every aircraft seen into a small file for the day, so the day's
# count is the number of distinct aircraft, and, since 0.31.0, each aircraft's callsign, altitude and type into
# another (the airlines, types and altitudes of the page). Thirty days are kept, then pruned. About 30 KB a day on the card.
#
# A fifteen-minute sample misses an aircraft that crossed in less than that, so the daily count is a floor, and
# both the page and the command say so. Off by default: `stats on` starts the timer, `stats off` stops it and
# keeps the files, `stats clear` empties them.
STATS_DIR="${ZB_STATS_OUT_DIR:-/var/lib/zenithboard/stats}"
STATS_FILE="$STATS_DIR/stats.csv"
STATS_HEADER="when,messages,farthest_km,aircraft_pos,aircraft_seen"
STATS_DAYS=30
STATS_UNIT=zenithboard-stats
STATS_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
STATS_AIRCRAFT_DIR="${ZB_STATS_DIR:-/run}"          # where the decoder writes aircraft.json and stats.json

stats_state() { [ "$(cfg_get STATS 0)" = 1 ] && echo on || echo off; }
stats_day_file() { echo "$STATS_DIR/seen-$1"; }   # stats_day_file YYYY-MM-DD
# 0.31.0: per aircraft of the day, what the statistics page counts: callsign, altitude (ft), type when the decoder
# knows it. One tab-separated line per aircraft, about 25 KB a day.
stats_fleet_file() { echo "$STATS_DIR/fleet-$1"; }

stats_install_units() {
  [ -f "$ZB_HOME/systemd/$STATS_UNIT.service" ] || return 0
  install -d -m 755 "$STATS_UNIT_DIR"
  install -m 644 "$ZB_HOME/systemd/$STATS_UNIT.service" "$ZB_HOME/systemd/$STATS_UNIT.timer" "$STATS_UNIT_DIR/"
  systemctl daemon-reload; systemctl enable --now "$STATS_UNIT.timer" >/dev/null 2>&1 || true
}
stats_remove_units() {
  systemctl disable --now "$STATS_UNIT.timer" >/dev/null 2>&1 || true
  rm -f "$STATS_UNIT_DIR/$STATS_UNIT.service" "$STATS_UNIT_DIR/$STATS_UNIT.timer"; systemctl daemon-reload 2>/dev/null || true
}

# The folder belongs to the wall's user: the timer runs as that user, and the wall server reads it.
stats_prepare_dir() {
  [ -d "$STATS_DIR" ] || install -d -m 755 "$STATS_DIR" 2>/dev/null || return 1
  [ "$(id -u)" -ne 0 ] || chown "$ZB_USER:$ZB_USER" "$STATS_DIR" 2>/dev/null || true
  [ -f "$STATS_FILE" ] || { echo "$STATS_HEADER" > "$STATS_FILE" && { [ "$(id -u)" -ne 0 ] || chown "$ZB_USER:$ZB_USER" "$STATS_FILE" 2>/dev/null || true; }; }
}

stats_on()  { stats_prepare_dir || { echo "Could not make $STATS_DIR"; return 1; }; cfg_set STATS 1; stats_install_units
              echo "Statistics are ON: one line every 15 minutes in $STATS_FILE, $STATS_DAYS days kept."
              echo "Read them with 'zenithboard stats' or at http://$(local_ip):$(cfg_get PORT 8080)/stats"; }
stats_off() { cfg_set STATS 0; stats_remove_units; echo "Statistics are OFF. The files are kept in $STATS_DIR (empty them: zenithboard stats clear)."; }
stats_clear() { rm -f "$STATS_DIR"/seen-* "$STATS_DIR"/gaps-* "$STATS_DIR"/farthest-* "$STATS_DIR"/fleet-* 2>/dev/null; [ -d "$STATS_DIR" ] && echo "$STATS_HEADER" > "$STATS_FILE"; echo "Statistics emptied ($STATS_DIR)."; }

# One sample. Reads the decoder's two files; writes one CSV line and today's aircraft. Silent when there is
# nothing to read: a decoder that is not running is not an error worth a journal line every quarter hour.
stats_run() {
  local d sj aj now day n msgs far pos seen ldb
  d=$(cfg_get DECODER ""); [ -n "$d" ] || d=$(installed_decoder); [ -n "$d" ] || return 0
  sj="$STATS_AIRCRAFT_DIR/$d/stats.json"; aj="$STATS_AIRCRAFT_DIR/$d/aircraft.json"
  [ -r "$sj" ] || return 0
  stats_prepare_dir || return 0
  now=$(date '+%Y-%m-%d %H:%M'); day=${now%% *}
  # tar1090's aircraft database, when `data localdb on`: the type of an aircraft the decoder did not give one
  ldb=""; [ "$(cfg_get LOCAL_DB 0)" = 1 ] && ldb=$(cfg_get LOCAL_DB_DIR /usr/local/share/tar1090/git-db/db)
  n=$(python3 - "$sj" "$aj" "$(stats_day_file "$day")" "$(stats_fleet_file "$day")" "$ldb" "$ZB_HOME/flightinfo" <<'PY'
import json, sys, os
sj, aj, dayfile, fleetfile, localdb, flightinfo = sys.argv[1:7]
try:
    j = json.load(open(sj))
except Exception:
    sys.exit(1)
w = j.get("last15min") or {}
l = w.get("local") or {}
msgs = w.get("messages")
if msgs is None:                       # dump1090-fa has no top-level count: use what the receiver accepted
    acc = l.get("accepted"); msgs = sum(acc) if isinstance(acc, list) else (acc or 0)
far = round((w.get("max_distance") or 0) / 1000.0)
seen, pos, fleet = set(), 0, {}
try:
    for a in (json.load(open(aj)).get("aircraft") or []):
        h = str(a.get("hex", "")).lower().strip()
        if h and not h.startswith("~"):           # ~ marks a non-ICAO, made-up address
            seen.add(h)
            if a.get("lat") is not None:
                pos += 1
            alt = a.get("alt_baro")
            try:
                mil = "1" if int(a.get("dbFlags") or 0) & 1 else ""     # the decoder's own database, when it has one
            except (TypeError, ValueError):
                mil = ""
            fleet[h] = [str(a.get("flight") or "").strip().upper(), str(int(alt)) if isinstance(alt, (int, float)) else "",
                        str(a.get("t") or "").strip().upper(), str(a.get("category") or "").strip().upper()[:2], mil]
except Exception:
    pass
# the fleet file: what was known before is kept, a blank never replaces a value, the altitude is the latest.
# 0.36.0: two more columns, the emitter category (A1 light ... B1 glider, B6 drone) and a military mark; a line of
# 0.31.0 has four columns and is read as before
WIDTH = 5
known = {}
try:
    for line in open(fleetfile):
        f = line.rstrip("\n").split("\t")
        if len(f) >= 4 and f[0]:
            known[f[0]] = (f[1:] + [""] * WIDTH)[:WIDTH]
except FileNotFoundError:
    pass
# an aircraft new to the day is looked up once in tar1090's database, here rather than by the page: a few dozen
# addresses a quarter hour instead of thirty days' worth at once on a Pi 3B (0.31.0); its type when the decoder gave
# none, and since 0.36.0 its military mark
new = [h for h in fleet if h not in known]
info = {}
if new and localdb and os.path.isdir(localdb):
    try:
        sys.path.insert(0, flightinfo)
        import server
        info = server.local_info(new, localdb)
    except Exception:
        info = {}
for h, v in fleet.items():
    old_f = known.get(h, [""] * WIDTH)
    db = info.get(h) or {}
    v[2] = v[2] or db.get("t", "")
    v[4] = v[4] or ("1" if db.get("mil") else "")
    known[h] = [v[k] or old_f[k] for k in range(WIDTH)]
if known:
    ftmp = fleetfile + ".tmp"
    with open(ftmp, "w") as fh:
        fh.write("".join("%s\t%s\n" % (h, "\t".join(v)) for h, v in sorted(known.items())))
    os.replace(ftmp, fleetfile)
old = set()
try:
    old = set(x.strip() for x in open(dayfile) if x.strip())
except FileNotFoundError:
    pass
allhex = old | seen
tmp = dayfile + ".tmp"
with open(tmp, "w") as fh:
    fh.write("\n".join(sorted(allhex)) + ("\n" if allhex else ""))
os.replace(tmp, dayfile)
print(int(msgs), far, pos, len(allhex))
PY
  ) || return 0
  read -r msgs far pos seen <<<"$n"
  printf '%s,%s,%s,%s,%s\n' "$now" "$msgs" "$far" "$pos" "$seen" >> "$STATS_FILE"
  stats_gaps_sample "$day"
  stats_farthest_sample
  stats_prune
}

# ---- what the wall cannot name or draw (0.21.0): the two counters the roadmap items "airline names for bare
# callsigns" and "more silhouettes" are decided on. At each sample the wall is asked, on the loopback, about the
# aircraft inside its radius; each aircraft shown with a callsign but no airline name is noted once under its
# three-letter prefix, and each aircraft drawn with the generic silhouette once under its type code.
# Files: gaps-YYYY-MM-DD, lines "airline<TAB>PREFIX<TAB>hex" and "shape<TAB>TYPE<TAB>hex"; thirty days like the rest.
stats_gaps_sample() {   # stats_gaps_sample YYYY-MM-DD
  local port f
  port=$(cfg_get PORT 8080); f="$STATS_DIR/gaps-$1"
  python3 - "$port" "$(cfg_get RADIUS 10)" "$f" <<'PY' 2>/dev/null || true
import json, os, sys, urllib.request
port, radius, out = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with urllib.request.urlopen("http://127.0.0.1:%s/api/planes?radius_km=%s" % (port, radius), timeout=5) as r:
        planes = json.load(r).get("planes") or []
except Exception:
    sys.exit(0)
lines = set()
try:
    lines = set(x.rstrip("\n") for x in open(out) if x.strip())
except FileNotFoundError:
    pass
for p in planes:
    h = str(p.get("hex", "")).lower()
    cs = str(p.get("flight") or "").strip().upper()
    if h and cs and not p.get("airline") and cs[:3].isalpha():
        lines.add("airline\t%s\t%s" % (cs[:3], h))
    if h and (p.get("shape") or "generic") == "generic" and p.get("type"):
        lines.add("shape\t%s\t%s" % (str(p["type"]).upper(), h))
tmp = out + ".tmp"
with open(tmp, "w") as fh:
    fh.write("\n".join(sorted(lines)) + ("\n" if lines else ""))
os.replace(tmp, out)
PY
}

# ---- which aircraft was the farthest (0.22.0). The decoder only says how far; the wall watches aircraft.json every
# few seconds and keeps, for today and yesterday, the farthest aircraft with its airline, route and the large city
# nearest it. It keeps that in memory, so it is asked here and written down: farthest-YYYY-MM-DD, one JSON object,
# thirty days like the rest. A farther record already written (before the wall restarted, say) is never replaced;
# the same record asked again fills in what the lookups found since.
STATS_FARTHEST_TRIES=4          # a route still being looked up: ask again, 3 s apart (adsbdb is asked 1.5 s apart)
stats_farthest_sample() {
  python3 - "$(cfg_get PORT 8080)" "$STATS_DIR" "$STATS_FARTHEST_TRIES" "${ZB_FARTHEST_WAIT:-3}" <<'PY' 2>/dev/null || true
import json, os, re, sys, time, urllib.request
port, out, tries, wait = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
def ask():
    with urllib.request.urlopen("http://127.0.0.1:%s/api/farthest" % port, timeout=5) as r:
        return json.load(r)
try:
    got = ask()
    while tries > 0 and any(d.get("pending") for d in got.get("days") or []):
        time.sleep(wait); tries -= 1; got = ask()
except Exception:
    sys.exit(0)
for rec in got.get("days") or []:
    day = str(rec.get("day") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day) or not isinstance(rec.get("km"), (int, float)):
        continue
    f = os.path.join(out, "farthest-" + day)
    try:
        with open(f) as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        old = None
    if isinstance(old, dict):
        if float(old.get("km") or 0) > rec["km"]:
            continue
        if old.get("hex") == rec.get("hex") and old.get("time") == rec.get("time"):
            for k, v in old.items():             # the same record: keep what an earlier answer knew and this one does not
                if rec.get(k) in (None, "", [], {}):
                    rec[k] = v
    rec.pop("pending", None)
    with open(f + ".tmp", "w") as fh:
        json.dump(rec, fh, ensure_ascii=False, sort_keys=True)
    os.replace(f + ".tmp", f)
PY
}

# The counters over the thirty days, most frequent first: "zenithboard stats gaps" is what to paste in an issue
stats_gaps() {
  local days
  days=$(ls "$STATS_DIR"/gaps-* 2>/dev/null | wc -l)
  [ "$days" -gt 0 ] || { echo "Nothing noted yet. Statistics are $(stats_state); the wall must be running, and the first sample comes on the next quarter hour."; return 1; }
  echo "What the wall could not name or draw, over $days day(s) of samples (distinct aircraft; a sample every 15 minutes misses some)"
  echo
  echo "Callsign prefixes shown without an airline name:"
  cat "$STATS_DIR"/gaps-* | awk -F'\t' '$1=="airline" {print $2 "\t" $3}' | sort -u | cut -f1 | sort | uniq -c | sort -rn | awk '{printf "  %-6s %s aircraft\n", $2, $1}' | head -40
  echo
  echo "Type codes drawn with the generic silhouette:"
  cat "$STATS_DIR"/gaps-* | awk -F'\t' '$1=="shape" {print $2 "\t" $3}' | sort -u | cut -f1 | sort | uniq -c | sort -rn | awk '{printf "  %-6s %s aircraft\n", $2, $1}' | head -40
}

# Thirty days of lines, thirty day files. Timestamps are YYYY-MM-DD HH:MM, which compare correctly as text.
stats_prune() {
  local cut tmp f d
  [ -f "$STATS_FILE" ] || return 0
  cut=$(date -d "$STATS_DAYS days ago" '+%Y-%m-%d %H:%M' 2>/dev/null) || return 0
  tmp="$STATS_FILE.tmp"
  { echo "$STATS_HEADER"; awk -F, -v c="$cut" 'NR>1 && $1 >= c' "$STATS_FILE"; } > "$tmp" && mv "$tmp" "$STATS_FILE"
  for f in "$STATS_DIR"/seen-* "$STATS_DIR"/gaps-* "$STATS_DIR"/farthest-* "$STATS_DIR"/fleet-*; do
    [ -f "$f" ] || continue
    d=${f##*/}; d=${d#seen-}; d=${d#gaps-}; d=${d#farthest-}; d=${d#fleet-}     # the YYYY-MM-DD after the prefix
    [ "$d" \< "${cut%% *}" ] && rm -f "$f"
  done
  return 0
}

# ------------------------------------------------------------------ the terminal view
stats_spark() {   # stats_spark v1 v2 ... -> one bar per value, eight heights
  local max=0 v out="" i
  local -a bars=("▁" "▂" "▃" "▄" "▅" "▆" "▇" "█")    # an array, so the glyphs survive a locale that is not UTF-8
  for v in "$@"; do [ "${v:-0}" -gt "$max" ] && max=$v; done
  for v in "$@"; do
    if [ "$max" -le 0 ]; then i=0; else i=$(( (${v:-0} * 7 + max / 2) / max )); fi
    out="$out${bars[$i]}"
  done
  printf '%s' "$out"
}

stats_show() {
  [ -f "$STATS_FILE" ] || { echo "No statistics yet. Turn them on with: sudo zenithboard stats on"; return 1; }
  local today yday rows out hours seen_today
  today=$(date '+%Y-%m-%d'); yday=$(date -d yesterday '+%Y-%m-%d' 2>/dev/null)
  rows=$(awk 'NR>1' "$STATS_FILE" | grep -c . || true)
  echo "Statistics: $(stats_state), $rows samples of 15 minutes, $STATS_DAYS days kept    File: $STATS_FILE"
  [ "$rows" -gt 0 ] || { echo "No sample yet: the first one comes on the next quarter hour."; return 0; }
  seen_today=$(grep -c . "$(stats_day_file "$today")" 2>/dev/null || echo 0)
  out=$(awk -F, -v today="$today" -v yday="$yday" -v seen_today="$seen_today" '
    NR>1 { day=substr($1,1,10); hour=substr($1,12,2)
           msgs[day]+=$2; if ($3>far[day]) far[day]=$3; if ($5>seen[day]) seen[day]=$5; days[day]=1
           if (day==today) h[hour]+=$2 }
    END {
      n=0; for (d in days) n++
      printf "%-10s %5d aircraft seen   %7d messages   farthest %3d km\n", "Today", seen_today, msgs[today], far[today]
      if (yday in days) printf "%-10s %5d aircraft seen   %7d messages   farthest %3d km\n", "Yesterday", seen[yday], msgs[yday], far[yday]
      best=0; for (d in days) if (far[d]>best) { best=far[d]; bestd=d }
      tot=0; for (d in days) tot+=seen[d]
      if (n>1) printf "%-10s %5d aircraft/day on average   best %d km on %s\n", n " days", tot/n, best, bestd
      printf "HOURS"; for (i=0;i<24;i++) printf " %d", h[sprintf("%02d",i)]; printf "\n"
    }' "$STATS_FILE")
  echo
  printf '%s\n' "$out" | grep -v '^HOURS'
  hours=$(printf '%s\n' "$out" | sed -n 's/^HOURS //p')
  echo
  echo "Messages per hour today, 00 to 23"
  # shellcheck disable=SC2086
  printf ' %s\n' "$(stats_spark $hours)"
  echo
  echo "Aircraft seen is a floor: a sample every 15 minutes misses an aircraft that crossed in less. CSV: zenithboard stats csv"
}
stats_csv() { [ -f "$STATS_FILE" ] && cat "$STATS_FILE" || { echo "No statistics yet."; return 1; }; }

stats_status() {
  echo "Statistics: $(stats_state)     Folder: $STATS_DIR"
  if [ -f "$STATS_FILE" ]; then
    echo "Samples: $(awk 'NR>1' "$STATS_FILE" | grep -c . || true)   Days with aircraft files: $(ls "$STATS_DIR"/seen-* 2>/dev/null | wc -l)"
    [ "$(stats_state)" = on ] && systemctl list-timers "$STATS_UNIT.timer" --no-pager 2>/dev/null | sed -n '2p'
  fi
  echo "Page: http://$(local_ip):$(cfg_get PORT 8080)/stats"
}
