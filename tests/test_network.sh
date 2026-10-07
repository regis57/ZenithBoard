#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_network.sh   Fixed IP and domain name: validation, mask autocomplete, the exact nmcli calls, curl configs, answers.
# shellcheck disable=SC2034  # variables are used inside the eval-ed check strings
set -u
cd "$(dirname "$0")/.." || exit 1
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ZENITHBOARD_ETC="$t/etc"; mkdir -p "$ZENITHBOARD_ETC"; touch "$ZENITHBOARD_ETC/config.env"
export ZB_SKIP_SERVICES=1 ZB_RUN_DIR="$t/run"
# shellcheck source=lib/common.sh
. lib/common.sh
# shellcheck source=lib/wifi.sh
. lib/wifi.sh
# shellcheck source=lib/network.sh
. lib/network.sh
# shellcheck source=lib/ddns.sh
. lib/ddns.sh
fail=0
ok()  { echo "ok   $1"; }
bad() { echo "FAIL $1"; fail=1; }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# ---- addresses and masks
check "valid ip"                 'net_valid_ip 192.168.1.50'
check "ip: 5 parts refused"      '! net_valid_ip 1.2.3.4.5'
check "ip: 256 refused"          '! net_valid_ip 192.168.1.256'
check "ip: letters refused"      '! net_valid_ip 192.168.one.5'
check "host ip: loopback refused" '! net_valid_host_ip 127.0.0.1'
check "host ip: multicast refused" '! net_valid_host_ip 224.0.0.1'
check "mask 255.255.255.0 -> 24" '[ "$(net_to_prefix 255.255.255.0)" = 24 ]'
check "mask /16 -> 16"           '[ "$(net_to_prefix /16)" = 16 ]'
check "mask 24 -> 24"            '[ "$(net_to_prefix 24)" = 24 ]'
check "mask 255.255.0.0 -> 16"   '[ "$(net_to_prefix 255.255.0.0)" = 16 ]'
check "mask 255.0.255.0 refused (holes)" '! net_to_prefix 255.0.255.0'
check "mask 33 refused"          '! net_to_prefix 33'
check "prefix 24 -> mask"        '[ "$(net_prefix_to_mask 24)" = 255.255.255.0 ]'
check "prefix 22 -> mask"        '[ "$(net_prefix_to_mask 22)" = 255.255.252.0 ]'
check "same subnet yes"          'net_same_subnet 192.168.1.50 192.168.1.1 24'
check "same subnet no"           '! net_same_subnet 192.168.1.50 192.168.2.1 24'
check "same subnet /16"          'net_same_subnet 192.168.1.50 192.168.2.1 16'
check "gateway guess"            '[ "$(net_guess_gateway 192.168.7.50 24)" = 192.168.7.1 ]'
check "gateway guess /16"        '[ "$(net_guess_gateway 10.1.2.3 16)" = 10.1.0.1 ]'

# ---- DNS
check "dns cloudflare"           '[ "$(net_dns_preset cloudflare)" = "1.1.1.1 1.0.0.1" ]'
check "dns google"               '[ "$(net_dns_preset google)" = "8.8.8.8 8.8.4.4" ]'
check "dns router = gateway"     '[ "$(net_dns_preset router 192.168.1.1)" = 192.168.1.1 ]'
check "dns custom commas"        '[ "$(net_dns_preset "9.9.9.9,149.112.112.112")" = "9.9.9.9 149.112.112.112" ]'
check "dns list valid"           'net_valid_dns_list "1.1.1.1 1.0.0.1"'
check "dns list bad"             '! net_valid_dns_list "1.1.1.1 nope"'
check "dns list empty refused"   '! net_valid_dns_list ""'

# ---- the nmcli calls (a stub records the arguments): only IPv4 address settings, never the route metric or autoconnect
mkdir -p "$t/bin"; printf '#!/bin/bash\necho "$*" >> %s/nm.log\n[ "$1 $2 $3" = "-t -f UUID,DEVICE" ] && echo "uuid-eth:eth0"\nexit 0\n' "$t" > "$t/bin/nmcli"; chmod +x "$t/bin/nmcli"
PATH="$t/bin:$PATH"
net_apply_static uuid-eth 192.168.1.50 24 192.168.1.1 "1.1.1.1 1.0.0.1"
check "static: modify call"      'grep -q "connection modify uuid uuid-eth ipv4.method manual ipv4.addresses 192.168.1.50/24 ipv4.gateway 192.168.1.1 ipv4.dns 1.1.1.1 1.0.0.1 ipv4.ignore-auto-dns yes" "$t/nm.log"'
check "static: metric untouched" '! grep -q "metric\|autoconnect\|priority" "$t/nm.log"'
check "static: active profile is restarted" 'grep -q "connection up uuid uuid-eth" "$t/nm.log"'
: > "$t/nm.log"; net_apply_dhcp uuid-eth
check "dhcp: back to auto"       'grep -q "ipv4.method auto ipv4.addresses  ipv4.gateway  ipv4.dns  ipv4.ignore-auto-dns no" "$t/nm.log"'
check "dhcp: metric untouched"   '! grep -q "metric\|autoconnect\|priority" "$t/nm.log"'
: > "$t/nm.log"; net_apply_static uuid-other 10.0.0.5 24 10.0.0.1 "8.8.8.8"
check "static: inactive profile saved only" '! grep -q "connection up" "$t/nm.log"'

