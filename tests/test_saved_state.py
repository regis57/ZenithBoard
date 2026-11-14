"""The state the two posting services keep on the card (flightinfo/saved_state.py, lot 0 after 1.0): read safely,
written only when it has changed, written before the service stops, and kept by one piece of code for both."""
import contextlib
import io
import json
import os
import re
import shutil
import signal
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "flightinfo"))
import saved_state  # noqa: E402
import social  # noqa: E402
import telegram  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(signal.signal, signal.SIGTERM, signal.getsignal(signal.SIGTERM))
        self.dir = os.path.join(self.tmp, "state")
        self.saved = saved_state.SavedState(self.dir, "social")
        self.file = os.path.join(self.dir, "state.json")

    def on_card(self):
        with open(self.file, encoding="utf-8") as fh:
            return json.load(fh)


class ReadTest(Base):
    def test_a_missing_a_cut_or_a_wrong_file_is_an_empty_state(self):
        self.assertEqual(self.saved.load(), {})
        os.makedirs(self.dir)
        for text in ("", '{"posted": {"4ca7b1"', "[1, 2]", '"text"', "\x00\x00"):
            with open(self.file, "w") as fh:
                fh.write(text)
            self.assertEqual(self.saved.load(), {}, text)

    def test_what_was_saved_is_read_back(self):
        st = {"last_post": 1800000000.5, "posted": {"4ca7b1": {"t": 1.0, "flight": "EZY12AB"}}, "name": "Trémery"}
        self.assertTrue(self.saved.save(st))
        self.assertEqual(saved_state.SavedState(self.dir, "social").load(), st)
        self.assertFalse(os.path.exists(self.file + ".tmp"), "the temporary file is not left behind")


class OnChangeTest(Base):
    def test_an_unchanged_state_is_not_written_again(self):
        st = {"a": 1}
        self.assertTrue(self.saved.save(st))
        os.utime(self.file, ns=(10**18, 10**18))                 # a time of ours, to see a write
        self.saved._stamp = self.saved._stamp_now()
        self.assertFalse(self.saved.save(st))
        self.assertFalse(self.saved.save(dict(st)))
        self.assertEqual(os.stat(self.file).st_mtime_ns, 10**18, "the card was not touched")
        st["a"] = 2
        self.assertTrue(self.saved.save(st))
        self.assertNotEqual(os.stat(self.file).st_mtime_ns, 10**18)
        self.assertEqual(self.on_card(), {"a": 2})

    def test_a_state_just_read_and_unchanged_is_not_written(self):
        self.saved.save({"a": 1})
        other = saved_state.SavedState(self.dir, "social")
        self.assertFalse(other.save(other.load()))

    def test_a_write_by_another_process_is_not_taken_for_ours(self):
        # `zenithboard social post` records its post while the service runs: the service's next save must write
        st = {"a": 1}
        self.saved.save(st)
        hand = saved_state.SavedState(self.dir, "social")
        hand.save({"a": 1, "last_post": 5})
        self.assertTrue(self.saved.save(st), "the file is no longer what this process wrote")
        self.assertEqual(self.on_card(), st)

    def test_a_file_removed_is_written_again(self):
        self.saved.save({"a": 1})
        os.unlink(self.file)
        self.assertTrue(self.saved.save({"a": 1}))
        self.assertTrue(os.path.exists(self.file))

    def test_a_card_that_refuses_is_said_and_does_not_stop_the_service(self):
        with open(os.path.join(self.tmp, "blocked"), "w") as fh:
            fh.write("a file where the folder should be")
        bad = saved_state.SavedState(os.path.join(self.tmp, "blocked", "state"), "telegram")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertFalse(bad.save({"a": 1}))
            self.assertFalse(bad.save({"a": object()}), "a state that cannot be written as JSON")
        self.assertEqual(err.getvalue().count("telegram: cannot save state:"), 2)
        self.assertTrue(self.saved.save({"a": 1}) and not self.saved.save({"a": 1}))


class StopTest(Base):
    def test_sigterm_writes_the_state_then_leaves(self):
        st = {"posted": {}}
        self.saved.save(st)
        self.saved.on_stop(lambda: st, lambda s: s.update(queue=3))
        st["posted"]["4ca7b1"] = {"t": 1.0}
        with self.assertRaises(SystemExit) as left:
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        self.assertEqual(left.exception.code, 0)
        self.assertEqual(self.on_card(), {"posted": {"4ca7b1": {"t": 1.0}}, "queue": 3})

    def test_the_bluesky_service_writes_its_post_down_when_stopped(self):
        # before lot 0 only the Telegram service did; a stop between a look and the next save could lose up to
        # fifteen seconds of what the service had counted
        class Halt(Exception):
            pass
        keep = social.STATE_DIR
        self.addCleanup(setattr, social, "STATE_DIR", keep)
        social.STATE_DIR = self.dir
        clock = [1800000000.0]

        def sleep(sec):
            raise Halt()
        seen = {}

        def poll(c, st, tr, ac, now):
            seen["state"] = st
            return [], None
        for name, fake in (("read_aircraft", lambda c: []), ("account", lambda: {}), ("one_poll", poll),
                           ("cfg", lambda: {"SOCIAL_RADIUS_KM": "10"}), ("run_summaries", lambda c, sec, st, now, lf: lf)):
            self.addCleanup(setattr, social, name, getattr(social, name))
            setattr(social, name, fake)
        self.addCleanup(setattr, time, "time", time.time); time.time = lambda: clock[0]
        self.addCleanup(setattr, time, "sleep", time.sleep); time.sleep = sleep
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(Halt):
                social.cmd_run()
        seen["state"]["last_post"] = clock[0]                    # the service has just posted, and is stopped
        with self.assertRaises(SystemExit):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        self.assertEqual(self.on_card()["last_post"], clock[0])


class OnePlaceTest(unittest.TestCase):
    def test_both_services_keep_their_state_through_the_helper(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for mod, name in ((social, "social"), (telegram, "telegram")):
            keep = mod.STATE_DIR
            self.addCleanup(setattr, mod, "STATE_DIR", keep)
            mod.STATE_DIR = os.path.join(tmp, name)
            self.assertIsInstance(mod.saved(), saved_state.SavedState)
            self.assertEqual((mod.saved().directory, mod.saved().name), (mod.STATE_DIR, name))
            self.assertTrue(mod.save_state({"a": 1}))
            self.assertFalse(mod.save_state({"a": 1}), "%s: an unchanged state is not written again" % name)
            self.assertEqual(mod.load_state(), {"a": 1})

    def test_no_service_writes_state_json_by_itself(self):
        for name in ("social.py", "telegram.py"):
            with open(os.path.join(HERE, "..", "flightinfo", name), encoding="utf-8") as fh:
                src = fh.read()
            self.assertNotIn("state.json.tmp", src, name)
            self.assertFalse(re.search(r"signal\.signal\(signal\.SIGTERM", src), "%s: the stop goes through the helper" % name)


if __name__ == "__main__":
    unittest.main()
