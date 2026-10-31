#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Telegram messages (0.99.6, asked for by the owner on 30 October 2026).

To one private Telegram chat, the owner's own or his group's: a message for each aircraft crossing the sharing radius
(the Bluesky posts' radius, and their rule: one message per crossing), and one for each aircraft, anywhere the antenna
hears it, that sends an emergency squawk (7500, 7600, 7700), once per flight and code. Off by default. Text only, from
templates in the posts' language (flightinfo/static/i18n/LANG/posts.json), or the owner's own when he writes them.
The squawks go to that chat and nowhere else: Bluesky never posts them.

What never leaves the Pi, here as in the posts: the receiver's position, and the distance or the bearing from it. A
squawk message says where the aircraft is from the aircraft's own position: the town of 5 000 inhabitants or more
nearest it, or the city of 100 000 or more and how far the aircraft is from that city.

The bot's token lives in /etc/zenithboard/telegram.env (root:zenithboard, mode 0640) with the chat's id: never in
config.env, in a log or on a command line. A network error that could carry the API's address has the token taken out.

    telegram.py run                            the service loop
    telegram.py check                          does the token answer (getMe)? the bot's name
    telegram.py chats                          the chats that wrote to the bot lately (getUpdates): id, kind, name
    telegram.py hello                          send the "connected" message to the chat set up
    telegram.py test [crossing|squawk] [send]  each message filled on an aircraft overhead now, or a sample; send: to the chat
    telegram.py template-check KIND [--] TEXT  the owner's template for crossing or squawk: usable, and short enough?
    telegram.py template-test KIND [--] [TEXT] that template filled on an aircraft overhead now, or a sample
    telegram.py template-default KIND          the default template of crossing or squawk, in the messages' language
    telegram.py template-tags                  the tags a template can use
    telegram.py status                         what it does, what it sent, what went wrong

Standard library only, like the wall and the Bluesky service, whose rules and words it shares (social.py).
"""
import datetime
import json
import os
import re
import signal
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server  # noqa: E402  (config, aircraft.json, places, user agent)
import post_lang  # noqa: E402  (the posts' language and their template language)
import social  # noqa: E402  (the crossing rule, the wall's answers, the template tags)

N_ = post_lang.N_

SECRETS_FILE = os.environ.get("ZENITHBOARD_TELEGRAM_SECRETS", "/etc/zenithboard/telegram.env")
STATE_DIR = os.environ.get("ZENITHBOARD_TELEGRAM_DIR", "/var/lib/zenithboard/telegram")
ETC = os.environ.get("ZENITHBOARD_ETC", "/etc/zenithboard")
TEMPLATE_FILES = {"crossing": os.path.join(ETC, "telegram-crossing.txt"), "squawk": os.path.join(ETC, "telegram-squawk.txt")}
API = os.environ.get("ZENITHBOARD_TELEGRAM_API", "https://api.telegram.org")      # a test points it at a stand-in

DEFAULTS = {
    "TELEGRAM": "0",
    "TELEGRAM_CROSSINGS": "1",        # the aircraft crossing the sharing radius (SOCIAL_RADIUS_KM), once per crossing
    "TELEGRAM_SQUAWKS": "1",          # the emergency squawks, anywhere the antenna hears them, once per flight and code
    "TELEGRAM_RULES": "all",          # all, or some of military,helicopter,heavy: which crossings are written
    "TELEGRAM_LANG": "",              # empty: the posts' language (SOCIAL_LANG), English until that is set
    "TELEGRAM_UNITS": "",             # empty: the posts' units, else the wall's
}
RULES = ("military", "helicopter", "heavy")   # rare and farthest need the Bluesky service's thirty days of history

READ_EVERY_S = 5
ASK_EVERY_S = 15
SETTLE_S = social.SETTLE_S        # a crossing whose route or model the wall is still looking up waits up to this long
CROSSING_GAP_S = social.CROSSING_GAP_S
SQUAWK_GAP_S = 3600               # the same flight squawking the same code again within the hour is the same event
CONFIRM_S = 4                     # a code is believed once seen on two reads this far apart, or with the aircraft's own
                                  # emergency status saying the same: one bad decode of a reply never sends a message
SEND_EVERY_S = 3.1                # Telegram: about 20 messages a minute into one group, one a second into a private chat
SENDS_PER_LOOK = 3
KEEP_S = {"squawk": 3600, "crossing": 600, "test": 600}   # a message that cannot go out is dropped after this long
PAUSE_ON_FAIL_S = 600             # a refused token or chat: tried again ten minutes later, not at every look
PAUSE_OFFLINE_S = 60
MAX_TEXT = 4096                   # Telegram's longest message
TEMPLATE_MAX = 1500               # the owner's template, as typed
NEAR_TOWN_KM = 15

EMERGENCY = {"7500": N_("Unlawful interference (hijacking)"), "7600": N_("Radio failure (lost communications)"),
             "7700": N_("General emergency")}
STATUS_CODE = {"unlawful": "7500", "nordo": "7600", "general": "7700"}      # readsb's "emergency" field

# The defaults. The words are the posts' catalogue's; the rest is tags, in every language alike. An empty [part] goes,
# and so does a line left empty.
SQUAWK_HEAD = N_("Squawk {squawk}: {meaning}")
TEST_HEAD = N_("Test message, not a real event:")
HELLO = N_("ZenithBoard is connected to this chat. The aircraft crossing the sharing radius and the emergency squawks the antenna hears will be written here.")
NEAR_TOWN = N_("near {place}")
NEAR_CITY = N_("{distance} from {place} ({country})")
NO_POSITION = N_("position not known")
BODY = "[{flight}][ · {airline}][ · {type}][ · {registration}][ {flag}]\n[{from} → {to}]\n[{altitude}][ · {speed}][ · {climb}]"
TAGS = tuple(social.TEMPLATE_TAGS) + ("near", "meaning", "hex")
TAG_HELP = social.TAG_HELP + (("near", "where the aircraft is: the town nearest it, or a city and how far (never from the antenna)"),
                              ("meaning", "what the emergency squawk means (7500, 7600, 7700), in the messages' language"),
                              ("hex", "the aircraft's ICAO address (4ca7b1)"))


def default_template(kind, L):
    """The message's template in that language, before any tag is filled."""
    if kind == "squawk":
        return "\U0001F6A8 " + raw(L, SQUAWK_HEAD) + "\n" + BODY + "\n[{near}]\n{time}[ · {tracker}]"
    return "✈ [{flight}][ · {airline}]\n[{why}]\n[{type}][ · {registration}][ {flag}]\n[{from} → {to}]\n" \
           "[{altitude}][ · {speed}][ · {climb}]\n{time}[ · {area}]\n[{tracker}]"


def raw(L, key):
    """The catalogue's template for that English key, unfilled."""
    got = L.words.get(key, key)
    return (got.get("other") or key) if isinstance(got, dict) else got


# --------------------------------------------------------------------------- settings and secrets
def cfg():
    c = social.cfg()
    for k, v in DEFAULTS.items():
        c.setdefault(k, v)
    return c


def secrets():
    try:
        with open(SECRETS_FILE, "r", encoding="utf-8") as fh:
            return server.parse_env_text(fh.read())
    except OSError:
        return {}


def ready(sec):
    return bool(sec.get("TELEGRAM_BOT_TOKEN") and sec.get("TELEGRAM_CHAT_ID"))


def lang_of(c):
    code = str(c.get("TELEGRAM_LANG") or c.get("SOCIAL_LANG") or "en").strip()
    return code if code in post_lang.offered() else "en"


def view(c):
    """The settings as the posts' code reads them, with the messages' own language and units in their place."""
    v = dict(c, SOCIAL_LANG=lang_of(c))
    u = str(c.get("TELEGRAM_UNITS") or "").strip().lower()
    if u in ("metric", "imperial", "aviation"):
        v["SOCIAL_UNITS"] = u
    return v


def rules_of(c):
    want = {r.strip().lower() for r in str(c.get("TELEGRAM_RULES", "all")).split(",") if r.strip()}
    return set(RULES) | {"all"} if "all" in want or not want else {r for r in want if r in RULES}


def scrub(text, sec=None):
    tok = (sec or secrets()).get("TELEGRAM_BOT_TOKEN") or ""
    text = str(text)
    return text.replace(tok, "<token>") if tok else re.sub(r"bot[0-9]{5,}:[A-Za-z0-9_-]{20,}", "bot<token>", text)


# --------------------------------------------------------------------------- the owner's templates
def template_file_text(kind):
    try:
        with open(TEMPLATE_FILES[kind], encoding="utf-8", errors="replace") as fh:
            return fh.read(TEMPLATE_MAX * 2).strip()
    except OSError:
        return ""


def template_problem(text):
    """None when it can be used, else why not, in plain words."""
    text = str(text or "").strip()
    if len(text) > TEMPLATE_MAX:
        return "too long: %d characters, %d at most" % (len(text), TEMPLATE_MAX)
    return post_lang.check_template(text, TAGS)


def template_of(kind, L):
    mine = template_file_text(kind)
    return mine if mine and template_problem(mine) is None else default_template(kind, L)


# --------------------------------------------------------------------------- the words
def distance_words(km, L, units):
    if units == "aviation":
        return L.num(int(round(km / 1.852))) + post_lang.NBSP + "NM"
    if units == "imperial":
        return L.num(int(round(km / 1.609344))) + post_lang.NBSP + "mi"
    return L.unit(int(round(km)), "kilometer")


def near_words(lat, lon, L, units):
    """Where the aircraft is, from its own position: the town of 5 000 or more nearest it within 15 km, else the city
    of 100 000 or more nearest it and how far from it. Never the antenna's position, nor the distance from it."""
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return L.t(NO_POSITION)
    towns = server._towns_near(lat, lon, NEAR_TOWN_KM)
    if towns:
        return L.t(NEAR_TOWN, place=server.tidy_place(min(towns, key=towns.get)))
    city = server.nearest_city(lat, lon)
    if not city:
        return ""
    cc = str(city.get("country") or "")
    return L.t(NEAR_CITY, distance=distance_words(city["km"], L, units), place=city["name"],
               country=L.country(cc, server.country_name(cc)) if cc else "")


def fill(kind, p, c, why=None, now=None, template=None, ac=None, code=None):
    """One message: the template filled, empty [parts] and empty lines gone, within Telegram's length."""
    v = view(c)
    L = post_lang.of(v)
    now = time.time() if now is None else now
    values = social.template_values(p, v, why, L, now)
    values["hex"] = str(p.get("hex") or "").lower()
    if code:
        values["squawk"], values["meaning"] = code, L.t(EMERGENCY.get(code, ""))
    else:
        values["meaning"] = ""
    tpl = template or template_of(kind, L)
    if "{near" in tpl:              # a few tenths of a second on a Pi 3 (the places list is read): only when it is asked for
        src = ac or {}
        values["near"] = near_words(src.get("lat", p.get("lat")), src.get("lon", p.get("lon")), L, social.units_of(v))
    text = L.render(tpl, values)
    lines = [re.sub(r"[ \t]{2,}", " ", x).strip() for x in text.split("\n")]
    text = "\n".join(x for x in lines if x and x not in ("✈", "\U0001F6A8"))
    return text[:MAX_TEXT]


# --------------------------------------------------------------------------- the network
class TgError(Exception):
    def __init__(self, code, text, params=None):
        Exception.__init__(self, text)
        self.code, self.text, self.params = code, text, params or {}


def call(sec, method, payload=None, timeout=20):
    """One Bot API call -> its result. TgError with Telegram's own code and words when it says no."""
    url = "%s/bot%s/%s" % (API, sec.get("TELEGRAM_BOT_TOKEN", ""), method)
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": server.USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8", "replace") or "{}")
        except (ValueError, OSError):
            body = {}
        raise TgError(exc.code, scrub(body.get("description") or "HTTP %s" % exc.code, sec), body.get("parameters"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise TgError(0, scrub("no answer: %s" % getattr(exc, "reason", exc), sec))
    if not isinstance(body, dict) or not body.get("ok"):
        body = body if isinstance(body, dict) else {}
        raise TgError(body.get("error_code", 0), scrub(body.get("description") or "refused", sec), body.get("parameters"))
    return body.get("result")


def send(sec, text):
    return call(sec, "sendMessage", {"chat_id": sec.get("TELEGRAM_CHAT_ID"), "text": text,
                                     "link_preview_options": {"is_disabled": True}})


# --------------------------------------------------------------------------- state
def load_state():
    try:
        with open(os.path.join(STATE_DIR, "state.json"), encoding="utf-8") as fh:
            s = json.load(fh)
            return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(s):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = os.path.join(STATE_DIR, "state.json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(s, fh)
        os.replace(tmp, os.path.join(STATE_DIR, "state.json"))
    except OSError as exc:
        print("telegram: cannot save state: %s" % exc, file=sys.stderr, flush=True)


def prune(s, now):
    """A crossing ends an hour after the aircraft left the radius; a squawk an hour after the code was last heard."""
    for key, gap in (("posted", CROSSING_GAP_S), ("squawks", SQUAWK_GAP_S)):
        s[key] = {k: v for k, v in (s.get(key) or {}).items() if isinstance(v, dict) and now - float(v.get("t", 0)) < gap}
    cut = (datetime.date.fromtimestamp(now) - datetime.timedelta(days=7)).isoformat()
    s["days"] = {d: n for d, n in (s.get("days") or {}).items() if d >= cut}
    s.pop("posts", None); s.pop("post_days", None)          # social.remember's counts: not kept here
    return s


def count(s, kind, now):
    day = s.setdefault("days", {}).setdefault(social.day_of(now), {})
    day[kind] = int(day.get(kind, 0)) + 1


# --------------------------------------------------------------------------- what is worth a message
class Squawks(object):
    """The emergency codes heard at each read; a code counts once it is heard twice, CONFIRM_S apart, or with the
    aircraft's own emergency status saying the same."""
    def __init__(self):
        self.heard = {}                            # "hex:code" -> [first, last]

    def look(self, aircraft, now):
        out = []
        for ac in aircraft or []:
            h = str(ac.get("hex", "")).lower().strip()
            if not re.match(r"^[0-9a-f]{6}$", h) or float(ac.get("seen", 0) or 0) > 60:
                continue
            own = STATUS_CODE.get(str(ac.get("emergency") or "").lower())
            sq = str(ac.get("squawk") or "").strip()
            code = sq if sq in EMERGENCY else own
            if not code:
                continue
            v = self.heard.setdefault(h + ":" + code, [now, now])
            v[1] = now
            if own == code or v[1] - v[0] >= CONFIRM_S:
                out.append((ac, code))
        for k in [k for k, v in self.heard.items() if now - v[1] > 120]:
            del self.heard[k]
        return out


def squawk_seen(state, ac, code, now):
    """(new, record): this flight's code was not written about within the hour (a different callsign on the same
    airframe is another flight); the record's time moves on while the code is heard."""
    flight = str(ac.get("flight") or "").strip().upper()
    key = str(ac.get("hex", "")).lower() + ":" + code
    rec = state.setdefault("squawks", {}).get(key)
    new = rec is None or (flight and rec.get("flight") and rec["flight"] != flight)
    state["squawks"][key] = {"t": now, "flight": flight or (rec or {}).get("flight", "")}
    return new


def squawk_plane(c, ac):
    """What the wall knows of a squawking aircraft (airline, model, route), or what aircraft.json says when the wall
    cannot place it (no position)."""
    p = social.ask_wall_one(c, ac.get("hex")) if "lat" in ac and "lon" in ac else None
    if p:
        return p
    alt = ac.get("alt_baro", ac.get("alt_geom"))
    return {"hex": ac.get("hex", ""), "flight": str(ac.get("flight") or "").strip(), "registration": ac.get("r"),
            "type": ac.get("t"), "alt_ft": alt if isinstance(alt, (int, float)) else None, "gs_kt": ac.get("gs"),
            "track": ac.get("track"), "vrate_fpm": ac.get("baro_rate", ac.get("geom_rate"))}


def crossing_candidates(c, planes, state, pending_since, now):
    """The aircraft inside the radius worth a message, not yet written about in this crossing: (plane, why)."""
    rules, out = rules_of(c), []
    for p in planes or ():
        if p.get("on_ground") or not (p.get("flight") or social.known(p)) or social.already_posted(state, p):
            continue
        if p.get("pending"):                       # the wall is still asking for its route or model: wait a little
            since = pending_since.setdefault(p.get("hex"), now)
            if now - since < SETTLE_S:
                continue
        score, why = social.interest(p, rules, {}, now)
        if score > 0:
            out.append((p, why))
    return out


# --------------------------------------------------------------------------- the outbox
class Outbox(object):
    def __init__(self):
        self.items, self.next_at, self.pause_until, self.said = [], 0.0, 0.0, {}
        self.moved = None                          # (old id, new id) once Telegram said the group became a supergroup

    def follow_move(self, sec):
        """A supergroup's new id, put back after each read of the secrets file (0.99.16: it was lost at the next read,
        a quarter of a minute later, and every message was refused again). Only the exact old id is replaced: a chat
        the owner set up since is his choice."""
        if self.moved and str(sec.get("TELEGRAM_CHAT_ID", "")) == self.moved[0]:
            sec["TELEGRAM_CHAT_ID"] = self.moved[1]
        return sec

    def add(self, kind, text, what, now):
        self.items.append({"kind": kind, "text": text, "what": what, "made": now})
        self.items.sort(key=lambda m: (m["kind"] != "squawk", m["made"]))    # an emergency goes first

    def note(self, key, line, now, every=600):
        """A line for the journal, at most once per `every` seconds for the same kind of trouble."""
        if now - self.said.get(key, 0) >= every:
            self.said[key] = now
            print(line, flush=True)

    def flush(self, sec, state, now, sender=None):
        sender = sender or send
        for m in [m for m in self.items if now - m["made"] > KEEP_S.get(m["kind"], 600)]:
            print("telegram: dropped the %s message about %s: it could not go out for %d min" % (m["kind"], m["what"], (now - m["made"]) // 60), flush=True)
            self.items.remove(m)
        n = 0
        while self.items and n < SENDS_PER_LOOK and now >= self.next_at and now >= self.pause_until:
            m = self.items[0]
            try:
                sender(sec, m["text"])
            except TgError as exc:
                return self.refused(exc, sec, state, now)
            self.items.pop(0)
            n += 1
            count(state, m["kind"], now)
            state["last"] = {"t": now, "kind": m["kind"], "what": m["what"]}
            print("telegram: sent the %s message about %s" % (m["kind"], m["what"]), flush=True)
            self.next_at = now + SEND_EVERY_S
            if self.items and n < SENDS_PER_LOOK:
                time.sleep(SEND_EVERY_S)
                now += SEND_EVERY_S
        return n

    def refused(self, exc, sec, state, now):
        state["error"] = {"t": now, "text": "%s %s" % (exc.code or "", exc.text)}
        retry = int((exc.params or {}).get("retry_after") or 0)
        moved = (exc.params or {}).get("migrate_to_chat_id")
        if exc.code == 429:
            self.pause_until = now + max(retry, 5)
            self.note("429", "telegram: Telegram asks to wait %d s (too many messages)" % max(retry, 5), now, 60)
        elif moved:
            # the group became a supergroup, with a new id: used from now on, kept in memory only (the service cannot
            # write its secrets file); the setup writes it for good
            self.moved = (str(sec.get("TELEGRAM_CHAT_ID", "")), str(moved))
            sec["TELEGRAM_CHAT_ID"] = str(moved)
            self.note("moved", "telegram: the group became a supergroup; its new id is used until a restart. To keep it: sudo zenithboard telegram chat", now)
        elif exc.code == 0:
            self.pause_until = now + PAUSE_OFFLINE_S
            self.note("offline", "telegram: %s; tried again in a minute" % exc.text, now)
        else:
            self.pause_until = now + PAUSE_ON_FAIL_S
            self.note("refused", "telegram: Telegram refused (%s %s); tried again in 10 min. Check: sudo zenithboard telegram check" % (exc.code, exc.text), now)
        return 0


# --------------------------------------------------------------------------- the service
def one_look(c, state, aircraft, squawks, pending_since, outbox, now, ask=True):
    """Detect what is new and queue its message. The squawks at every read, the crossings when it is time to ask the wall."""
    if server.cfg_bool(c, "TELEGRAM_SQUAWKS", "1"):
        for ac, code in squawks.look(aircraft, now):
            if squawk_seen(state, ac, code, now):
                p = squawk_plane(c, ac)
                what = "%s (%s)" % (p.get("flight") or p.get("registration") or ac.get("hex"), code)
                outbox.add("squawk", fill("squawk", p, c, now=now, ac=ac, code=code), what, now)
                print("telegram: squawk %s heard from %s" % (code, what.split(" (")[0]), flush=True)
    if ask and server.cfg_bool(c, "TELEGRAM_CROSSINGS", "1"):
        radius = server.cfg_float(c, "SOCIAL_RADIUS_KM", 15)
        planes = social.ask_wall(c, radius)
        social.note_seen(state, planes + social.inside_now(c, aircraft, radius), now)
        for p, why in crossing_candidates(c, planes, state, pending_since, now):
            social.remember(state, p, now)
            outbox.add("crossing", fill("crossing", p, c, why, now), p.get("flight") or p.get("registration") or p.get("hex"), now)
        if len(pending_since) > 2000:
            pending_since.clear()


def cmd_run():
    c, sec = cfg(), secrets()
    state = prune(load_state(), time.time())
    squawks, outbox, pending_since = Squawks(), Outbox(), {}
    # nothing read from telegram.env is ever written to the journal, the chat's name included (CodeQL #85-87, 0.99.6)
    print("telegram: running ZenithBoard %s. Bot and chat: %s. Crossings: %s (radius %s km, %s). Squawks: %s. Language: %s." % (
        server.VERSION, "set up" if ready(sec) else "NONE (run: sudo zenithboard telegram setup)",
        "on" if server.cfg_bool(c, "TELEGRAM_CROSSINGS", "1") else "off", c.get("SOCIAL_RADIUS_KM"),
        "all" if "all" in rules_of(c) else ", ".join(sorted(rules_of(c))),
        "on" if server.cfg_bool(c, "TELEGRAM_SQUAWKS", "1") else "off", lang_of(c)), flush=True)
    last_ask = last_save = 0

    def stop(signum, frame):
        # systemd stops the service with SIGTERM: what this pass already sent is written down first, so a restart
        # never sends it again (0.99.16)
        state["queue"] = len(outbox.items)
        save_state(state)
        sys.exit(0)
    signal.signal(signal.SIGTERM, stop)
    while True:
        now = time.time()
        c = cfg()
        aircraft = social.read_aircraft(c)
        ask = now - last_ask >= ASK_EVERY_S
        if ask:
            last_ask = now
            prune(state, now)
            sec = outbox.follow_move(secrets() or sec)
        before = len(outbox.items)
        try:
            one_look(c, state, aircraft, squawks, pending_since, outbox, now, ask)
        except Exception as exc:                    # a message that cannot be made must not stop the service
            print("telegram: could not make a message: %s" % exc, flush=True)
        queued, sent = len(outbox.items) > before, 0
        if outbox.items:
            if ready(sec):
                try:
                    sent = outbox.flush(sec, state, now) or 0
                except Exception as exc:            # whatever went wrong with one message, the service goes on
                    outbox.note("flush", "telegram: could not send: %s" % scrub(exc, sec), now, 600)
                    outbox.pause_until = now + PAUSE_OFFLINE_S
            else:
                outbox.note("nochat", "telegram: no bot or chat set up, nothing can be sent: sudo zenithboard telegram setup", now, 3600)
                outbox.items = [m for m in outbox.items if now - m["made"] <= KEEP_S.get(m["kind"], 600)]
        # written at once when this pass queued or sent anything (0.99.16: a message sent with the queue then empty
        # waited up to a minute to be written down, and a restart in that minute sent it again)
        if queued or sent or outbox.items or now - last_save >= 60:
            state["queue"] = len(outbox.items)
            save_state(state)
            last_save = now
        time.sleep(READ_EVERY_S)


# --------------------------------------------------------------------------- commands
SQUAWK_SAMPLE_AC = {"hex": "4ca7b1", "lat": 50.04, "lon": 8.56, "squawk": "7700"}     # by Frankfurt airport: never near the antenna


def sample_plane(c, kind):
    """An aircraft overhead now (the nearest the wall knows well), else the posts' own sample."""
    planes = [p for p in social.ask_wall(c, server.cfg_float(c, "SOCIAL_RADIUS_KM", 15)) if social.known(p) and not p.get("on_ground")]
    return (planes[0], None) if planes else (dict(social.SAMPLE), SQUAWK_SAMPLE_AC if kind == "squawk" else None)


def message_for(kind, c, template=None):
    p, ac = sample_plane(c, kind)
    if kind == "squawk":
        return fill("squawk", p, c, template=template, ac=ac or SQUAWK_SAMPLE_AC, code="7700")
    return fill("crossing", p, c, template=template)


def cmd_check():
    sec = secrets()
    if not sec.get("TELEGRAM_BOT_TOKEN"):
        print("FAILED: no bot token set up. Run: sudo zenithboard telegram setup")
        return 1
    try:
        me = call(sec, "getMe") or {}
    except TgError as exc:
        print("FAILED: Telegram says %s %s" % (exc.code or "", exc.text))
        return 1
    print("OK: the bot @%s (%s) answers." % (me.get("username", "?"), me.get("first_name", "")))
    return 0


def cmd_chats():
    """The chats seen in the bot's waiting updates, newest first: a private chat after /start, a group the bot was added
    to or that wrote /start@bot. One a line: id, kind, name (tabs and line ends taken out)."""
    sec = secrets()
    try:
        ups = call(sec, "getUpdates", {"timeout": 0, "allowed_updates": ["message", "channel_post", "my_chat_member"]}) or []
    except TgError as exc:
        print("FAILED: Telegram says %s %s" % (exc.code or "", exc.text), file=sys.stderr)
        return 1
    seen = {}
    for u in ups:
        for k in ("message", "channel_post", "my_chat_member", "edited_message"):
            chat = (u.get(k) or {}).get("chat") if isinstance(u.get(k), dict) else None
            if isinstance(chat, dict) and "id" in chat:
                name = chat.get("title") or " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x) or chat.get("username") or "?"
                seen[str(chat["id"])] = (chat.get("type") or "?", re.sub(r"[\t\r\n]+", " ", name)[:60])
    for cid, (kind, name) in reversed(list(seen.items())):
        print("%s\t%s\t%s" % (cid, kind, name))
    return 0


def cmd_hello():
    sec = secrets()
    if not ready(sec):
        print("FAILED: no bot or chat set up. Run: sudo zenithboard telegram setup")
        return 1
    try:
        send(sec, post_lang.of(view(cfg())).t(HELLO))
    except TgError as exc:
        print("FAILED: Telegram says %s %s" % (exc.code or "", exc.text))
        return 1
    print("OK: the message is in the chat.")
    return 0


def cmd_test(kinds, do_send=False):
    c, sec = cfg(), secrets()
    L = post_lang.of(view(c))
    rc = 0
    for kind in kinds:
        text = message_for(kind, c)
        print("---- %s message (%s)" % (kind, lang_of(c)))
        print(text)
        if do_send:
            if not ready(sec):
                print("FAILED: no bot or chat set up. Run: sudo zenithboard telegram setup")
                return 1
            try:
                send(sec, L.t(TEST_HEAD) + "\n" + text)
                print("(sent)")
            except TgError as exc:
                print("FAILED: Telegram says %s %s" % (exc.code or "", exc.text))
                rc = 1
            time.sleep(SEND_EVERY_S if kind != kinds[-1] else 0)
    if not do_send:
        print("(nothing sent)")
    return rc


def cmd_template_check(kind, text):
    if kind not in TEMPLATE_FILES:
        print("Which template? crossing or squawk")
        return 1
    if str(text).strip().lower() in ("", "none"):
        print("No template of your own: the default is used.")
        return 0
    why = template_problem(text)
    if why:
        print("Not usable: %s." % why)
        return 1
    long_one = fill(kind, social.LONG_SAMPLE, cfg(), "military", template=text, ac=SQUAWK_SAMPLE_AC, code="7700" if kind == "squawk" else None)
    print("Usable. On a long sample it makes %d characters (Telegram takes %d)." % (len(long_one), MAX_TEXT))
    return 0


def cmd_template_test(kind, text=None):
    if kind not in TEMPLATE_FILES:
        print("Which template? crossing or squawk")
        return 1
    c = cfg()
    text = (text or "").strip() or None
    if text and template_problem(text):
        print("Not usable: %s." % template_problem(text))
        return 1
    print(message_for(kind, c, template=text))
    print("(nothing sent)")
    return 0


def cmd_status():
    c, sec, s = cfg(), secrets(), load_state()
    now = time.time()
    print("Telegram messages: %s" % ("ON" if server.cfg_bool(c, "TELEGRAM", "0") else "off"))
    print("  Bot and chat: %s" % ("set up" if ready(sec) else "NOT set up (sudo zenithboard telegram setup)"))
    print("  Crossings: %s, the sharing radius (%s km), %s" % ("on" if server.cfg_bool(c, "TELEGRAM_CROSSINGS", "1") else "off",
                                                              c.get("SOCIAL_RADIUS_KM"), "every crossing" if "all" in rules_of(c) else ", ".join(sorted(rules_of(c)))))
    print("  Emergency squawks: %s, anywhere the antenna hears them (7500, 7600, 7700)" % ("on" if server.cfg_bool(c, "TELEGRAM_SQUAWKS", "1") else "off"))
    print("  Language: %s   Units: %s" % (lang_of(c), social.units_of(view(c))))
    for kind in ("crossing", "squawk"):
        mine = template_file_text(kind)
        print("  %s template: %s" % (kind.capitalize(), "yours" if mine and not template_problem(mine) else ("yours, NOT usable (%s): the default is used" % template_problem(mine) if mine else "the default")))
    days = s.get("days") or {}
    today = days.get(social.day_of(now), {})
    # today and the six days before it, by date (0.99.16: every stored day was added, eight of them after midnight)
    seven = {(datetime.date.fromtimestamp(now) - datetime.timedelta(days=i)).isoformat() for i in range(7)}
    week = {k: sum(int(d.get(k, 0)) for day, d in days.items() if day in seven and isinstance(d, dict)) for k in ("crossing", "squawk")}
    print("  Sent today: %d crossing(s), %d squawk(s); last 7 days: %d and %d" % (int(today.get("crossing", 0)), int(today.get("squawk", 0)), week["crossing"], week["squawk"]))
    last = s.get("last") or {}
    if last:
        print("  Last sent: %s, the %s message about %s" % (time.strftime("%Y-%m-%d %H:%M", time.localtime(last.get("t", 0))), last.get("kind"), last.get("what")))
    err = s.get("error") or {}
    if err and now - float(err.get("t", 0)) < 86400:
        print("  Last refusal: %s, %s" % (time.strftime("%H:%M", time.localtime(err.get("t", 0))), err.get("text")))
    if s.get("queue"):
        print("  Waiting to go out: %s" % s.get("queue"))
    return 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "status"
    rest = argv[2:]
    if rest[:1] == ["--"]:
        rest = rest[1:]
    if cmd == "run":
        return cmd_run()
    if cmd == "check":
        return cmd_check()
    if cmd == "chats":
        return cmd_chats()
    if cmd == "hello":
        return cmd_hello()
    if cmd == "test":
        kinds = [k for k in rest if k in TEMPLATE_FILES] or ["crossing", "squawk"]
        return cmd_test(kinds, "send" in rest)
    if cmd in ("template-check", "template-test"):
        kind = rest[0] if rest else ""
        text = rest[1:]
        if text[:1] == ["--"]:
            text = text[1:]
        text = "\n".join(text)
        return cmd_template_check(kind, text) if cmd == "template-check" else cmd_template_test(kind, text)
    if cmd == "template-default":
        if not rest or rest[0] not in TEMPLATE_FILES:
            print("Which template? crossing or squawk")
            return 1
        print(default_template(rest[0], post_lang.of(view(cfg()))))
        return 0
    if cmd == "template-tags":
        for name, words in TAG_HELP:
            print("  {%s}  %s" % (name, words))
        print("  [ ... ]  a part left out when a tag inside is empty;  {tag|cap}  with a capital")
        return 0
    if cmd == "status":
        return cmd_status()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
