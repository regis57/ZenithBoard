#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""`zenithboard memory` (0.34.0): what each service of the receiver uses, read from /proc, nothing changed.

Asked for by the owner once the Pi 3B fed four networks (ADSB Exchange, FlightAware, Flightradar24, Plane Finder):
memory, threads and open files, service by service. systemd cannot say it on a Pi: Raspberry Pi OS boots with the
kernel's memory controller off (cgroup_disable=memory), so `systemctl status` shows no memory line (seen on the real
Pi, 0.19.4). The cgroups still list each service's processes, so this adds up the processes' own figures:

  memory   PSS (proportional set size): a shared library is split between the processes that use it, so the
           services add up to what is really in use. Readable for every process by root only; for another user's
           process without root, RSS, which counts shared libraries in each (said in the output).
  peak     the largest a service's processes have been since they started (VmHWM, added up): a process that has
           ended, Node drawing a post say, is not in it.
  threads  from /proc/PID/status.
  files    open file descriptors, root only.
"""
import os
import sys

PROC = os.environ.get("ZB_PROC", "/proc")
CGROUP = os.environ.get("ZB_CGROUP", "/sys/fs/cgroup")
# what the services are, in words; anything else is shown by its unit name
NAMES = {
    "readsb": "decoder", "dump1090-fa": "decoder", "dump978-fa": "978 MHz decoder", "skyaware978": "978 MHz map data",
    "tar1090": "receiver map (history)", "lighttpd": "web server (maps)", "adsbexchange-feed": "ADSB Exchange feed",
    "adsbexchange-mlat": "ADSB Exchange MLAT", "adsbexchange-stats": "ADSB Exchange stats", "piaware": "FlightAware",
    "fr24feed": "Flightradar24", "pfclient": "Plane Finder", "zenithboard-flightinfo": "the wall",
    "zenithboard-social": "Bluesky posts", "collectd": "graphs1090 (collect)", "graphs1090": "graphs1090 (draw)",
    "NetworkManager": "network", "systemd-journald": "system logs", "sshd": "SSH", "ssh": "SSH", "cron": "cron",
    "avahi-daemon": "name on the network (mDNS)", "dbus": "system bus", "wpa_supplicant": "Wi-Fi", "rsyslog": "system logs (text)",
}
SMALL_KB = 1024                   # services under 1 MB are counted together


def status_of(pid):
    out = {}
    try:
        with open(os.path.join(PROC, str(pid), "status")) as fh:
            for line in fh:
                k, _, v = line.partition(":")
                out[k] = v.strip()
    except OSError:
        return None
    return out


def kb(v):
    try:
        return int(str(v).split()[0])
    except (ValueError, IndexError):
        return 0


def pss_kb(pid):
    """PSS from smaps_rollup, or None when it cannot be read (another user's process, without root)."""
    try:
        with open(os.path.join(PROC, str(pid), "smaps_rollup")) as fh:
            for line in fh:
                if line.startswith("Pss:"):
                    return kb(line.split(":", 1)[1])
    except OSError:
        return None
    return None


def open_files(pid):
    try:
        return len(os.listdir(os.path.join(PROC, str(pid), "fd")))
    except OSError:
        return None


def process(pid):
    st = status_of(pid)
    if not st or "VmRSS" not in st:              # a kernel thread, or gone meanwhile
        return None
    p = pss_kb(pid)
    return {"pid": pid, "name": st.get("Name", "?"), "rss": kb(st.get("VmRSS")), "pss": p,
            "peak": kb(st.get("VmHWM")), "threads": kb(st.get("Threads", "1")), "files": open_files(pid)}


def service_dirs():
    """{unit name: [pids]} for the services running, from the cgroup tree (v2, or v1's systemd hierarchy)."""
    out = {}
    for base in (os.path.join(CGROUP, "system.slice"), os.path.join(CGROUP, "systemd", "system.slice")):
        if not os.path.isdir(base):
            continue
        for unit in sorted(os.listdir(base)):
            if not unit.endswith(".service"):
                continue
            pids = []
            for root, _, files in os.walk(os.path.join(base, unit)):
                if "cgroup.procs" in files:
                    try:
                        with open(os.path.join(root, "cgroup.procs")) as fh:
                            pids += [int(x) for x in fh.read().split() if x.strip().isdigit()]
                    except OSError:
                        pass
            if pids:
                out[unit[:-len(".service")]] = sorted(set(pids))
        if out:
            break
    return out


def meminfo():
    m = {}
    try:
        with open(os.path.join(PROC, "meminfo")) as fh:
            for line in fh:
                k, _, v = line.partition(":")
                m[k] = kb(v)
    except OSError:
        pass
    return m


def mb(k):
    if not k:
        return "0 MB"
    return "%d MB" % round(k / 1024.0) if k >= 1024 else "%.1f MB" % (k / 1024.0)


def report(out=sys.stdout):
    w = out.write
    m = meminfo()
    total, avail = m.get("MemTotal", 0), m.get("MemAvailable", 0)
    w("Memory:   %s in all, %s in use, %s available" % (mb(total), mb(total - avail), mb(avail)))
    if m.get("SwapTotal"):
        w(" (swap: %s used of %s)" % (mb(m["SwapTotal"] - m.get("SwapFree", 0)), mb(m["SwapTotal"])))
    w("\n")
    try:
        with open(os.path.join(PROC, "loadavg")) as fh:
            la = fh.read().split()
        threads = la[3].split("/")[1]
        w("Threads:  %s in all. Load: %s %s %s (over 1, 5 and 15 minutes; %d cores)\n" % (
            threads, la[0], la[1], la[2], os.cpu_count() or 1))
    except (OSError, IndexError):
        pass
    services = service_dirs()
    if not services:
        w("\nNo service could be read (no cgroup tree at %s): the processes alone.\n" % CGROUP)
        largest(w, set())
        return 0
    rows, rss_used, in_services = [], False, set()
    for unit, pids in services.items():
        ps = [p for p in (process(x) for x in pids) if p]
        if not ps:
            continue
        in_services |= {p["pid"] for p in ps}
        mem = 0
        for p in ps:
            if p["pss"] is None:
                rss_used = True
            mem += p["pss"] if p["pss"] is not None else p["rss"]
        files = [p["files"] for p in ps]
        rows.append({"unit": unit, "what": NAMES.get(unit, ""), "mem": mem, "peak": sum(p["peak"] for p in ps),
                     "threads": sum(p["threads"] for p in ps), "procs": len(ps),
                     "files": None if any(f is None for f in files) else sum(files)})
    rows.sort(key=lambda r: -r["mem"])
    big = [r for r in rows if r["mem"] >= SMALL_KB]
    small = [r for r in rows if r["mem"] < SMALL_KB]
    w("\nService by service (%s):\n" % ("memory as RSS for some: run with sudo for PSS" if rss_used
                                         else "memory as PSS: shared libraries split between their users, so it adds up"))
    w("  %-24s %-24s %8s %8s %7s %6s %5s\n" % ("SERVICE", "WHAT", "MEMORY", "PEAK", "THREADS", "FILES", "PROCS"))
    for r in big:
        w("  %-24s %-24s %8s %8s %7d %6s %5d\n" % (r["unit"][:24], r["what"][:24], mb(r["mem"]), mb(r["peak"]),
                                                  r["threads"], "-" if r["files"] is None else r["files"], r["procs"]))
    if small:
        w("  %-24s %-24s %8s %8s %7d\n" % ("%d more service%s" % (len(small), "" if len(small) == 1 else "s"), "under 1 MB each", mb(sum(r["mem"] for r in small)),
                                         "", sum(r["threads"] for r in small)))
    total_s = sum(r["mem"] for r in rows)
    w("  %-49s %8s %8s %7d\n" % ("All services", mb(total_s), "", sum(r["threads"] for r in rows)))
    others = sum(p["pss"] if p["pss"] is not None else p["rss"] for p in all_processes() if p["pid"] not in in_services)
    if others:
        w("  %-49s %8s\n" % ("Outside the services (logins, this command)", mb(others)))
    if any(r["files"] is None for r in rows):
        w("Open files: run with sudo to count them.\n")
    w("Peak: the largest each service's running processes have been since they started; one that has ended is not in it.\n")
    largest(w, in_services)
    return 0


def all_processes():
    out = []
    try:
        names = os.listdir(PROC)
    except OSError:
        return out
    for d in names:
        if d.isdigit():
            p = process(int(d))
            if p:
                out.append(p)
    return out


def largest(w, _in_services, n=6):
    """The largest processes, whatever runs them: the same figures, one process at a time."""
    ps = sorted(all_processes(), key=lambda p: -(p["pss"] if p["pss"] is not None else p["rss"]))[:n]
    if not ps:
        return
    w("\nLargest processes:\n")
    w("  %7s %-24s %8s %8s %7s %6s\n" % ("PID", "NAME", "MEMORY", "PEAK", "THREADS", "FILES"))
    for p in ps:
        w("  %7d %-24s %8s %8s %7d %6s\n" % (p["pid"], p["name"][:24], mb(p["pss"] if p["pss"] is not None else p["rss"]),
                                           mb(p["peak"]), p["threads"], "-" if p["files"] is None else p["files"]))


if __name__ == "__main__":
    sys.exit(report())
