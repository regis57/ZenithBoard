"""One way to keep a service's state on the card, for the Bluesky and the Telegram services (lot 0 after 1.0).

Each service had its own copy of the same few lines (read state.json, write it through a temporary file) and its own
idea of when to write: the Bluesky service at every look, the Telegram service at every pass with a message waiting.
Here the file is written **when what it holds has changed**, and at once when the service is told to stop, so that
"once per crossing" holds through a restart in one place.

    saved = SavedState("/var/lib/zenithboard/telegram", "telegram")
    state = saved.load()
    saved.save(state)            # writes when the state differs from what is on the card, says so by True
    saved.on_stop(lambda: state) # SIGTERM: write, then leave

A write by another process (`zenithboard social post` records its post while the service runs) is seen by the file's
time and size: the next save writes even when the service's own state has not moved.
"""
import json
import os
import signal
import sys


class SavedState(object):
    def __init__(self, directory, name, filename="state.json"):
        self.directory, self.name, self.filename = directory, name, filename
        self._text = None          # what this process last wrote or read
        self._stamp = None         # the file's (mtime_ns, size) then

    @property
    def path(self):
        return os.path.join(self.directory, self.filename)

    def _stamp_now(self):
        try:
            st = os.stat(self.path)
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def load(self):
        """The state as a dict; {} when the file is missing, unreadable or not a dict (a first start, a card cut off)."""
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                text = fh.read()
            s = json.loads(text)
        except (OSError, ValueError):
            self._text = self._stamp = None
            return {}
        if not isinstance(s, dict):
            self._text = self._stamp = None
            return {}
        self._text, self._stamp = text, self._stamp_now()
        return s

    def save(self, state, force=False):
        """Write the state when it differs from the file. True when written, False when there was nothing to write
        or the card refused (said once on the journal's error stream, as each service did)."""
        try:
            text = json.dumps(state)
        except (TypeError, ValueError) as exc:
            print("%s: cannot save state: %s" % (self.name, exc), file=sys.stderr, flush=True)
            return False
        if not force and text == self._text and self._stamp is not None and self._stamp == self._stamp_now():
            return False
        try:
            os.makedirs(self.directory, exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self.path)
        except OSError as exc:
            print("%s: cannot save state: %s" % (self.name, exc), file=sys.stderr, flush=True)
            return False
        self._text, self._stamp = text, self._stamp_now()
        return True

    def on_stop(self, current, before=None, save=None):
        """systemd stops a service with SIGTERM: what was already sent is written down first, so a restart never
        sends it again (0.99.16 for Telegram; the Bluesky service too since this helper). `current` gives the state,
        `before` may put a last figure in it."""
        def stop(signum, frame):
            state = current()
            if before:
                before(state)
            (save or self.save)(state)
            sys.exit(0)
        signal.signal(signal.SIGTERM, stop)
        return stop
