#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Gain of the RTL-SDR dongle: show it, judge it from the decoder's own statistics, change it. Nothing here is automatic.
# Files can be redirected for tests: ZB_DEFAULT_DIR (/etc/default) and ZB_STATS_DIR (/run).

GAIN_DEFAULT_DIR="${ZB_DEFAULT_DIR:-/etc/default}"
GAIN_STATS_DIR="${ZB_STATS_DIR:-/run}"
# the gain steps an R820T/R828T dongle (the usual RTL-SDR) really has; any other value is rounded to the nearest one
GAIN_STEPS="0.0 0.9 1.4 2.7 3.7 7.7 8.7 12.5 14.4 15.7 16.6 19.7 20.7 22.9 25.4 28.0 29.7 32.8 33.8 36.4 37.2 38.6 40.2 42.1 43.4 43.9 44.5 48.0 49.6"
GAIN_MAX=49.6

gain_decoder() { local d; d=$(cfg_get DECODER ""); [ -n "$d" ] || d=$(installed_decoder); echo "$d"; }
gain_file()    { echo "$GAIN_DEFAULT_DIR/$1"; }          # gain_file readsb|dump1090-fa
gain_stats()   { echo "$GAIN_STATS_DIR/$1/stats.json"; }

# gain_current DECODER -> a number, "auto" (readsb's own auto-gain), "agc" (the dongle's automatic gain, -10) or "default"
gain_current() {
  local f g; f=$(gain_file "$1"); [ -f "$f" ] || { echo default; return 0; }
  g=$(grep -E '^(RECEIVER|DECODER)_OPTIONS=' "$f" | grep -oE -e '--gain[ =][^" ]+' | head -1 | sed -E 's/--gain[ =]//')
  case "$g" in
    "") echo default ;;
    auto*) echo auto ;;
    -*) echo agc ;;
    *) echo "$g" ;;
  esac
}

gain_label() {
  case "$1" in
    default) echo "not set (the decoder uses the maximum)" ;;
    auto) echo "automatic (readsb auto-gain, experimental)" ;;
    agc) echo "automatic (-10: the dongle's own AGC, not the best for aircraft)" ;;
    *) echo "$1 dB" ;;
  esac
}

# gain_nearest VALUE -> the closest real step, or "max"
gain_nearest() {
  case "$1" in max) echo "$GAIN_MAX"; return 0 ;; esac
  [[ "$1" =~ ^[0-9]+(\.[0-9]+)?$ ]] || return 1
  awk -v want="$1" -v steps="$GAIN_STEPS" 'BEGIN{n=split(steps,s," ");b=s[1];for(i=2;i<=n;i++){d=s[i]-want;if(d<0)d=-d;e=b-want;if(e<0)e=-e;if(d<e)b=s[i]}print b}'
}

# gain_step_move CURRENT up|down -> the neighbouring step
gain_step_move() {
  local cur="$1" dir="$2"
  [[ "$cur" =~ ^[0-9]+(\.[0-9]+)?$ ]] || cur=$GAIN_MAX
  awk -v c="$cur" -v dir="$dir" -v steps="$GAIN_STEPS" 'BEGIN{n=split(steps,s," ");k=1;for(i=1;i<=n;i++){d=s[i]-c;if(d<0)d=-d;e=s[k]-c;if(e<0)e=-e;if(d<e)k=i}
    if(dir=="up"&&k<n)k++; if(dir=="down"&&k>1)k--; print s[k]}'
}

# gain_write DECODER VALUE|default : replace any --gain in the options line, or add it. Other options (serial, device, lat/lon) stay.
# Both readsb and dump1090-fa keep it in RECEIVER_OPTIONS of /etc/default/<decoder>.
gain_write() {
  local d="$1" v="$2" f var=RECEIVER_OPTIONS
  f=$(gain_file "$d"); [ -f "$f" ] || { err "$f not found: is $d installed?"; return 1; }
  sed -i -E 's/ ?--gain[ =][^" ]+//; s/^([A-Z_]+_OPTIONS=") +/\1/' "$f"
  [ "$v" = default ] && return 0
  if grep -qE "^$var=\"" "$f"; then
    sed -i -E "/^$var=\"/{s|^($var=\")|\1--gain $v |;s| +\"\$|\"|}" "$f"
  else
    printf '%s="--gain %s"\n' "$var" "$v" >> "$f"
  fi
}

gain_restart() { [ "${ZB_SKIP_SERVICES:-}" = 1 ] || systemctl restart "$1"; }

