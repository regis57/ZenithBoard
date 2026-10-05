#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ZenithBoard ACARS ingester.

acarsdec sends one JSON object per UDP datagram to 127.0.0.1:<port>.
This service filters the messages, stores them in SQLite (read by Grafana) and
deletes everything older than ACARS_RETENTION_DAYS (default 7) every hour,
so the Raspberry Pi's SD card never fills up.
"""
import json
import os
import socket
import sqlite3
import sys
import threading
import time

CONFIG_FILE = os.environ.get("ZENITHBOARD_CONFIG", "/etc/zenithboard/config.env")

DEFAULTS = {
    "ACARS_DB": "/var/lib/zenithboard/acars.db",
    "ACARS_UDP_PORT": "5555",
    "ACARS_RETENTION_DAYS": "7",
    "ACARS_IGNORE_EMPTY": "1",           # drop messages without any text (pure acknowledgements)
    "ACARS_IGNORE_LABELS": "_d,Q0,SQ",   # _d = ACK, Q0 = link test, SQ = squitter
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,          -- unix seconds (UTC)
  freq REAL, level REAL, mode TEXT, label TEXT, block_id TEXT,
  tail TEXT, flight TEXT, msgno TEXT, depa TEXT, dsta TEXT, text TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts);
"""


def load_config(path=CONFIG_FILE):
    cfg = dict(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    cfg[k.strip()] = v.strip().strip("\"'")
    except OSError:
        pass
    return cfg


def parse_message(raw, ignore_labels=(), ignore_empty=True):
    """Turn one acarsdec JSON datagram into a DB row (tuple), or None if filtered out."""
    try:
        m = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(m, dict):
        return None
    label = (m.get("label") or "").strip()
    text = (m.get("text") or "").strip()
    if label in ignore_labels:
        return None
    if ignore_empty and not text:
        return None
    ts = int(float(m.get("timestamp") or time.time()))
    return (ts, m.get("freq"), m.get("level"), str(m.get("mode") or ""), label, str(m.get("block_id") or ""),
            (m.get("tail") or "").strip(".").strip(), (m.get("flight") or "").strip(), m.get("msgno"),
            m.get("depa"), m.get("dsta"), text)


def purge(conn, retention_days, now=None):
    """Delete messages older than retention_days. Returns number of deleted rows."""
    cutoff = int((now if now is not None else time.time()) - retention_days * 86400)
    cur = conn.execute("DELETE FROM messages WHERE ts < ?", (cutoff,))
    conn.commit()
    return cur.rowcount


def open_db(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.executescript(SCHEMA)
    conn.commit()
    try:
        os.chmod(path, 0o640)   # group "zenithboard" (Grafana is a member) can read
    except OSError:
        pass
    return conn


def main():
    cfg = load_config()
    days = float(cfg["ACARS_RETENTION_DAYS"])
    labels = tuple(x.strip() for x in cfg["ACARS_IGNORE_LABELS"].split(",") if x.strip())
    ignore_empty = cfg["ACARS_IGNORE_EMPTY"] not in ("0", "false", "no")
    conn = open_db(cfg["ACARS_DB"])
    lock = threading.Lock()

    def janitor():
        while True:
            with lock:
                n = purge(conn, days)
                if n:
                    conn.execute("VACUUM")
                    print("purged %d messages older than %g days" % (n, days), flush=True)
            time.sleep(3600)

    threading.Thread(target=janitor, daemon=True).start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", int(cfg["ACARS_UDP_PORT"])))
    print("ACARS ingester: udp/127.0.0.1:%s -> %s (keep %g days)" % (cfg["ACARS_UDP_PORT"], cfg["ACARS_DB"], days), flush=True)
    while True:
        data, _ = sock.recvfrom(65535)
        for line in data.decode("utf-8", "replace").splitlines():
            row = parse_message(line, labels, ignore_empty)
            if row:
                with lock:
                    conn.execute("INSERT INTO messages (ts,freq,level,mode,label,block_id,tail,flight,msgno,depa,dsta,text)"
                                 " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
                    conn.commit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
