#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Run: bash tests/test_hardware.sh   (checks low-memory / old-Pi detection with fake system files)
set -e
cd "$(dirname "$0")/.."
. lib/common.sh
t=$(mktemp -d)
printf 'MemTotal:         948000 kB\nMemAvailable:     700000 kB\n' > "$t/mem1"
printf 'MemTotal:        1900000 kB\nMemAvailable:    1500000 kB\n' > "$t/mem2"
printf 'MemTotal:        3900000 kB\nMemAvailable:    3000000 kB\n' > "$t/mem4"
ZB_MEMINFO="$t/mem1" is_low_mem   || { echo "1 GB board must be low-mem"; exit 1; }
ZB_MEMINFO="$t/mem2" is_low_mem   && { echo "2 GB board must NOT be low-mem"; exit 1; }
ZB_MEMINFO="$t/mem4" is_low_mem   && { echo "4 GB board must NOT be low-mem"; exit 1; }
[ "$(ZB_MEMINFO="$t/mem1" mem_total_mb)" = 925 ] || { echo "mem_total_mb wrong"; exit 1; }
printf 'Raspberry Pi 3 Model B Rev 1.2\0' > "$t/m3"; printf 'Raspberry Pi 4 Model B Rev 1.4\0' > "$t/m4"
printf 'Raspberry Pi Zero 2 W Rev 1.0\0' > "$t/mz"; printf 'Raspberry Pi 5 Model B Rev 1.0\0' > "$t/m5"
ZB_PI_MODEL_FILE="$t/m3" is_old_pi || { echo "Pi 3 must be old"; exit 1; }
ZB_PI_MODEL_FILE="$t/mz" is_old_pi || { echo "Pi Zero must be old"; exit 1; }
ZB_PI_MODEL_FILE="$t/m4" is_old_pi && { echo "Pi 4 must not be old"; exit 1; }
ZB_PI_MODEL_FILE="$t/m5" is_old_pi && { echo "Pi 5 must not be old"; exit 1; }
# The installer's notice (0.20.1): what a Pi 3 with 1 GB is told comes from the reference Pi's measurements
eval "$(sed -n '/^hardware_notice() {/,/^}/p' install.sh)"
said=""; wt_msg() { said="$1"; }; cfg_get() { echo ""; }; cfg_set() { :; }
printf 'MemTotal:         437000 kB\nMemAvailable:     300000 kB\n' > "$t/mem05"
ZB_PI_MODEL_FILE="$t/m3" ZB_MEMINFO="$t/mem1" hardware_notice
case "$said" in *"measured on"*"650 MB free"*) ;; *) echo "Pi 3, 1 GB: wrong notice: $said"; exit 1 ;; esac
case "$said" in *"no extra feeders"*|*"one or two extra feeders"*) echo "Pi 3, 1 GB: told to hold back feeders it was measured with"; exit 1 ;; esac
said=""; ZB_PI_MODEL_FILE="$t/mz" ZB_MEMINFO="$t/mem05" hardware_notice
case "$said" in *"older Raspberry Pi"*"no extra feeders"*) ;; *) echo "Zero 2 W, 512 MB: wrong notice: $said"; exit 1 ;; esac
said=""; ZB_PI_MODEL_FILE="$t/m4" ZB_MEMINFO="$t/mem2" hardware_notice
[ -z "$said" ] || { echo "Pi 4, 2 GB: no notice expected: $said"; exit 1; }
echo "hardware detection tests OK"
