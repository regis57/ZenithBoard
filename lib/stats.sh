# shellcheck shell=bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Statistics (menu 7 Options -> 1 Statistics, and `zenithboard stats ...`).
#
# Nothing on the Pi keeps history by itself: the decoder's stats.json holds the last fifteen minutes and the total
# since it started, and aircraft.json is the present moment. So, when switched on, a timer runs this every fifteen
# minutes on the quarter hour and writes one line: messages in those fifteen minutes, the farthest aircraft in km,
# how many aircraft had a position. It also notes every aircraft seen into a small file for the day, so the day's
# count is the number of distinct aircraft, and, since 0.31.0, each aircraft's callsign, altitude and type into
# another (the airlines, types and altitudes of the page). Thirty days are kept, then pruned. About 30 KB a day on the card.
#
# A fifteen-minute sample misses an aircraft that crossed in less than that, so the daily count is a floor, and
# both the page and the command say so. Since 0.54.18 the wall's five-second look adds those (11% of the day's). Off by default: `stats on` starts the timer, `stats off` stops it and
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
  stats_open_files                                  # 0.99.13: on the update, the files the old UMask=0077 wrote
  systemctl daemon-reload; systemctl enable --now "$STATS_UNIT.timer" >/dev/null 2>&1 || true
}
stats_remove_units() {
  systemctl disable --now "$STATS_UNIT.timer" >/dev/null 2>&1 || true
  rm -f "$STATS_UNIT_DIR/$STATS_UNIT.service" "$STATS_UNIT_DIR/$STATS_UNIT.timer"; systemctl daemon-reload 2>/dev/null || true
}

# The folder belongs to the wall's user: the timer runs as that user, and the wall server reads it.
stats_prepare_dir() {
  ensure_zb_user                                    # 0.43.0: the timer runs as the wall's user, which a fresh card may not have yet
  # 0.99.11 (review B3): made and handed over without following a link planted in the folder's or the file's place
  zb_service_dir "$STATS_DIR" 755 || return 1
  [ -f "$STATS_FILE" ] || stats_new_file
  stats_open_files
}
# 0.99.13 (review B5, S2): the unit's UMask=0077 made every file the timer wrote 0600, so `zenithboard stats` without
# sudo read nothing and said 0 samples. The unit now says 0022; the files written before are opened up here, once,
# on the next sample or update. They hold no position (counts, aircraft addresses, callsigns, the farthest aircraft's
# nearest city), the same the /stats page shows. Each file is opened without following a link and changed through
# its descriptor, so a link planted in the folder never lets root change another file's mode (review B3).
stats_open_files() {
  [ -d "$STATS_DIR" ] || return 0
  python3 - "$STATS_DIR" <<'PY' 2>/dev/null || true
import os, re, stat, sys
try:
    dfd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
except OSError:
    sys.exit(0)
for name in os.listdir(dfd):
    if name != "stats.csv" and not re.match(r"^(seen|fleet|gaps|farthest)-\d{4}-\d{2}-\d{2}$", name):
        continue
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
    except OSError:
        continue
    try:
        st = os.fstat(fd)
        if stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode) & 0o044 != 0o044:
            os.fchmod(fd, 0o644)
    except OSError:
        pass
    finally:
        os.close(fd)
PY
}
# What `stats`, `stats gaps` and `stats status` print when this user cannot read the files (0.99.13, review B5, S2):
# the truth, instead of "no sample yet" or 0. Returns 0, having said so, when something there cannot be read.
stats_unreadable() {   # stats_unreadable SUBCOMMAND
  local f
  if [ -e "$STATS_DIR" ] && { [ ! -r "$STATS_DIR" ] || [ ! -x "$STATS_DIR" ]; }; then f=$STATS_DIR
  else
    for f in "$STATS_FILE" "$STATS_DIR"/seen-* "$STATS_DIR"/gaps-* "$STATS_DIR"/fleet-* "$STATS_DIR"/farthest-* ""; do
      [ -n "$f" ] || return 1
      [ ! -e "$f" ] || [ -r "$f" ] || break
    done
  fi
  echo "The statistics are there, but this user cannot read $f. Run with sudo: sudo zenithboard stats $1"
  echo "(0.99.13 and later make them readable at the next sample or update: cd ~/ZenithBoard && sudo zenithboard update)"
  return 0
}
stats_new_file() {
  zb_put "$STATS_FILE" 644 "$STATS_HEADER" || return 1
  [ "$(id -u)" -ne 0 ] || chown -h "$ZB_USER:$ZB_USER" -- "$STATS_FILE" 2>/dev/null || true
}