# gain_set VALUE|max|default
gain_set() {
  local d v="$1" g
  d=$(gain_decoder); [ -n "$d" ] || { err "No decoder installed yet: use menu 1 ADSB first."; return 1; }
  if [ "$v" = default ]; then g=default
  else g=$(gain_nearest "$v") || { err "Gain must be a number in dB (0 to $GAIN_MAX), 'max' or 'default'. Steps: $GAIN_STEPS"; return 1; }
  fi
  gain_write "$d" "$g" || return 1
  gain_restart "$d"
  if [ "$g" = default ]; then echo "Gain: the setting was removed; $d uses its default again."
  else echo "Gain set to $g dB on $d (the dongle only has fixed steps, so $v became $g). The decoder was restarted."; fi
  if [ "$(gain_current "$d")" = default ] && [ "$g" != default ]; then warn "The gain line could not be found in $(gain_file "$d"): check the file."; fi
  if [ -f /boot/piaware-config.txt ] && [ "$d" = dump1090-fa ]; then
    echo "Note: on the PiAware SD-card image the gain is kept in /boot/piaware-config.txt and may be put back at boot: then use  sudo piaware-config rtlsdr-gain $g"
  fi
  echo "Now wait 15-30 minutes and run:  zenithboard gain check"
}

# gain_numbers DECODER -> "ACCEPTED STRONG MAXKM SIGNAL PEAK" from the last 15 minutes, or nothing
gain_numbers() {
  local f; f=$(gain_stats "$1"); [ -r "$f" ] || return 1
  python3 - "$f" <<'PY'
import json, sys
try:
    j = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
w = j.get("last15min") or j.get("last5min") or j.get("last1min") or {}
l = w.get("local") or {}
acc = l.get("accepted")
acc = sum(acc) if isinstance(acc, list) else (acc or 0)
md = w.get("max_distance") or 0
print(acc, l.get("strong_signals", 0) or 0, round(md / 1000.0), l.get("signal", ""), l.get("peak_signal", ""))
PY
}

# gain_verdict ACCEPTED STRONG CURRENT -> prints the advice
gain_verdict() {
  local acc="$1" strong="$2" cur="$3" pct
  if [ "${acc:-0}" -lt 300 ]; then echo "Not enough messages yet to judge (${acc:-0} in the last 15 minutes). Check again in a while, ideally when aircraft are flying."; return 0; fi
  pct=$(awk -v s="$strong" -v a="$acc" 'BEGIN{printf "%.1f", 100*s/a}')
  if awk -v p="$pct" 'BEGIN{exit !(p>5)}'; then
    echo "TOO HIGH: $pct% of the messages are very strong (more than 5%). The receiver is overloaded. Lower the gain by ONE step ($(gain_step_move "$cur" down) dB), wait 15-30 minutes, check again."
  elif awk -v p="$pct" 'BEGIN{exit !(p<1)}'; then
    if [ "$cur" = "$GAIN_MAX" ] || [ "$cur" = default ]; then echo "FINE: $pct% strong messages (under 1%) and the gain is already at its maximum. Nothing more to gain here (the share is lower at night: judge it at a busy hour)."
    else echo "LOW SHARE: $pct% strong messages (under 1%). On its own that is no reason to change anything: the share depends on traffic and is lower at night or when few aircraft are close. Check again at a BUSY hour. If it is still under 1% then, you may try ONE step higher ($(gain_step_move "$cur" up) dB), wait 15-30 minutes, then compare range and aircraft count."; fi
  else
    echo "GOOD: $pct% strong messages, in the usual 1-5% range. Leave the gain as it is."
  fi
}

gain_check() {
  local d cur n acc strong km sig peak pct
  d=$(gain_decoder); [ -n "$d" ] || { echo "No decoder installed yet: use menu 1 ADSB first."; return 1; }
  cur=$(gain_current "$d")
  echo "Decoder: $d     Gain: $(gain_label "$cur")     Checked: $(date '+%Y-%m-%d %H:%M')"
  if ! n=$(gain_numbers "$d") || [ -z "$n" ]; then echo "No statistics yet ($(gain_stats "$d") missing). Wait a minute after (re)starting the decoder."; return 1; fi
  read -r acc strong km sig peak <<<"$n"
  pct=$(awk -v s="$strong" -v a="$acc" 'BEGIN{if(a>0)printf "%.1f",100*s/a; else print "0.0"}')
  echo "Last 15 minutes:  $acc messages accepted,  $strong very strong ($pct%),  farthest aircraft ${km} km"
  [ -z "$sig" ] || echo "Average signal ${sig} dBFS,  strongest ${peak} dBFS"
  echo
  case "$cur" in
    auto|agc) echo "The gain is automatic, so there is nothing to lower or raise by hand. For a fixed gain choose a value in the menu (start with the maximum $GAIN_MAX)."; echo ;;
  esac
  gain_verdict "$acc" "$strong" "$cur"
  echo
  echo "Method: change one step at a time and wait 15-30 minutes. Keep what gives the most aircraft and the longest range, with 1-5% strong messages."
}

