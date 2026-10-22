#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The web console's root helper (0.39.0), started by zenithboard-console.path when a job appears in the spool.

The spool is written by the wall's server (user zenithboard); everything in it is treated as untrusted. A job is a
small JSON file naming one action and its values. It is opened without following links, must be a plain file of
that user under 4 KB, and is checked against flightinfo/console_actions.py (root's own copy in /opt) before the one
`zenithboard` command it describes is run, as an argument list, never through a shell, its input closed. What the
command prints goes to out/ID.log and the end to out/ID.json, both root's, readable by the wall; one line per job
goes to out/journal.log. After each job the overview's facts are read again (out/state.json).
"""
import json
import os
import pwd
import re
import stat
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ZB_HOME = os.environ.get("ZENITHBOARD_HOME", os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ZB_HOME, "flightinfo"))
import console_actions as actions  # noqa: E402

CONSOLE_DIR = os.environ.get("ZB_CONSOLE_DIR", "/var/lib/zenithboard/console")
SPOOL = os.path.join(CONSOLE_DIR, "state", "spool")
OUT = os.path.join(CONSOLE_DIR, "out")
ZB_BIN = os.environ.get("ZENITHBOARD_BIN", os.path.join(ZB_HOME, "bin", "zenithboard"))
WALL_USER = os.environ.get("ZB_USER", "zenithboard")
MAX_JOB_BYTES = 4096
MAX_LOG_BYTES = 256 * 1024          # a full update prints a lot; the end is what matters
KEEP_JOBS = 60
JOURNAL_LINES = 400
TIMEOUT_S = {"long": 3600, "": 300}


def wall_uid():
    try:
        return pwd.getpwnam(WALL_USER).pw_uid
    except KeyError:
        return None


def _create(path):
    """A new file for the wall to read: owner read-write, its group read, others nothing (the umask makes the mode;
    out/ is root's, so nothing in it can be a planted link, and it is never followed anyway)."""
    old = os.umask(0o137)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW)
    finally:
        os.umask(old)
    _group(path)
    return fd


def write_out(name, data):
    """A file in out/, replaced in one step."""
    path = os.path.join(OUT, name)
    tmp = path + ".tmp"
    with os.fdopen(_create(tmp), "wb") as fh:
        fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    os.replace(tmp, path)


def _group(path):
    try:
        gid = pwd.getpwnam(WALL_USER).pw_gid
        os.chown(path, 0, gid)
    except (KeyError, PermissionError, OSError):
        pass                                    # tests run without root: the file stays the tester's


def read_job(path, uid):
    """-> the job as a dict, or None when it is not something the wall could have written."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError:
        return None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_JOB_BYTES:
            return None
        if uid is not None and st.st_uid not in (uid, 0):
            return None
        raw = os.read(fd, MAX_JOB_BYTES + 1)
    finally:
        os.close(fd)
    try:
        job = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    return job if isinstance(job, dict) else None


def state_snapshot():
    """The overview's facts, from `zenithboard console state` (KEY=value lines)."""
    try:
        out = subprocess.run([ZB_BIN, "console", "state"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=60, env=_env()).stdout.decode("utf-8", "replace")
    except (OSError, subprocess.TimeoutExpired):
        return
    facts = {}
    for line in out.splitlines():
        k, sep, v = line.partition("=")
        if sep and re.match(r"^[a-z0-9_]{1,40}$", k):
            facts[k] = v[:200]
    write_out("state.json", json.dumps({"at": int(time.time()), "facts": facts}))


def _env():
    return {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "TERM": "dumb", "LANG": "C.UTF-8",
            "HOME": "/root", "ZB_FROM_CONSOLE": "1"}


def journal(line):
    path = os.path.join(OUT, "journal.log")
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()[-(JOURNAL_LINES - 1):]
    except OSError:
        lines = []
    lines.append(line)
    write_out("journal.log", "\n".join(lines) + "\n")


def run_job(job_id, job):
    name, params = job.get("action"), job.get("params") or {}
    who = re.sub(r"[^\w .:@()-]", "", str(job.get("by", "")))[:60]
    started = time.time()
    meta = {"id": job_id, "action": name, "params": params, "by": who, "queued": job.get("at"), "started": int(started)}
    try:
        argv = actions.build(name, params)
    except actions.Refused as e:
        meta.update(state="refused", rc=None, ended=int(time.time()), error=str(e))
        write_out(job_id + ".json", json.dumps(meta))
        journal("%s  %-14s refused (%s)  %s" % (time.strftime("%Y-%m-%d %H:%M"), str(name)[:20], e, who))
        return
    meta["state"] = "running"
    write_out(job_id + ".json", json.dumps(meta))
    rc = 0
    if argv is not None:
        flags = actions.flags(name)
        timeout = TIMEOUT_S["long"] if "long" in flags else TIMEOUT_S[""]
        log_path = os.path.join(OUT, job_id + ".log")
        with os.fdopen(_create(log_path), "wb", buffering=0) as log:
            log.write(("$ zenithboard %s\n" % " ".join(" ".join(a.split()) for a in argv)).encode("utf-8"))
            try:
                p = subprocess.Popen([ZB_BIN] + argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, env=_env(), cwd="/")
                killer = threading.Timer(timeout, p.kill)      # a command that hangs without a word is stopped too
                killer.start()
                written = 0
                for chunk in iter(lambda: p.stdout.readline(), b""):
                    if written < MAX_LOG_BYTES:
                        log.write(chunk)
                        written += len(chunk)
                rc = p.wait()
                killer.cancel()
                if time.time() - started >= timeout:
                    log.write(b"\n(stopped: it ran longer than %d minutes)\n" % (timeout // 60))
            except OSError as e:
                log.write(("could not run it: %s\n" % e).encode("utf-8"))
                rc = 127
    meta.update(state="done", rc=rc, ended=int(time.time()))
    write_out(job_id + ".json", json.dumps(meta))
    if "read" in actions.flags(name):
        return                                    # looking changes nothing: the journal keeps the changes
    shown = " ".join("%s=%s" % (k, v) for k, v in sorted(params.items())) if isinstance(params, dict) else ""
    shown = " ".join(shown.split())               # 0.50.0: a written post's lines on the journal's one line
    journal("%s  %-14s %-18s %s  %s" % (time.strftime("%Y-%m-%d %H:%M"), name, shown[:18], "ok" if rc == 0 else "rc=%s" % rc, who))


def prune():
    jobs = sorted((os.path.getmtime(os.path.join(OUT, n)), n[:-5]) for n in os.listdir(OUT)
                  if n.endswith(".json") and actions.JOB_ID_RE.match(n[:-5]))
    for _, jid in jobs[:-KEEP_JOBS]:
        for ext in (".json", ".log"):
            try:
                os.unlink(os.path.join(OUT, jid + ext))
            except OSError:
                pass                          # already gone: nothing to prune


def _mtime(path):
    try:
        return os.lstat(path).st_mtime
    except OSError:
        return 0


def main():
    if not os.path.isdir(SPOOL) or not os.path.isdir(OUT):
        return 0
    uid = wall_uid()
    ran = False
    for _round in range(50):                      # jobs dropped while one runs are taken in the same start
        names = sorted((n for n in os.listdir(SPOOL) if n.endswith(".job")), key=lambda n: _mtime(os.path.join(SPOOL, n)))
        if not names:
            break
        for n in names:
            path = os.path.join(SPOOL, n)
            job = read_job(path, uid)
            try:
                os.unlink(path)                   # taken: never run twice
            except OSError:
                pass                          # taken by another start: it will not run twice
            job_id = n[:-4]
            if job is None or not actions.JOB_ID_RE.match(job_id):
                continue
            run_job(job_id, job)
            ran = True
    if ran or not os.path.exists(os.path.join(OUT, "state.json")) or "--state" in sys.argv:
        state_snapshot()
    prune()
    return 0


if __name__ == "__main__":
    sys.exit(main())
