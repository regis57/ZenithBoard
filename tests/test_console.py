# SPDX-License-Identifier: GPL-3.0-or-later
"""The web console (0.39.0): the fixed list of actions, the password, who may come in, sessions, pairing a phone,
the requests themselves, and the root helper run against a stand-in `zenithboard`, in temporary folders."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import console  # noqa: E402
import console_actions as actions  # noqa: E402

RUNNER = os.path.join(HERE, "..", "tools", "console_run.py")


class ActionsTest(unittest.TestCase):
    def test_build_gives_the_argument_list(self):
        self.assertEqual(actions.build("units", {"value": "imperial"}), ["units", "imperial"])
        self.assertEqual(actions.build("localdb", {"value": "on"}), ["data", "localdb", "on"])
        self.assertEqual(actions.build("summary-at", {"period": "weekly", "when": "sun 19:00"}),
                         ["social", "summary", "weekly", "at", "sun", "19:00"])
        self.assertEqual(actions.build("location", {"lat": "49.1193", "lon": "6.1757"}), ["location", "49.1193", "6.1757"])
        self.assertEqual(actions.build("location", {"lat": "49.1", "lon": "6.2", "alt": "180"}), ["location", "49.1", "6.2", "180"])
        self.assertIsNone(actions.build("refresh", {}))

    def test_anything_else_is_refused(self):
        bad = [("uninstall", {}), ("config-set", {"value": "x"}), ("units", {"value": "metric; rm -rf /"}),
               ("units", {"value": "metric", "extra": "1"}), ("radius", {"value": "11"}), ("cycle", {"value": "61"}),
               ("cycle", {"value": "1e3"}), ("location", {"lat": "91", "lon": "0"}), ("location", {"lat": "4$(id)", "lon": "0"}),
               ("summary-at", {"period": "weekly", "when": "sun 25:00"}), ("summary-parts", {"period": "daily", "value": "1,5"}),
               ("social-sentence", {"value": "factual,`id`"}), ("units", {}), (None, {}), ("__class__", {})]
        for name, params in bad:
            with self.assertRaises(actions.Refused, msg=(name, params)):
                actions.build(name, params)

    def test_nothing_secret_or_cutting_the_network_is_listed(self):
        argvs = [" ".join(s[2] or []) for s in actions.ACTIONS.values()]
        for word in ("setup", "remove", "uninstall", "connect", "forget", "static", "dhcp", "import", "clear", "clean",
                     "config-set", "password", "post", "ddns set", "wifi on", "wifi off"):
            self.assertFalse([a for a in argvs if word in a.split() or a.startswith(word)], word)

    def test_catalog_never_shows_the_commands(self):
        cat = actions.catalog()
        self.assertEqual(cat["radius"]["params"][0]["choices"], ["1", "2", "5", "10", "15", "30", "50"])
        self.assertNotIn("argv", json.dumps(cat))
        self.assertTrue(all(v["section"] in dict(actions.SECTIONS) for v in cat.values()))


class PasswordAndPlacesTest(unittest.TestCase):
    def test_scrypt_hash(self):
        h = console.hash_password("correct horse", n=1024)
        self.assertTrue(h.startswith("scrypt$1024$8$1$"))
        self.assertTrue(console.check_password("correct horse", h))
        self.assertFalse(console.check_password("correct horsE", h))
        self.assertFalse(console.check_password("x", "plain"))
        self.assertFalse(console.check_password("x", "scrypt$99999999$8$1$AA==$AA=="), "absurd cost refused, not computed")

    def test_home_networks_only(self):
        for ip in ("192.168.1.20", "10.8.0.3", "172.20.1.1", "127.0.0.1", "::1", "fe80::1%eth0", "::ffff:192.168.1.5"):
            self.assertTrue(console.client_ok(ip), ip)
        for ip in ("8.8.8.8", "2a01:cb00::1", "::ffff:1.2.3.4", "garbage"):
            self.assertFalse(console.client_ok(ip), ip)

    def test_host_header_against_dns_rebinding(self):
        for hst in ("192.168.1.196:8080", "[fe80::1]:8080", "localhost:8080", "zenithboard.local", "pi.home.arpa:8080"):
            self.assertTrue(console.host_ok(hst), hst)
        for hst in ("evil.example.com", "evil.example.com:8080", "", "192.168.1.196.evil.com"):
            self.assertFalse(console.host_ok(hst), hst)
        self.assertTrue(console.host_ok("zb.duckdns.org:8080", "zb.duckdns.org"), "a name the owner listed in CONSOLE_HOSTS")


class LimiterTest(unittest.TestCase):
    def test_five_tries_then_a_doubling_wait(self):
        L, t = console.Limiter(), 1000.0
        for _ in range(4):
            L.miss("a", t)
        self.assertEqual(L.wait("a", t), 0)
        L.miss("a", t)
        self.assertGreater(L.wait("a", t), 25)
        L.miss("a", t + 31)
        self.assertGreater(L.wait("a", t + 31), 55)
        self.assertEqual(L.wait("b", t), 0, "another address is not held back")
        L.ok("a")
        self.assertEqual(L.wait("a", t + 31), 0)

    def test_many_misses_from_everywhere_hold_everyone(self):
        L, t = console.Limiter(), 5000.0
        for i in range(console.GLOBAL_FAILS):
            L.miss("10.0.0.%d" % i, t)
        self.assertGreater(L.wait("192.168.1.9", t + 1), 0)


class TempDirs(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        d = os.path.join(self.root, "console")
        os.makedirs(os.path.join(d, "state", "spool"))
        os.makedirs(os.path.join(d, "out"))
        self.env = os.path.join(self.root, "console.env")
        with open(self.env, "w") as fh:
            fh.write('CONSOLE_PASSWORD_HASH="%s"\nCONSOLE_EPOCH="0"\n' % console.hash_password("a long password", n=1024))
        saved = {k: getattr(console, k) for k in ("ENV_FILE", "CONSOLE_DIR", "STATE_DIR", "SPOOL_DIR", "OUT_DIR")}
        self.addCleanup(lambda: [setattr(console, k, v) for k, v in saved.items()])
        console.ENV_FILE, console.CONSOLE_DIR = self.env, d
        console.STATE_DIR, console.SPOOL_DIR, console.OUT_DIR = os.path.join(d, "state"), os.path.join(d, "state", "spool"), os.path.join(d, "out")
        console._env_cache.update(mtime=None, data={})
        self.dir = d


class SessionsTest(TempDirs):
    def test_kept_as_a_hash_and_ended_by_a_sign_out_for_everyone(self):
        s = console.Sessions()
        tok, rec = s.create("password", "iPhone")
        self.assertEqual(console.Sessions().get(tok)["id"], rec["id"], "a restart of the wall keeps it")
        with open(s.path) as fh:
            self.assertNotIn(tok, fh.read())
        self.assertEqual(stat.S_IMODE(os.stat(s.path).st_mode), 0o600)
        with open(self.env, "a") as fh:
            fh.write('CONSOLE_EPOCH="%d"\n' % (time.time() + 5))
        os.utime(self.env, (time.time() + 10, time.time() + 10))
        self.assertIsNone(console.Sessions().get(tok), "console password / signout ends it")

    def test_lifetimes(self):
        s = console.Sessions()
        tok, rec = s.create("password", "Mac")
        rec["created"] -= console.PASSWORD_LIFE_S + 1
        self.assertIsNone(s.get(tok))
        tok, rec = s.create("paired", "iPhone")
        rec["created"] -= console.PASSWORD_LIFE_S + 1                 # a paired phone outlives a password session
        self.assertIsNotNone(s.get(tok))
        rec["seen"] -= console.PAIRED_IDLE_S + 1
        self.assertIsNone(s.get(tok))

    def test_revoke_the_others(self):
        s = console.Sessions()
        a, ra = s.create("password", "Mac")
        b, _ = s.create("paired", "iPhone")
        self.assertEqual(s.revoke(keep=ra["id"]), 1)
        self.assertIsNotNone(s.get(a))
        self.assertIsNone(s.get(b))


class PairsTest(TempDirs):
    def test_once_and_within_five_minutes(self):
        p = console.Pairs()
        tok, pid = p.make("Mac 1")
        self.assertTrue(p.redeem(tok, "iPhone"))
        self.assertFalse(p.redeem(tok, "iPhone"), "works once")
        self.assertEqual(p.status(pid)["used_by"], "iPhone")
        tok2, _ = p.make("Mac 1")
        p.links[console._sha(tok2)]["until"] = time.time() - 1
        self.assertFalse(p.redeem(tok2, "iPhone"))
        self.assertFalse(p.redeem("x" * 30, "iPhone"))

    def test_the_terminals_code(self):
        tok = "terminal-made-token-1234567890"
        with open(os.path.join(self.dir, "out", "pair"), "w") as fh:
            fh.write("%s %d\n" % (console._sha(tok), time.time() + 300))
        p = console.Pairs()
        self.assertTrue(p.redeem(tok, "iPhone"))
        self.assertFalse(console.Pairs().redeem(tok, "iPhone"), "noted as used, even after a restart")


class HandleTest(TempDirs):
    CFG = {"CONSOLE": "1", "_VERSION": "0.39.0"}

    def req(self, method, path, body=None, cookie=None, headers=None, client="192.168.1.20", cfg=None, query=None):
        hd = {"Host": "192.168.1.196:8080", "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)"}
        if body is not None:
            hd["Content-Type"] = "application/json"
        if cookie:
            hd["Cookie"] = "other=1; zbc=" + cookie
        hd.update(headers or {})
        return self.c.handle(console.Request(method, path, query, hd, client, json.dumps(body).encode() if body is not None else b"",
                                             cfg or self.CFG))

    def setUp(self):
        super().setUp()
        self.c = console.Console()

    def login(self):
        r = self.req("POST", "/console/api/login", {"password": "a long password"})
        self.assertEqual(r.code, 200, r.body)
        cookie = r.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Path=/console", cookie)
        tok = cookie.split(";")[0].split("=", 1)[1]
        csrf = self.req("GET", "/console/api/session", cookie=tok).body["csrf"]
        return tok, csrf

    def test_other_paths_are_not_its_business(self):
        self.assertIsNone(self.req("GET", "/stats"))
        self.assertIsNone(self.req("GET", "/consoles"))

    def test_strangers_and_other_names_get_nothing(self):
        self.assertEqual(self.req("GET", "/console", client="8.8.8.8").code, 403)
        self.assertEqual(self.req("GET", "/console", headers={"Host": "evil.example.com"}).code, 403)
        r = self.req("GET", "/console")
        self.assertEqual((r.code, r.file), (200, "console.html"))
        self.assertIn("frame-ancestors 'none'", r.headers["Content-Security-Policy"])

    def test_off_says_so_and_does_nothing(self):
        off = {"CONSOLE": "0"}
        self.assertFalse(self.req("GET", "/console/api/session", cfg=off).body["enabled"])
        self.assertEqual(self.req("POST", "/console/api/login", {"password": "a long password"}, cfg=off).code, 404)

    def test_sign_in_and_run_one_action(self):
        self.assertEqual(self.req("POST", "/console/api/login", {"password": "wrong"}).code, 401)
        tok, csrf = self.login()
        self.assertEqual(self.req("GET", "/console/api/state").code, 401, "no cookie, nothing")
        st = self.req("GET", "/console/api/state", cookie=tok).body
        self.assertEqual(st["cfg"]["UNITS"], "metric")
        self.assertIn("radius", st["catalog"])
        r = self.req("POST", "/console/api/run", {"action": "radius", "params": {"value": "15"}}, cookie=tok, headers={"X-ZB-CSRF": csrf})
        self.assertEqual(r.code, 200, r.body)
        with open(os.path.join(self.dir, "state", "spool", r.body["job"] + ".job")) as fh:
            job = json.load(fh)
        self.assertEqual((job["action"], job["params"], job["by"][:6]), ("radius", {"value": "15"}, "iPhone"))
        self.assertEqual(self.req("GET", "/console/api/job", cookie=tok, query={"id": [r.body["job"]]}).body["state"], "queued")

    def test_a_change_needs_the_pages_own_token_and_origin(self):
        tok, csrf = self.login()
        run = {"action": "radius", "params": {"value": "15"}}
        self.assertEqual(self.req("POST", "/console/api/run", run, cookie=tok).code, 403)
        self.assertEqual(self.req("POST", "/console/api/run", run, cookie=tok, headers={"X-ZB-CSRF": "x" + csrf}).code, 403)
        self.assertEqual(self.req("POST", "/console/api/run", run, cookie=tok, headers={"X-ZB-CSRF": csrf, "Origin": "http://evil.example"}).code, 403)
        self.assertEqual(self.req("POST", "/console/api/run", run, cookie=tok, headers={"X-ZB-CSRF": csrf, "Sec-Fetch-Site": "cross-site"}).code, 403)
        r = self.c.handle(console.Request("POST", "/console/api/run", None, {"Host": "192.168.1.196:8080", "Cookie": "zbc=" + tok,
                                                                              "X-ZB-CSRF": csrf, "Content-Type": "text/plain"},
                                          "192.168.1.20", json.dumps(run).encode(), self.CFG))
        self.assertEqual(r.code, 400, "a form post (text/plain) is not JSON")
        self.assertEqual(self.req("POST", "/console/api/run", {"action": "uninstall"}, cookie=tok, headers={"X-ZB-CSRF": csrf}).code, 400)
        self.assertEqual(os.listdir(os.path.join(self.dir, "state", "spool")), [])

    def test_too_many_tries(self):
        for _ in range(console.FAIL_FREE):
            self.req("POST", "/console/api/login", {"password": "nope"})
        r = self.req("POST", "/console/api/login", {"password": "a long password"})
        self.assertEqual(r.code, 429, "even the right one waits")

    def test_pair_a_phone(self):
        tok, csrf = self.login()
        made = self.req("POST", "/console/api/pair", {}, cookie=tok, headers={"X-ZB-CSRF": csrf}).body
        r = self.req("POST", "/console/api/pair/redeem", {"token": made["token"]})
        self.assertEqual(r.code, 200)
        self.assertIn("Max-Age=%d" % console.PAIRED_LIFE_S, r.headers["Set-Cookie"])
        self.assertEqual(self.req("POST", "/console/api/pair/redeem", {"token": made["token"]}).code, 401)
        self.assertEqual(self.req("GET", "/console/api/pair", cookie=tok, query={"id": [made["id"]]}).body["used_by"], "iPhone")
        listing = self.req("GET", "/console/api/sessions", cookie=tok).body["sessions"]
        self.assertEqual(sorted(s["kind"] for s in listing), ["paired", "password"])
        self.assertNotIn("csrf", json.dumps(listing))

    def test_sign_out(self):
        tok, csrf = self.login()
        r = self.req("POST", "/console/api/logout", {}, cookie=tok, headers={"X-ZB-CSRF": csrf})
        self.assertIn("Max-Age=0", r.headers["Set-Cookie"])
        self.assertEqual(self.req("GET", "/console/api/state", cookie=tok).code, 401)


class RunnerTest(TempDirs):
    """tools/console_run.py, the root helper, against a stand-in for bin/zenithboard."""

    def setUp(self):
        super().setUp()
        self.stub = os.path.join(self.root, "zenithboard")
        with open(self.stub, "w") as fh:
            fh.write("#!/bin/sh\nif [ \"$1 $2\" = \"console state\" ]; then echo version=0.39.0; echo temp_c=51; echo 'bad key=x'; exit 0; fi\n"
                     "echo \"ran: $*\"; echo \"input: $(cat 2>&1 | head -c 20)\"; [ \"$1\" = radius ] || exit 3\n")
        os.chmod(self.stub, stat.S_IRWXU)        # its owner only: the test runs it as that user

    def run_helper(self):
        env = dict(os.environ, ZB_CONSOLE_DIR=self.dir, ZENITHBOARD_BIN=self.stub, ZB_USER=__import__("pwd").getpwuid(os.getuid()).pw_name)
        subprocess.run([sys.executable, RUNNER], env=env, check=True, timeout=60)

    def job(self, name, params):
        return console.submit(name, params, "Mac 1")

    def test_a_job_runs_once_and_says_what_it_printed(self):
        j = self.job("radius", {"value": "15"})
        self.run_helper()
        st = console.job_status(j)
        self.assertEqual((st["state"], st["rc"]), ("done", 0))
        self.assertIn("ran: radius 15", st["log"])
        self.assertIn("input: \n", st["log"], "its input is closed: nothing can be asked")
        self.assertEqual(os.listdir(console.SPOOL_DIR), [])
        with open(os.path.join(self.dir, "out", "journal.log")) as fh:
            self.assertIn("radius", fh.read())
        with open(os.path.join(self.dir, "out", "state.json")) as fh:
            self.assertEqual(json.load(fh)["facts"], {"version": "0.39.0", "temp_c": "51"})
        self.assertEqual(console.job_status(j, st["next"])["log"], "", "read from where the page left off")

    def test_a_failing_command_and_a_read_are_told_apart(self):
        j = self.job("health", {})
        self.run_helper()
        self.assertEqual(console.job_status(j)["rc"], 3)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "out", "journal.log")), "looking changes nothing: not in the journal")

    def test_what_the_wall_could_have_forged_is_refused_or_ignored(self):
        spool = console.SPOOL_DIR
        with open(os.path.join(spool, "0123456789abcdef.job"), "w") as fh:
            json.dump({"action": "units", "params": {"value": "metric;reboot"}}, fh)
        with open(os.path.join(spool, "fedcba9876543210.job"), "w") as fh:
            fh.write(json.dumps({"action": "radius", "params": {"value": "10"}, "pad": "x" * 5000}))
        secret = os.path.join(self.root, "secret")
        with open(secret, "w") as fh:
            fh.write(json.dumps({"action": "radius", "params": {"value": "10"}}))
        os.symlink(secret, os.path.join(spool, "aaaaaaaaaaaaaaaa.job"))
        with open(os.path.join(spool, "NOT-AN-ID.job"), "w") as fh:
            json.dump({"action": "radius", "params": {"value": "10"}}, fh)
        self.run_helper()
        self.assertEqual(console.job_status("0123456789abcdef")["state"], "refused")
        for jid in ("fedcba9876543210", "aaaaaaaaaaaaaaaa"):
            self.assertIsNone(console.job_status(jid), "too big / a link: never run")
        self.assertEqual(os.listdir(spool), [])
        self.assertFalse([n for n in os.listdir(os.path.join(self.dir, "out")) if n.endswith(".log") and n != "journal.log"], "nothing ran")


if __name__ == "__main__":
    unittest.main()