# ------------------------------------------------------------------ 24-hour log
# One line every 15 minutes in a CSV file, keeping the last 24 hours and nothing more, so the gain can be
# judged over a whole day (quiet night, busy evening) instead of from a single check. Off until turned on.
GAIN_LOG_UNIT=zenithboard-gain-log
GAIN_LOG_UNIT_DIR="${ZB_SYSTEMD_DIR:-/etc/systemd/system}"
GAIN_LOG_FILE="${ZB_VAR_DIR:-/var/lib/zenithboard}/gain-log.csv"
GAIN_LOG_HEADER="when,gain_db,decoder,accepted,strong,strong_pct,farthest_km,avg_dbfs,peak_dbfs"
GAIN_LOG_HOURS=24
GAIN_LOG_MAX_ROWS=96          # 24 h at one line every 15 minutes

gain_log_state() { [ "$(cfg_get GAINLOG 0)" = 1 ] && echo on || echo off; }
gain_log_path()  { echo "$GAIN_LOG_FILE"; }

gain_log_install_units() {
  [ -f "$ZB_HOME/systemd/$GAIN_LOG_UNIT.service" ] || return 0
  install -d -m 755 "$GAIN_LOG_UNIT_DIR"
  install -m 644 "$ZB_HOME/systemd/$GAIN_LOG_UNIT.service" "$ZB_HOME/systemd/$GAIN_LOG_UNIT.timer" "$GAIN_LOG_UNIT_DIR/"
  systemctl daemon-reload; systemctl enable --now "$GAIN_LOG_UNIT.timer" >/dev/null 2>&1 || true
}
gain_log_remove_units() {
  systemctl disable --now "$GAIN_LOG_UNIT.timer" >/dev/null 2>&1 || true
  rm -f "$GAIN_LOG_UNIT_DIR/$GAIN_LOG_UNIT.service" "$GAIN_LOG_UNIT_DIR/$GAIN_LOG_UNIT.timer"; systemctl daemon-reload 2>/dev/null || true
}

gain_log_start() {
  install -d -m 755 "$(dirname "$GAIN_LOG_FILE")" 2>/dev/null || true
  [ -f "$GAIN_LOG_FILE" ] || echo "$GAIN_LOG_HEADER" > "$GAIN_LOG_FILE"
  cfg_set GAINLOG 1; gain_log_install_units
  echo "Gain log is ON: one line every 15 minutes in $GAIN_LOG_FILE, keeping the last $GAIN_LOG_HOURS hours."
  echo "Read it with 'zenithboard gain log show', empty it with 'zenithboard gain log clear'."
}
gain_log_stop() { cfg_set GAINLOG 0; gain_log_remove_units; echo "Gain log is OFF. The file is kept: $GAIN_LOG_FILE"; }
gain_log_clear() {
  install -d -m 755 "$(dirname "$GAIN_LOG_FILE")" 2>/dev/null || true
  echo "$GAIN_LOG_HEADER" > "$GAIN_LOG_FILE"; echo "Gain log emptied ($GAIN_LOG_FILE)."
}

# Drop anything older than 24 hours. Timestamps are written YYYY-MM-DD HH:MM, which compares correctly as text.
gain_log_prune() {
  local cut tmp
  [ -f "$GAIN_LOG_FILE" ] || return 0
  cut=$(date -d "$GAIN_LOG_HOURS hours ago" '+%Y-%m-%d %H:%M' 2>/dev/null) || return 0
  tmp="$GAIN_LOG_FILE.tmp"
  { echo "$GAIN_LOG_HEADER"
    awk -F, -v c="$cut" 'NR>1 && $1 >= c' "$GAIN_LOG_FILE" | tail -n "$GAIN_LOG_MAX_ROWS"
  } > "$tmp" && mv "$tmp" "$GAIN_LOG_FILE"
}

# One measurement appended. Called by the timer; safe to run by hand.
gain_log_run() {
  local d cur n acc strong km sig peak pct
  [ -f "$GAIN_LOG_FILE" ] || { install -d -m 755 "$(dirname "$GAIN_LOG_FILE")" 2>/dev/null || true; echo "$GAIN_LOG_HEADER" > "$GAIN_LOG_FILE"; }
  d=$(gain_decoder); [ -n "$d" ] || return 0
  n=$(gain_numbers "$d") || return 0
  [ -n "$n" ] || return 0
  read -r acc strong km sig peak <<<"$n"
  pct=$(awk -v s="$strong" -v a="$acc" 'BEGIN{if(a>0)printf "%.2f",100*s/a; else print "0.00"}')
  cur=$(gain_current "$d")
  printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$(date '+%Y-%m-%d %H:%M')" "$cur" "$d" "$acc" "$strong" "$pct" "$km" "$sig" "$peak" >> "$GAIN_LOG_FILE"
  gain_log_prune
}