# ---- profile list parsing (escaped colons in names)
printf '#!/bin/bash\nprintf "%%s\\n" "u1:802-3-ethernet:Wired connection 1" "u2:802-11-wireless:Home\\:Net" "u3:loopback:lo" "u4:vpn:Work"\n' > "$t/bin/nmcli"
out=$(net_profiles)
check "profiles: ethernet and wifi only" '[ "$(printf "%s\n" "$out" | wc -l)" = 2 ]'
check "profiles: type names"      'printf "%s\n" "$out" | grep -q "^u1	ethernet	Wired connection 1$"'
check "profiles: colon in name"   'printf "%s\n" "$out" | grep -q "^u2	wifi	Home:Net$"'

# ---- domain name: configs
check "host ok"                  'ddns_valid_host myplanes.duckdns.org'
check "host: space refused"      '! ddns_valid_host "my planes.org"'
check "host: injection refused"  '! ddns_valid_host "a.org&token=x"'
check "token ok"                 'ddns_valid_token abcd1234-ef56'
check "token too short"          '! ddns_valid_token abc'
check "token from direct URL"    '[ "$(ddns_token_from "https://freedns.afraid.org/dynamic/update.php?TokEN123abc456")" = TokEN123abc456 ]'
check "token from sync URL"      '[ "$(ddns_token_from "https://sync.afraid.org/u/TokEN123abc456/")" = TokEN123abc456 ]'
check "token bare"               '[ "$(ddns_token_from TokEN123abc456)" = TokEN123abc456 ]'
c=$(ddns_curl_config duckdns myplanes.duckdns.org "" tok12345678)
check "duckdns url: suffix stripped" 'printf "%s\n" "$c" | grep -q "domains=myplanes&token=tok12345678&ip=\""'
c=$(ddns_curl_config noip home.ddns.net 'us"er' 'pa\ss"w')
check "noip: hostname in url"    'printf "%s\n" "$c" | grep -q "hostname=home.ddns.net"'
check "noip: user escaped"       'printf "%s\n" "$c" | grep -qF "user = \"us\\\"er:pa\\\\ss\\\"w\""'
c=$(ddns_curl_config freedns x.mooo.com "" TokEN123abc456)
check "freedns url"              'printf "%s\n" "$c" | grep -q "sync.afraid.org/u/TokEN123abc456/"'
check "unknown provider refused" '! ddns_curl_config nope a b c'

# ---- domain name: answers
check "duckdns OK"               '[ "$(ddns_interpret duckdns OK)" = ok ]'
check "duckdns KO"               '[ "$(ddns_interpret duckdns KO)" = fail ]'
check "noip good"                '[ "$(ddns_interpret noip "good 1.2.3.4")" = ok ]'
check "noip nochg"               '[ "$(ddns_interpret noip "nochg 1.2.3.4")" = nochg ]'
check "noip badauth"             '[ "$(ddns_interpret noip badauth)" = fail ]'
check "freedns updated"          '[ "$(ddns_interpret freedns "Updated 1 host(s) a.mooo.com to 1.2.3.4 in 0.1 seconds")" = ok ]'
check "freedns unchanged"        '[ "$(ddns_interpret freedns "ERROR: Address 1.2.3.4 has not changed.")" = nochg ]'
check "freedns error"            '[ "$(ddns_interpret freedns "ERROR: Invalid update URL")" = fail ]'
check "empty answer is a failure" '[ "$(ddns_interpret duckdns "")" = fail ]'

# ---- domain name: stored root-only, off deletes the key
ZB_ETC="$t/etc"; DDNS_CURL="$t/etc/ddns.curl"; DDNS_STATE="$t/run/zenithboard-ddns.status"
printf '#!/bin/bash\necho OK\n' > "$t/bin/curl"; chmod +x "$t/bin/curl"
ZB_HOME="$t/none"
out=$(ddns_set duckdns myplanes.duckdns.org "" tok12345678)
check "set: succeeds"            'printf "%s" "$out" | grep -q "^OK"'
check "set: key file is mode 600" '[ "$(stat -c %a "$DDNS_CURL")" = 600 ]'
check "set: provider saved"      '[ "$(cfg_get DDNS_PROVIDER)" = duckdns ] && [ "$(cfg_get DDNS_HOST)" = myplanes.duckdns.org ]'
check "set: secret not in config" '! grep -q tok12345678 "$ZENITHBOARD_ETC/config.env"'
check "set: state written"       'grep -q "ok" "$DDNS_STATE"'
printf '#!/bin/bash\necho KO\n' > "$t/bin/curl"
check "update: a refusal is reported" '! ddns_update && grep -q FAILED "$DDNS_STATE"'
ddns_off
check "off: key deleted"         '[ ! -e "$DDNS_CURL" ] && [ "$(cfg_get DDNS_PROVIDER)" = none ]'
out=$(ddns_set noip a.ddns.net "" ""); check "noip without key refused" '[ $? -ne 0 ] || printf "%s" "$out" | grep -q needs'
out=$(ddns_set duckdns a.duckdns.org "" "bad"); check "bad token refused" 'printf "%s" "$out" | grep -q "token"'

[ "$fail" = 0 ] && echo "ALL OK" || { echo "SOME FAILED"; exit 1; }