stats_on()  { stats_prepare_dir || { echo "Could not make $STATS_DIR"; return 1; }; cfg_set STATS 1; stats_install_units
              echo "Statistics are ON: one line every 15 minutes in $STATS_FILE, $STATS_DAYS days kept."
              # 0.54.16: the page only once the wall that serves it is installed
              if is_flightinfo 2>/dev/null; then echo "Read them with 'zenithboard stats' or at http://$(local_ip):$(cfg_get PORT 8080)/stats"
              else echo "Read them with 'zenithboard stats'; the /stats page comes with the wall (menu 2 The wall)."; fi; }
stats_off() { cfg_set STATS 0; stats_remove_units; echo "Statistics are OFF. The files are kept in $STATS_DIR (empty them: zenithboard stats clear)."; }
stats_clear() { rm -f "$STATS_DIR"/seen-* "$STATS_DIR"/gaps-* "$STATS_DIR"/farthest-* "$STATS_DIR"/fleet-* 2>/dev/null; [ -d "$STATS_DIR" ] && stats_new_file; echo "Statistics emptied ($STATS_DIR)."; }

# One sample. Reads the decoder's two files; writes one CSV line and today's aircraft. Silent when there is
# nothing to read: a decoder that is not running is not an error worth a journal line every quarter hour.
# 0.99.13 (review B5, S2): whatever the caller's umask (the unit had 0077), what a sample writes is readable by the
# Pi's other users, as the unit's own UMask=0022 now says too.
stats_run() ( umask 022; stats_sample )
stats_sample() {
  local d sj aj now day n msgs far pos seen ldb
  d=$(cfg_get DECODER ""); [ -n "$d" ] || d=$(installed_decoder); [ -n "$d" ] || return 0
  sj="$STATS_AIRCRAFT_DIR/$d/stats.json"; aj="$STATS_AIRCRAFT_DIR/$d/aircraft.json"
  [ -r "$sj" ] || return 0
  stats_prepare_dir || return 0
  # The row is stamped with the time of the sample; its messages and farthest (the decoder's last15min) are the
  # quarter hour before it, and `/stats` and `stats show` count them there (0.99.22, S5): the row stamped 00:00 is
  # the day before's 23:45 to 24:00. The aircraft with a position are a look at this moment, and the day's files
  # are this day's (the day before's last aircraft are added to its own file below).
  now=$(date '+%Y-%m-%d %H:%M'); day=${now%% *}
  # tar1090's aircraft database, when `data localdb on`: the type of an aircraft the decoder did not give one
  ldb=""; [ "$(cfg_get LOCAL_DB 0)" = 1 ] && ldb=$(cfg_get LOCAL_DB_DIR /usr/local/share/tar1090/git-db/db)
  n=$(python3 - "$sj" "$aj" "$(stats_day_file "$day")" "$(stats_fleet_file "$day")" "$ldb" "$ZB_HOME/flightinfo" "$(cfg_get PORT 8080)" <<'PY'
import json, sys, os, time, urllib.request
sj, aj, dayfile, fleetfile, localdb, flightinfo, port = sys.argv[1:8]
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
                        str(a.get("t") or "").strip().upper(), str(a.get("category") or "").strip().upper()[:2], mil,
                        time.strftime("%H%M")]
except Exception:
    pass
# 0.54.18: every aircraft the wall saw since, in its five-second look (flightinfo/server.py, SeenTracker). The look
# above, once a quarter hour, missed an aircraft that crossed between two: 11% fewer than FlightAware counted. Without
# the wall (stats on without it, 0.54.16) or with an older one, the quarter-hour look alone, as before.
today = os.path.basename(dayfile)[len("seen-"):]
live = {}
try:
    with urllib.request.urlopen("http://127.0.0.1:%s/api/seen" % port, timeout=5) as r:
        live = (json.load(r) or {}).get("days") or {}
except Exception:
    live = {}
for h, v in (live.get(today) or {}).items():
    if isinstance(v, list) and len(v) == 6 and len(h) == 6:
        seen.add(h)
        old_v = fleet.get(h)
        fleet[h] = [str(x) for x in v] if old_v is None else [old_v[k] or str(v[k]) for k in range(6)]
# the day before, for the aircraft of its last quarter hour (a sample at 00:05 reads them after midnight)
for day, d in live.items():
    if day == today or not isinstance(d, dict):
        continue
    pfile = dayfile[:-len(today)] + day
    if not os.path.exists(pfile):
        continue                                   # only a day the timer has already started
    try:
        prev = set(x.strip() for x in open(pfile) if x.strip())
        add = set(h for h in d if len(h) == 6) - prev
        if add:
            with open(pfile + ".tmp", "w") as fh:
                fh.write("\n".join(sorted(prev | add)) + "\n")
            os.replace(pfile + ".tmp", pfile)
        # and its fleet file, which the 24 hours' airlines and models read (the review, 0.54.18)
        pfleet = fleetfile[:-len(today)] + day
        rows = {}
        try:
            for line in open(pfleet):
                f = line.rstrip("\n").split("\t")
                if f and f[0]:
                    rows[f[0]] = f[1:]
        except FileNotFoundError:
            pass
        changed = False
        for h, v in d.items():
            if len(h) == 6 and isinstance(v, list) and len(v) == 6:
                old_v = (rows.get(h, []) + [""] * 6)[:6]
                new_v = [old_v[k] or str(v[k]) for k in range(6)]
                if h not in rows or new_v != rows[h][:6]:
                    rows[h] = new_v; changed = True
        if changed:
            with open(pfleet + ".tmp", "w") as fh:
                fh.write("".join("%s\t%s\n" % (h, "\t".join(v)) for h, v in sorted(rows.items())))
            os.replace(pfleet + ".tmp", pfleet)
    except OSError:
        pass
# the fleet file: what was known before is kept, a blank never replaces a value, the altitude is the latest.
# 0.36.0: two more columns, the emitter category (A1 light ... B1 glider, B6 drone) and a military mark; 0.37.0 one
# more, the time last seen (HHMM), for the statistics page's last 24 hours. Older lines are read as before
WIDTH = 6
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
  # 0.99.13 (review B5, W6): no radius in the question. RADIUS is in the owner's units (km, miles or nautical miles)
  # and was sent as radius_km, so a 10-mile radius sampled 10 km: imperial and aviation users were undercounted.
  # Asked without it, the wall applies RADIUS in its own units, the radius it shows.
  python3 - "$port" "$f" <<'PY' 2>/dev/null || true
import json, os, sys, urllib.request
port, out = sys.argv[1], sys.argv[2]
try:
    with urllib.request.urlopen("http://127.0.0.1:%s/api/planes" % port, timeout=5) as r:
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
  ! stats_unreadable gaps || return 1
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
  ! stats_unreadable show || return 1
  [ -f "$STATS_FILE" ] || { echo "No statistics yet. Turn them on with: sudo zenithboard stats on"; return 1; }
  local today yday rows out hours f counts
  today=$(date '+%Y-%m-%d'); yday=$(date -d yesterday '+%Y-%m-%d' 2>/dev/null)
  rows=$(awk 'NR>1' "$STATS_FILE" | grep -c . || true)
  echo "Statistics: $(stats_state), $rows samples of 15 minutes, $STATS_DAYS days kept    File: $STATS_FILE"
  [ "$rows" -gt 0 ] || { echo "No sample yet: the first one comes on the next quarter hour."; return 0; }
  # 0.99.13 (review B5, S6): each day's aircraft are its day file's, as for Today and on the /stats page. The CSV's
  # count is the one at the day's last sample, so the aircraft the wall added after it (its five-second look, and a
  # sample after midnight that writes the day before's last ones) were left out of Yesterday and of the average.
  counts="#"
  for f in "$STATS_DIR"/seen-????-??-??; do [ -f "$f" ] && counts="$counts"$'\n'"${f##*/seen-},$(grep -c . "$f" || true)"; done
  # The average covers complete days only: before today, sampled from the first hour (00) to the last (23). Today,
  # and a first or last day the timer was on for part of, would pull it down; the label gives how many it covers.
  # 0.99.22 (S5): the messages and the farthest in the quarter hour they measure (the stamp less 15 minutes, as on
  # /stats), the aircraft and the complete days at the stamp, the sampler's own day.
  out=$(awk -F, -v today="$today" -v yday="$yday" '
    function mdays(y, m) { return m == 2 ? ((y % 4 == 0 && y % 100 != 0) || y % 400 == 0 ? 29 : 28) : (m == 4 || m == 6 || m == 9 || m == 11 ? 30 : 31) }
    function prevday(d,   y, m, n) { y=substr(d,1,4)+0; m=substr(d,6,2)+0; n=substr(d,9,2)-1
      if (n < 1) { m--; if (m < 1) { m=12; y-- }; n=mdays(y, m) }
      return sprintf("%04d-%02d-%02d", y, m, n) }
    FNR==NR { if ($1 != "#") cnt[$1]=$2; next }
    FNR>1 { day=substr($1,1,10); hour=substr($1,12,2)
           q=substr($1,12,2)*60 + substr($1,15,2) - 15; mday=day; if (q < 0) { q+=1440; mday=prevday(day) }
           mhour=sprintf("%02d", int(q/60))
           msgs[mday]+=$2; if ($3>far[mday]) far[mday]=$3; if ($5>seen[day]) seen[day]=$5; days[day]=1; days[mday]=1
           if (hour=="00") first[day]=1; if (hour=="23") last[day]=1
           if (mday==today) h[mhour]+=$2 }
    function aircraft(d) { return (d in cnt) ? cnt[d] : seen[d] }
    END {
      n=0; for (d in days) n++
      printf "%-10s %5d aircraft seen   %7d messages   farthest %3d km\n", "Today", aircraft(today), msgs[today], far[today]
      if (yday in days) printf "%-10s %5d aircraft seen   %7d messages   farthest %3d km\n", "Yesterday", aircraft(yday), msgs[yday], far[yday]
      best=0; for (d in days) if (far[d]>best) { best=far[d]; bestd=d }
      nc=0; tot=0; for (d in days) if (d < today && (d in first) && (d in last)) { nc++; tot+=aircraft(d) }
      if (nc>0) printf "%-10s %5d aircraft/day on average over %d complete day%s   best %d km on %s\n", "Average", tot/nc, nc, (nc>1 ? "s" : ""), best, bestd
      else if (n>1) printf "%-10s no complete day yet (sampled from 00:00 to 23:45)   best %d km on %s\n", "Average", best, bestd
      printf "HOURS"; for (i=0;i<24;i++) printf " %d", h[sprintf("%02d",i)]; printf "\n"
    }' <(printf '%s\n' "$counts") "$STATS_FILE")
  echo
  printf '%s\n' "$out" | grep -v '^HOURS'
  hours=$(printf '%s\n' "$out" | sed -n 's/^HOURS //p')
  echo
  echo "Messages per hour today, 00 to 23"
  # shellcheck disable=SC2086
  printf ' %s\n' "$(stats_spark $hours)"
  echo
  # 0.54.18: with the wall running, its five-second look adds the aircraft the quarter-hour sample missed
  if is_flightinfo 2>/dev/null; then echo "Aircraft seen: with the wall answering on this Pi, every address it saw, looking every 5 seconds (a floor, but within a few percent). CSV: zenithboard stats csv"
  else echo "Aircraft seen is a floor: a sample every 15 minutes misses an aircraft that crossed in less (the wall, when installed, looks every 5 seconds). CSV: zenithboard stats csv"; fi
}
stats_csv() { ! stats_unreadable csv || return 1; [ -f "$STATS_FILE" ] && cat "$STATS_FILE" || { echo "No statistics yet."; return 1; }; }

stats_status() {
  echo "Statistics: $(stats_state)     Folder: $STATS_DIR"
  if stats_unreadable status; then :
  elif [ -f "$STATS_FILE" ]; then
    echo "Samples: $(awk 'NR>1' "$STATS_FILE" | grep -c . || true)   Days with aircraft files: $(ls "$STATS_DIR"/seen-* 2>/dev/null | wc -l)"
    [ "$(stats_state)" = on ] && systemctl list-timers "$STATS_UNIT.timer" --no-pager 2>/dev/null | sed -n '2p'
  fi
  echo "Page: http://$(local_ip):$(cfg_get PORT 8080)/stats"
}