gain_log_show() {
  [ -f "$GAIN_LOG_FILE" ] || { echo "No gain log yet. Turn it on with 'sudo zenithboard gain log on'."; return 1; }
  cat "$GAIN_LOG_FILE"
}

gain_log_status() {
  local rows first last
  echo "Gain log: $(gain_log_state)     File: $GAIN_LOG_FILE"
  if [ -f "$GAIN_LOG_FILE" ]; then
    rows=$(awk 'NR>1' "$GAIN_LOG_FILE" | grep -c . || true)
    first=$(awk -F, 'NR==2{print $1}' "$GAIN_LOG_FILE")
    last=$(awk -F, 'END{if(NR>1)print $1}' "$GAIN_LOG_FILE")
    echo "Measurements: $rows (of $GAIN_LOG_MAX_ROWS for a full $GAIN_LOG_HOURS hours)"
    [ -n "$first" ] && echo "From $first to $last"
  else
    echo "Measurements: none yet"
  fi
  [ "$(gain_log_state)" = on ] && systemctl list-timers "$GAIN_LOG_UNIT.timer" --no-pager 2>/dev/null | sed -n '2p'
  return 0
}

gain_menu() {
  local c d cur v
  d=$(gain_decoder)
  if [ -z "$d" ]; then wt_msg "No decoder installed yet.\n\nInstall one first in menu 1 ADSB." 10; return 0; fi
  while true; do
    cur=$(gain_current "$d")
    c=$(wt_menu "Gain: how much the dongle amplifies the radio signal ($d).\n\nNow: $(gain_label "$cur")\n\nStart with the maximum. Lower it only if the check says the receiver is overloaded. Nothing changes by itself." \
      check "Check: is my gain right? (reads the last 15 minutes)" \
      max "Set the maximum ($GAIN_MAX dB, the usual best start)" \
      down "One step lower" \
      up "One step higher" \
      value "Type a value in dB" \
      default "Remove the setting (the decoder's default)" \
      log "24-hour log: a measurement every 15 min, as a CSV table ($(gain_log_state))" \
      back "Return to the previous menu") || return 0
    case "$c" in
      check) clear; gain_check; echo; read -rp "Press Enter to continue..." _ ;;
      max) clear; gain_set max; echo; read -rp "Press Enter to continue..." _ ;;
      down) clear; gain_set "$(gain_step_move "$cur" down)"; echo; read -rp "Press Enter to continue..." _ ;;
      up) clear; gain_set "$(gain_step_move "$cur" up)"; echo; read -rp "Press Enter to continue..." _ ;;
      value)
        v=$(wt_input "Gain in dB. The dongle has fixed steps, so the nearest one is used:\n$GAIN_STEPS" "$GAIN_MAX") || continue
        clear; gain_set "$v" || true; echo; read -rp "Press Enter to continue..." _ ;;
      default) clear; gain_set default; echo; read -rp "Press Enter to continue..." _ ;;
      log) gain_log_menu ;;
      *) return 0 ;;
    esac
  done
}

gain_log_menu() {
  local c
  while true; do
    c=$(wt_menu "24-hour gain log ($(gain_log_state)).\n\nOne measurement every 15 minutes, kept for 24 hours and no longer, in a CSV file you can open in a spreadsheet:\n$GAIN_LOG_FILE\n\nUseful to see the quiet night and the busy evening before deciding on a gain." \
      on "Start recording" \
      off "Stop recording (the file is kept)" \
      show "Show what has been recorded" \
      status "How many measurements so far" \
      clear "Empty the file and start again" \
      back "Return to the previous menu") || return 0
    case "$c" in
      on) clear; gain_log_start; echo; read -rp "Press Enter to continue..." _ ;;
      off) clear; gain_log_stop; echo; read -rp "Press Enter to continue..." _ ;;
      show) clear; gain_log_show | head -120; echo; read -rp "Press Enter to continue..." _ ;;
      status) clear; gain_log_status; echo; read -rp "Press Enter to continue..." _ ;;
      clear) clear; gain_log_clear; echo; read -rp "Press Enter to continue..." _ ;;
      *) return 0 ;;
    esac
  done
}
