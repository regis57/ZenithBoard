#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_graphs.sh   0.32.0: graphs1090, off by default. `on` refuses without lighttpd or room in /run,
# runs the author's installer and notes the packages it added; `off` runs its uninstaller, removes what it leaves
# behind and those packages only (never purge: Debian's purge of collectd-core deletes the history), keeps the
# history, and leaves a package that something else now needs. Stubs: systemctl, dpkg-query, apt-get, df, lighttpd,
# and an installer standing in for wiedehopf's, writing under a folder that stands in for /.
# shellcheck disable=SC2034
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc" T="$t" ZB_GRAPHS_ROOT="$t/root"
mkdir -p "$ZENITHBOARD_ETC" "$t/bin" "$t/root/run" "$t/root/etc/lighttpd/conf-enabled" "$t/root/etc/lighttpd/conf-available"
touch "$ZENITHBOARD_ETC/config.env"
printf 'bash\ngit\nlighttpd\nwget\n' > "$t/pkgs"; echo 200 > "$t/runfree"; : > "$t/extra"
# lighttpd's mod_alias was already there (tar1090 needs it): off must leave it
echo 'server.modules += ( "mod_alias" )' > "$t/root/etc/lighttpd/conf-enabled/07-mod_alias.conf"
printf '#!/bin/bash\necho "systemctl $*" >> "$T/log"\n' > "$t/bin/systemctl"
printf '#!/bin/bash\ncat "$T/pkgs"\n' > "$t/bin/dpkg-query"
cat > "$t/bin/df" <<'S'
#!/bin/bash
echo "Filesystem 1M-blocks Used Available Use% Mounted on"
echo "tmpfs 92 1 $(cat "$T/runfree") 1% /run"
S
cat > "$t/bin/apt-get" <<'S'
#!/bin/bash
echo "apt-get $*" >> "$T/log"
if [ "$1" = -s ]; then shift 2; for p in "$@" $(cat "$T/extra"); do echo "Remv $p [1.0]"; done; exit 0; fi
[ "$1" = remove ] || exit 0
shift 2; for p in "$@"; do sed -i "/^$p\$/d" "$T/pkgs"; done
S
printf '#!/bin/bash\necho 192.168.1.50\n' > "$t/bin/hostname"
chmod +x "$t"/bin/*; export PATH="$t/bin:$PATH"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/versions.sh
. lib/versions.sh
# shellcheck source=lib/graphs.sh
. lib/graphs.sh
installed_decoder() { echo readsb; }
has_lighttpd=0; graphs_has_lighttpd() { [ "$has_lighttpd" = 1 ]; }
local_ip() { echo 192.168.1.50; }
# wiedehopf's installer, as far as what it leaves on the Pi goes (read in its install.sh, 20 October 2026)
fetch() {
  echo "fetch $1" >> "$T/log"
  cat > "$2" <<'S'
R="$ZB_GRAPHS_ROOT"
printf 'collectd-core\nrrdtool\nlibpython3.11\n' >> "$T/pkgs"; sort -u -o "$T/pkgs" "$T/pkgs"
mkdir -p "$R/usr/share/graphs1090/html" "$R/lib/systemd/system" "$R/etc/default" "$R/etc/cron.d" "$R/etc/collectd" "$R/var/lib/collectd/rrd" "$R/etc/systemd/system/collectd.service.d"
echo '<html>' > "$R/usr/share/graphs1090/html/index.html"; echo 1.42 > "$R/usr/share/graphs1090/version"
printf 'echo "uninstall.sh ran" >> "$T/log"; rm -r "%s/usr/share/graphs1090"\n' "$R" > "$R/usr/share/graphs1090/uninstall.sh"
for f in 88-graphs1090.conf 95-graphs1090-otherport.conf; do echo x > "$R/etc/lighttpd/conf-available/$f"; ln -snf "$R/etc/lighttpd/conf-available/$f" "$R/etc/lighttpd/conf-enabled/$f"; done
echo x > "$R/lib/systemd/system/graphs1090.service"; echo DB= > "$R/etc/default/graphs1090"; echo cron > "$R/etc/cron.d/collectd_to_disk"
echo conf > "$R/etc/collectd/collectd.conf"; echo malarky > "$R/etc/systemd/system/collectd.service.d/malarky.conf"
echo rrd > "$R/var/lib/collectd/rrd/localhost.tar.gz"
S
}
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

check "off by default"                                 '[ "$(graphs_state)" = off ] && graphs_status | grep -q "graphs on"'
check "no lighttpd: refused, nothing changed"          '! graphs_on >/dev/null 2>&1 && [ ! -f "$GRAPHS_STATE" ] && ! grep -q fetch "$t/log" 2>/dev/null'
has_lighttpd=1
echo 20 > "$t/runfree"
check "too little room in /run: refused"               '! graphs_on 2>&1 | grep -q "graphs1090 is ON" && [ ! -f "$GRAPHS_STATE" ] && ! grep -q fetch "$t/log" 2>/dev/null'
echo 200 > "$t/runfree"
out=$(graphs_on 2>&1)
check "on: the author's installer, from the pinned address" 'grep -q "fetch https://github.com/wiedehopf/graphs1090/raw/master/install.sh" "$t/log"'
check "on: says the port and the once-a-day write"     'printf "%s" "$out" | grep -q ":8542/" && printf "%s" "$out" | grep -q "23:42" && [ "$(graphs_state)" = on ]'
check "on: notes exactly the packages it added"        '[ "$(graphs_state_get ADDED)" = "collectd-core libpython3.11 rrdtool" ]'
check "on: notes what was there before"                '[ "$(graphs_state_get COLLECTD_ETC)" = 0 ] && [ "$(graphs_state_get MOD_ALIAS)" = 1 ] && [ "$(cfg_get GRAPHS1090)" = 1 ]'
check "on again: already on, nothing downloaded"       'graphs_on | grep -q "already on" && [ "$(grep -c "^fetch" "$t/log")" = 1 ]'
graphs_update >/dev/null 2>&1
check "update: the installer again, the list unchanged" '[ "$(grep -c "^fetch" "$t/log")" = 2 ] && [ "$(graphs_state_get ADDED)" = "collectd-core libpython3.11 rrdtool" ]'
check "status: the version and the address"            'graphs_status | grep -q "on (version 1.42)" && graphs_status | grep -q "192.168.1.50:8542"'

out=$(graphs_off 2>&1)
R="$t/root"
check "off: its own uninstaller ran"                   'grep -q "uninstall.sh ran" "$t/log" && [ ! -e "$R/usr/share/graphs1090" ]'
check "off: lighttpd's two files gone, mod_alias kept" '[ -z "$(ls "$R/etc/lighttpd/conf-enabled" | grep graphs)" ] && [ -z "$(ls "$R/etc/lighttpd/conf-available" | grep graphs)" ] && [ -f "$R/etc/lighttpd/conf-enabled/07-mod_alias.conf" ]'
check "off: unit, settings, cron line, drop-in gone"   '[ ! -e "$R/lib/systemd/system/graphs1090.service" ] && [ ! -e "$R/etc/default/graphs1090" ] && [ ! -e "$R/etc/cron.d/collectd_to_disk" ] && [ ! -e "$R/etc/systemd/system/collectd.service.d/malarky.conf" ]'
check "off: lighttpd restarted"                        'grep -q "systemctl restart lighttpd" "$t/log"'
check "off: the added packages removed, never purged"  'grep -q "^apt-get remove -y collectd-core libpython3.11 rrdtool$" "$t/log" && ! grep -q purge "$t/log" && [ "$(tr "\n" " " < "$t/pkgs")" = "bash git lighttpd wget " ]'
check "off: collectd's folder goes (it was not there)" '[ ! -e "$R/etc/collectd" ]'
check "off: the history stays, and how to delete it is said" '[ -f "$R/var/lib/collectd/rrd/localhost.tar.gz" ] && printf "%s" "$out" | grep -q "sudo rm -r /var/lib/collectd/rrd"'
check "off: state gone, setting off"                   '[ ! -f "$GRAPHS_STATE" ] && [ "$(cfg_get GRAPHS1090)" = 0 ] && [ "$(graphs_state)" = off ]'
check "off again: already off"                         'graphs_off | grep -q "already off"'

# something installed since needs one of them: apt would take it too, so nothing is removed
graphs_on >/dev/null 2>&1; echo kodi > "$t/extra"; : > "$t/log"
out=$(graphs_off 2>&1)
check "a package now needed elsewhere: all kept, said" '! grep -q "^apt-get remove -y" "$t/log" && printf "%s" "$out" | grep -q "would also remove: kodi" && grep -q "^collectd-core$" "$t/pkgs" && [ -d "$R/etc/collectd" ]'

# the rest of ZenithBoard knows it
check "command: graphs on|off|status"                  'grep -q "on)     root_or_die; graphs_on" bin/zenithboard && grep -q "zenithboard graphs on|off|status" bin/zenithboard'
check "menu: Settings, Receiver, 6"                    'grep -q "graphs \"6  graphs1090" install.sh'
check "update: a component when on"                    'grep -q "graphs1090) is_graphs" lib/update.sh && grep -q "graphs_update" lib/update.sh'
check "security: port 8542 is known"                   'grep -q "8542) known=" lib/security.sh'
check "uninstall everything takes it"                  'grep -q "then graphs_off; fi" install.sh'
check "never purge, never apt_remove (purge)"          '! grep -v "^ *#" lib/graphs.sh | grep -q "purge\|apt_remove"'
[ "$fail" = 0 ] && echo "ALL OK"; exit "$fail"
