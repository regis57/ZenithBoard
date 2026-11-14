#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_mlat.sh
# 1.2: which network does MLAT (MLAT_NETWORK), with stand-ins for systemctl, piaware-config and apt. What matters:
# ADSB Exchange by default and nothing moved on a Pi that touches nothing; one client at a time, the others switched
# off before the chosen one is switched on; a network that is not installed cannot be chosen; the network that held
# MLAT being removed brings it back to ADSB Exchange; Flightradar24's stays off whatever is chosen; a feeder is
# restarted only when its switch moved; every choice says how to go back.
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" ZB_SKIP_SERVICES=1 ZB_BACKUP_DATA="$t/data" RB24_INI="$t/rbfeeder.ini" FR24_INI="$t/fr24feed.ini"
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/data"; touch "$ZENITHBOARD_ETC/config.env"
printf '#!/bin/bash\necho "systemctl $*" >> "%s/log"\n' "$t" > "$t/bin/systemctl"
# piaware-config: -showall lists the settings, "allow-mlat yes|no" sets it
cat > "$t/bin/piaware-config" <<P
#!/bin/bash
f="$t/piaware.conf"
if [ "\${1:-}" = -showall ]; then printf 'allow-auto-updates yes   # value set at /etc/piaware.conf:3\nallow-mlat %s   # value set at /etc/piaware.conf:7\nmlat-results yes   # using default value\n' "\$(cat "\$f")"; exit 0; fi
if [ "\${1:-}" = allow-mlat ]; then echo "\$2" > "\$f"; echo "piaware-config \$*" >> "$t/log"; fi
P
chmod +x "$t/bin/"*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/adsb.sh
. lib/adsb.sh
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

HAVE=" adsbx piaware fr24 radarbox "       # what is installed, for the stand-ins below
is_adsbx() { [[ $HAVE == *" adsbx "* ]]; }; is_piaware() { [[ $HAVE == *" piaware "* ]]; }
is_fr24() { [[ $HAVE == *" fr24 "* ]]; }; is_radarbox() { [[ $HAVE == *" radarbox "* ]]; }
unit_exists() { return 0; }; unit_active() { return 0; }; sleep() { :; }; mlat_count() { echo 1; }
PKG=""; pkg_installed() { [[ " $PKG " == *" $1 "* ]]; }
APT_OK=0; apt_install() { echo "apt_install $*" >> "$t/log"; [ "$APT_OK" = 0 ] && PKG="$PKG $1"; return "$APT_OK"; }
start() {   # the Pi as 1.1 left it: every other network's MLAT off
  echo no > "$t/piaware.conf"; printf 'mlat="no"\nmlat-without-gps="no"\nfr24key="abc"\n' > "$FR24_INI"
  printf '[client]\nkey=a1b2\n\n[mlat]\nautostart_mlat=false\nmlat_cmd=/usr/bin/mlat-client\n' > "$RB24_INI"; : > "$t/log"; : > "$ZENITHBOARD_ETC/config.env"; PKG=""; APT_OK=0
}
fa() { cat "$t/piaware.conf"; }; rb() { ini_sec_get "$RB24_INI" mlat autostart_mlat; }

# ---- the default: ADSB Exchange, and a Pi that touches nothing is not disturbed
start
check "default: ADSB Exchange, off by... nothing: the setting is not even written"  '[ "$(mlat_network)" = adsbx ] && [ -z "$(cfg_get MLAT_NETWORK "")" ]'
zb_mlat_guard > "$t/out" 2>&1
check "guard, default: ADSB Exchange's service on, the others left off"  'grep -q "enable --now adsbexchange-mlat" "$t/log" && [ "$(fa)" = no ] && [ "$(rb)" = false ] && grep -q "single MLAT client (ADSB Exchange)" "$t/out"'
check "guard, default: no feeder restarted for nothing"                  '! grep -q "restart" "$t/log" && ! grep -q "piaware-config" "$t/log"'
cfg_set MLAT_NETWORK bogus
check "a value that is not a network reads as ADSB Exchange"             '[ "$(mlat_network)" = adsbx ]'

# ---- FlightAware takes it: ADSB Exchange's off first, then FlightAware's on
start
mlat_set flightaware > "$t/out" 2>&1; rc=$?
check "flightaware: chosen, written, piaware told and restarted"         '[ "$rc" = 0 ] && [ "$(cfg_get MLAT_NETWORK)" = flightaware ] && [ "$(fa)" = yes ] && grep -q "systemctl restart piaware" "$t/log"'
check "flightaware: ADSB Exchange's client stopped BEFORE piaware's starts" '[ "$(grep -n "disable --now adsbexchange-mlat" "$t/log" | cut -d: -f1)" -lt "$(grep -n "piaware-config allow-mlat yes" "$t/log" | cut -d: -f1)" ] && ! grep -q "enable --now adsbexchange-mlat" "$t/log"'
check "flightaware: says what it needs and how to go back"               'grep -q "My ADS-B" "$t/out" && grep -q "Put it back:  sudo zenithboard mlat adsbx" "$t/out"'
: > "$t/log"; zb_mlat_guard >/dev/null 2>&1
check "guard again: nothing restarted, ADSB Exchange's kept off"         '! grep -q "restart" "$t/log" && grep -q "disable --now adsbexchange-mlat" "$t/log"'
mlat_set adsbx > "$t/out" 2>&1
check "and back: piaware off again, ADSB Exchange's on"                  '[ "$(fa)" = no ] && grep -q "enable --now adsbexchange-mlat" "$t/log" && grep -q "Put it back:  sudo zenithboard mlat flightaware" "$t/out"'

# ---- AirNav Radar: its client's package, then its line
start
mlat_set airnav > "$t/out" 2>&1
check "airnav: its mlat-client package installed, autostart_mlat true, restarted" 'grep -q "apt_install mlat-client" "$t/log" && [ "$(rb)" = true ] && grep -q "systemctl restart rbfeeder" "$t/log" && [ "$(cfg_get MLAT_NETWORK)" = airnav ]'
check "airnav: its command and key left as they were"                    'grep -qx "mlat_cmd=/usr/bin/mlat-client" "$RB24_INI" && grep -qx "key=a1b2" "$RB24_INI"'
start; APT_OK=1
mlat_set airnav > "$t/out" 2>&1
check "airnav, the package refused: its MLAT stays off and ADSB Exchange keeps it" '[ "$(rb)" = false ] && [ "$(cfg_get MLAT_NETWORK)" = adsbx ] && grep -q "enable --now adsbexchange-mlat" "$t/log" && grep -q "goes back to ADSB Exchange" "$t/out"'

# ---- none
start
mlat_set none > "$t/out" 2>&1
check "none: every client off, and it says what that means"              '[ "$(cfg_get MLAT_NETWORK)" = none ] && grep -q "disable --now adsbexchange-mlat" "$t/log" && ! grep -q "enable --now" "$t/log" && [ "$(fa)" = no ] && [ "$(rb)" = false ] && grep -q "No MLAT client runs" "$t/out"'

# ---- refusals
start
check "flightradar24 cannot be chosen, and it says why"                  '! mlat_set flightradar24 2> "$t/err" >/dev/null && grep -q "Flightradar24 is not offered" "$t/err" && [ -z "$(cfg_get MLAT_NETWORK "")" ]'
check "nor a word that is no network, nor nothing"                       '! mlat_set planefinder 2>/dev/null >&2 && ! mlat_set "" 2>/dev/null >&2 && ! mlat_set "adsbx; reboot" 2>/dev/null >&2 && [ ! -s "$t/log" ]'
HAVE=" adsbx fr24 "
check "a network that is not installed cannot be chosen"                 '! mlat_set flightaware 2> "$t/err" >/dev/null && grep -q "FlightAware is not installed" "$t/err" && [ -z "$(cfg_get MLAT_NETWORK "")" ] && [ ! -s "$t/log" ]'

# ---- the network that held MLAT is removed
HAVE=" adsbx piaware fr24 radarbox "; start; mlat_set flightaware >/dev/null 2>&1
HAVE=" adsbx fr24 radarbox "; : > "$t/log"
zb_mlat_guard > "$t/out" 2>&1
check "removed: MLAT comes back to ADSB Exchange, said, and its service started" '[ "$(cfg_get MLAT_NETWORK)" = adsbx ] && grep -q "not installed any more" "$t/out" && grep -q "enable --now adsbexchange-mlat" "$t/log"'

# ---- Flightradar24's stays off whatever is chosen, and a feeder that put it back on is corrected
HAVE=" adsbx piaware fr24 radarbox "
for n in adsbx flightaware airnav none; do
  start; printf 'mlat="yes"\nmlat-without-gps="yes"\nfr24key="abc"\n' > "$FR24_INI"
  mlat_set "$n" >/dev/null 2>&1
  check "fr24 off with $n chosen"                                        'grep -qx "mlat=\"no\"" "$FR24_INI" && grep -qx "mlat-without-gps=\"no\"" "$FR24_INI" && grep -qx "fr24key=\"abc\"" "$FR24_INI" && grep -q "restart fr24feed" "$t/log"'
done
start; echo yes > "$t/piaware.conf"; ini_sec_set "$RB24_INI" mlat autostart_mlat true
zb_mlat_guard >/dev/null 2>&1
check "an update that switched the others back on: all off again, each restarted once" '[ "$(fa)" = no ] && [ "$(rb)" = false ] && [ "$(grep -c "restart piaware" "$t/log")" = 1 ] && [ "$(grep -c "restart rbfeeder" "$t/log")" = 1 ]'

# ---- status, the rule table, the command
start; mlat_set flightaware >/dev/null 2>&1
out=$(mlat_status)
check "status: who does it, each network's switch, how to change"        'grep -q "MLAT is done by: FlightAware" <<<"$out" && grep -q "allow-mlat yes" <<<"$out" && grep -q "autostart_mlat false" <<<"$out" && grep -q "Flightradar24    off, always" <<<"$out" && grep -q "sudo zenithboard mlat adsbx|flightaware|airnav|none" <<<"$out"'
check "the table of rules holds the four choices, and an import checks them" 'rule_ok MLAT_NETWORK airnav && rule_ok MLAT_NETWORK none && ! rule_ok MLAT_NETWORK flightradar24 && [ "$MLAT_NETWORKS" = "adsbx flightaware airnav none" ]'
check "the command, the menu and the console's action"                   'grep -q "^  mlat)$" bin/zenithboard && grep -q "mlat \"5  MLAT: which network" lib/menus.sh && grep -q "\"mlat-network\"" flightinfo/console_actions.py && bash bin/zenithboard mlat 2>/dev/null | grep -q "MLAT is done by: "'
check "nothing in the code says ADSB Exchange owns MLAT for ever"        '! grep -n "ADSB Exchange keeps the only" bin/zenithboard lib/adsb.sh | grep -v "mlat_name"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
