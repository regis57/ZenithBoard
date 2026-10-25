# SPDX-License-Identifier: GPL-3.0-or-later
"""What the web console (0.39.0) may ask the Pi to do: one fixed list, read by both sides.

The wall's server runs as the unprivileged `zenithboard` user and cannot change anything itself. When a signed-in
browser asks for a change, the server checks it against this list and drops a small job file in a spool folder; a
root helper started by systemd (tools/console_run.py) reads the file, checks it against this same list again, and
runs the one `zenithboard` command it describes, as an argument list: never through a shell, never a command that is
not written below. A value is only ever one of the values listed, a number in its range, or text matching its pattern.

Left out on purpose, and done over SSH: uninstalling, Wi-Fi on/off/connect/forget/country and fixed addresses (one
mistake cuts the Pi off the network the console is reached through), anything asking for a password, token or key
(the Bluesky account, the domain name), posting to Bluesky, emptying statistics or logs, importing settings or
restoring a backup (0.42.0: a backup is made here and downloaded, but put back over SSH; the networks' keys never
travel through the console, so its backup leaves them out),
`config-set` (any key, any value), and the old ACARS removal.

A text value (0.51.0: the owner's own post templates, one per line) is passed as one argument, never split.
"""
import re
import unicodedata

HHMM = r"([01]?[0-9]|2[0-3]):[0-5][0-9]"
ON_OFF = ("on", "off")
THEMES = ("amber", "green", "red", "white", "turquoise")
PERIODS = ("daily", "weekly", "monthly")
# 0.50.0: the words of the posts, as lib/social.sh checks them again (social_hashtags_clean, social_area_clean)
HASHTAGS_RE = r"none|default|#?[A-Za-z0-9_]{1,40}( #?[A-Za-z0-9_]{1,40}){0,7}"
AREA_RE = r"[^\W_][\w '\u2019.,-]{0,39}"
RULES = ("military", "helicopter", "heavy", "rare", "farthest")
RULES_RE = r"^(all|(%s)(,(%s)){0,4})$" % ("|".join(RULES), "|".join(RULES))
TEMPLATES_MAX = 1500             # 0.51.0: the owner's templates, all of them (a few lines of 260 characters at most each)
# 0.47.0: the web pages' languages, the same codes as lib/common.sh (ZB_LANG_CODES) and flightinfo/static/i18n.js; the
# command itself refuses one this Pi has no catalogue for
LANGS = ("en", "fr", "de", "nl", "it", "es", "pt-BR", "pl", "fi", "et", "lv", "lt", "id", "sw", "ru", "uk", "ar", "ja", "ko",
         "zh-Hans", "zh-Hant")

SECTIONS = (
    ("overview", "Overview"),
    ("wall", "Wall"),
    ("receiver", "Receiver"),
    ("sharing", "Sharing"),
    ("reliability", "Reliability"),
    ("system", "System"),
)

# name: section, label, argv after `zenithboard` ({param} is replaced by its checked value; {param*} is split on
# spaces), params as (name, kind, choices or range or pattern, optional), and how the page should treat it:
#   read  -- only looks (status, health...): no confirmation, output shown
#   long  -- may take minutes (updates, installers): said before it starts
#   wall  -- restarts the wall's server, so the page reconnects by itself
#   ask   -- the page asks "are you sure" first
ACTIONS = {
    # -- the wall
    "units":        ("wall", "Units", ["units", "{value}"], [("value", "enum", ("metric", "imperial"))], "wall"),
    "radius":       ("wall", "Detection radius", ["radius", "{value}"], [("value", "enum", ("1", "2", "5", "10", "15", "30", "50"))], "wall"),
    "color":        ("wall", "Colour", ["color", "{value}"], [("value", "enum", THEMES)], "wall"),
    "mode":         ("wall", "Look", ["mode", "{value}"], [("value", "enum", ("dots", "flap"))], "wall"),
    "cycle":        ("wall", "Seconds per aircraft", ["cycle", "{value}"], [("value", "int", (2, 60))], "wall"),
    "photos":       ("wall", "Aircraft photos", ["photos", "{value}"], [("value", "enum", ON_OFF)], "wall"),
    "routes":       ("wall", "Flight routes", ["routes", "{value}"], [("value", "enum", ON_OFF)], "wall"),
    "localdb":      ("wall", "Receiver map's aircraft database", ["data", "localdb", "{value}"], [("value", "enum", ON_OFF)], "wall"),
    "data-auto":    ("wall", "Monthly aircraft-data refresh", ["data", "auto", "{value}"], [("value", "enum", ON_OFF)], ""),
    "data-update":  ("wall", "Refresh the aircraft data now", ["data", "update"], [], "long"),
    "data-status":  ("wall", "Aircraft data", ["data", "status"], [], "read"),
    "presets":      ("wall", "Presets", ["preset", "list"], [], "read"),
    # -- the receiver
    "region":       ("receiver", "Region", ["region", "{value}"], [("value", "enum", ("world", "us"))], ""),
    "location":     ("receiver", "Antenna position", ["location", "{lat}", "{lon}", "{alt}"],
                     [("lat", "float", (-90, 90)), ("lon", "float", (-180, 180)), ("alt", "int", (-500, 9000), True)], "ask wall long"),
    "stats":        ("receiver", "Statistics", ["stats", "{value}"], [("value", "enum", ON_OFF)], ""),
    "stats-show":   ("receiver", "Statistics", ["stats"], [], "read"),
    "stats-gaps":   ("receiver", "Unknown callsigns and types", ["stats", "gaps"], [], "read"),
    "graphs":       ("receiver", "graphs1090", ["graphs", "{value}"], [("value", "enum", ON_OFF)], "long ask"),
    "graphs-look":  ("receiver", "graphs1090 in ZenithBoard's look", ["graphs", "look", "{value}"], [("value", "enum", ON_OFF)], ""),
    # 0.52.0: ADSB Exchange's stats package, by their own script (lib/adsbxstats.sh); it asks nothing
    "adsbx-stats":  ("receiver", "ADSB Exchange stats", ["adsbx-stats", "{value}"], [("value", "enum", ON_OFF)], "long ask"),
    "gain-check":   ("receiver", "Gain check", ["gain", "check"], [], "read"),
    "gain-step":    ("receiver", "Gain one step", ["gain", "{value}"], [("value", "enum", ("up", "down"))], "ask"),
    "gain-log":     ("receiver", "Gain log, 24 h", ["gain", "log", "{value}"], [("value", "enum", ON_OFF)], ""),
    "status":       ("receiver", "Status", ["status"], [], "read"),
    "mlat-guard":   ("receiver", "One MLAT client only", ["mlat-guard"], [], ""),
    # -- sharing (the Bluesky account itself is set up over SSH: it asks for an app password)
    "social":       ("sharing", "Social sharing", ["social", "{value}"], [("value", "enum", ON_OFF)], "ask long"),
    "social-status": ("sharing", "Sharing status", ["social", "status"], [], "read"),
    "social-test":  ("sharing", "Try a post", ["social", "test"], [], "read long"),
    "social-look":  ("sharing", "Picture", ["social", "look", "{value}"], [("value", "enum", ("dotmap", "flap", "alternate"))], "long"),
    "social-colour": ("sharing", "Picture colour", ["social", "colour", "{value}"], [("value", "enum", THEMES + ("wall", "rotate"))], ""),
    "social-units": ("sharing", "Units of the posts", ["social", "units", "{value}"], [("value", "enum", ("metric", "imperial", "wall"))], ""),
    "social-map":   ("sharing", "Map", ["social", "map", "{value}"], [("value", "enum", ("normal", "night", "satellite", "terrain", "none", "rotate"))], ""),
    "social-photolink": ("sharing", "Photo link", ["social", "photolink", "{value}"], [("value", "enum", ON_OFF)], ""),
    "social-sentence": ("sharing", "Words of a post", ["social", "sentence", "{value}"],
                     [("value", "re", r"^(random|(factual|story|board|spotter|lookup|custom)(,(factual|story|board|spotter|lookup|custom)){0,5})$")], ""),
    # 0.51.0: the posts' language, and the owner's own templates (one per line; "none" for none), tried before they go
    "social-lang":  ("sharing", "Language of the posts", ["social", "lang", "{value}"], [("value", "enum", LANGS)], ""),
    "social-templates": ("sharing", "Your own templates", ["social", "template", "set", "--", "{text}"], [("text", "text", (TEMPLATES_MAX, None))], ""),
    "social-template-try": ("sharing", "Try the templates", ["social", "template", "test", "--", "{text}"], [("text", "text", (TEMPLATES_MAX, None))], "read"),
    # 0.53.3: a real button to delete them all (the owner), and one to put back the ones before the last change (.bak)
    "social-templates-delete": ("sharing", "Delete your templates", ["social", "template", "set", "--", "none"], [], "ask"),
    "social-templates-undo": ("sharing", "Put back your previous templates", ["social", "template", "undo"], [], "ask"),
    "social-gap":   ("sharing", "Least time between posts", ["social", "gap", "{value}"], [("value", "int", (0, 1440))], ""),
    # 0.50.0: what `social words` asks, one answer at a time
    "social-area":  ("sharing", "Place name", ["social", "area", "{value}"], [("value", "text", (40, AREA_RE))], ""),
    "social-radius": ("sharing", "Sharing radius", ["social", "radius", "{value}"], [("value", "int", (1, 200))], ""),
    "social-rules": ("sharing", "What is worth a post", ["social", "rules", "{value}"], [("value", "re", RULES_RE)], ""),
    "social-hashtags": ("sharing", "Hashtags", ["social", "hashtags", "{value*}"], [("value", "text", (340, HASHTAGS_RE))], ""),
    "social-places": ("sharing", "Town names on the maps", ["social", "places", "{value}"], [("value", "enum", ON_OFF)], "long"),
    "summary":      ("sharing", "Summary", ["social", "summary", "{period}", "{value}"], [("period", "enum", PERIODS), ("value", "enum", ON_OFF)], ""),
    "summary-at":   ("sharing", "Summary time", ["social", "summary", "{period}", "at", "{when*}"],
                     [("period", "enum", PERIODS),
                      ("when", "re", r"^(" + HHMM + r"|(mon|tue|wed|thu|fri|sat|sun) " + HHMM + r"|([1-9]|1[0-9]|2[0-8]) " + HHMM + r")$")], ""),
    "summary-parts": ("sharing", "Summary posts", ["social", "summary", "{period}", "parts", "{value}"],
                     [("period", "enum", PERIODS), ("value", "re", r"^[1-4](,[1-4]){0,3}$")], ""),
    "summary-test": ("sharing", "Try a summary", ["social", "summary", "{period}", "test"], [("period", "enum", PERIODS)], "read long"),
    "summaries":    ("sharing", "Summaries", ["social", "summary"], [], "read"),
    # -- reliability
    "watchdog":     ("reliability", "Hardware watchdog", ["watchdog", "{value}"], [("value", "enum", ON_OFF)], "ask"),
    "netwatch":     ("reliability", "Network watchdog", ["netwatch", "{value}"], [("value", "enum", ON_OFF)], ""),
    "keeplogs":     ("reliability", "Logs kept after a restart", ["keeplogs", "{value}"], [("value", "enum", ON_OFF)], ""),
    "wifi-harden":  ("reliability", "Wi-Fi hardening", ["wifi", "harden", "{value}"], [("value", "enum", ON_OFF)], ""),
    "patches":      ("reliability", "Daily security fixes", ["patches", "{value}"], [("value", "enum", ON_OFF)], ""),
    "logs-auto":    ("reliability", "Daily log clean-up", ["logs", "auto", "{value}"], [("value", "enum", ON_OFF)], ""),
    "health":       ("reliability", "Health", ["health"], [], "read"),
    "memory":       ("reliability", "Memory", ["memory"], [], "read"),
    "logs":         ("reliability", "Logs", ["logs", "{value}"], [("value", "enum", ("flightinfo", "decoder", "social", "uat"))], "read"),
    "logs-review":  ("reliability", "Log size and warnings", ["logs", "review"], [], "read"),
    # -- system
    "security":     ("system", "Security check", ["security"], [], "read"),
    "update-list":  ("system", "Installed components", ["update", "list"], [], "read"),
    "update-quick": ("system", "Update ZenithBoard and the wall", ["update", "quick"], [], "ask long wall"),
    "update":       ("system", "Update everything", ["update"], [], "ask long wall"),
    "net-status":   ("system", "Network", ["net", "status"], [], "read"),
    "tailscale-status": ("system", "Tailscale", ["tailscale", "status"], [], "read"),
    # 0.45.1 (the owner: "make Tailscale appear in the console"): connect (it installs Tailscale the first time, and
    # prints the sign-in link the page shows), disconnect, the console over Tailscale. Removing it asks for a typed
    # word: in the terminal, like every such step.
    "tailscale":    ("system", "Tailscale", ["tailscale", "{value}"], [("value", "enum", ON_OFF)], "ask long wall"),
    "tailscale-console": ("system", "The console over Tailscale", ["tailscale", "console", "{value}"], [("value", "enum", ON_OFF)], "ask wall"),
    "wifi-status":  ("system", "Wi-Fi", ["wifi", "status"], [], "read"),
    "ddns-status":  ("system", "Domain name", ["ddns", "status"], [], "read"),
    "ddns-update":  ("system", "Refresh the domain name", ["ddns", "update"], [], ""),
    "backup":       ("system", "Make a backup to download", ["backup", "make", "--console"], [], "long"),
    "backup-delete": ("system", "Delete the console's backup", ["backup", "delete", "--console"], [], "ask"),
    "console-off":  ("system", "Turn the console off", ["console", "off"], [], "ask"),
    "console-lang": ("system", "Language of the web pages", ["console", "lang", "{value}"], [("value", "enum", LANGS)], ""),
    "phone-signin": ("system", "Sign computers in with a phone", ["console", "phone-signin", "{value}"], [("value", "enum", ON_OFF)], "ask"),
    "refresh":      ("overview", "Refresh", None, [], "read"),       # nothing to run: the helper only reads the state again
}

JOB_ID_RE = re.compile(r"^[0-9a-f]{16}$")


class Refused(ValueError):
    """An action or a value that is not in the list."""


def _unwritable(ch):
    cat = unicodedata.category(ch)
    return (cat == "Cc" and ch not in "\n\t") or cat in ("Cs", "Co")


def _check(kind, rule, value):
    value = str(value).strip()
    if kind == "enum":
        if value in rule:
            return value
    elif kind == "int":
        if re.match(r"^-?\d{1,5}$", value) and rule[0] <= int(value) <= rule[1]:
            return str(int(value))
    elif kind == "float":
        if re.match(r"^-?\d{1,3}(\.\d{1,7})?$", value) and rule[0] <= float(value) <= rule[1]:
            return value
    elif kind == "re":
        if len(value) <= 64 and re.match(rule, value):
            return value
    elif kind == "text":                          # 0.50.0: (longest, pattern or None); lines kept, no other control
        longest, pattern = rule
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        # control characters but the line and the tab; a lone surrogate (a JSON escape could carry one, and nothing
        # can write it out) or a private-use character
        if 0 < len(value) <= longest and not any(_unwritable(ch) for ch in value) \
                and (pattern is None or ("\n" not in value and re.fullmatch(pattern, value))):
            return value
    raise Refused("not an allowed value")


def checked(name, params):
    """The values as build() takes them (stripped, lines as \n): what the job file keeps (0.50.0), so a value padded
    with spaces in a crafted request cannot make the file too long for the helper. Raises Refused like build()."""
    build(name, params)
    spec = ACTIONS[name]
    params = params if isinstance(params, dict) else {}
    out = {}
    for p in spec[3]:
        raw = params.get(p[0], "")
        if raw not in ("", None):
            out[p[0]] = _check(p[1], p[2], raw)
    return out


def build(name, params):
    """-> the argument list after `zenithboard`, or None for "refresh". Raises Refused for anything not listed."""
    spec = ACTIONS.get(name) if isinstance(name, str) else None
    if spec is None:
        raise Refused("unknown action")
    params = params if isinstance(params, dict) else {}
    known = {p[0] for p in spec[3]}
    if set(params) - known:
        raise Refused("unexpected value")
    got = {}
    for p in spec[3]:
        pname, kind, rule = p[0], p[1], p[2]
        optional = len(p) > 3 and p[3]
        raw = params.get(pname, "")
        if raw in ("", None):
            if optional:
                got[pname] = None
                continue
            raise Refused("missing value: %s" % pname)
        got[pname] = _check(kind, rule, raw)
    if spec[2] is None:
        return None
    argv = []
    for tok in spec[2]:
        m = re.match(r"^\{(\w+)(\*?)\}$", tok)
        if not m:
            argv.append(tok)
        elif got[m.group(1)] is None:
            continue
        elif m.group(2):
            argv.extend(got[m.group(1)].split(" "))
        else:
            argv.append(got[m.group(1)])
    return argv


def flags(name):
    spec = ACTIONS.get(name)
    return set(spec[4].split()) if spec else set()


def catalog():
    """What the page needs to draw a control: the label, the values it takes, the flags. Never the command."""
    out = {}
    for name, spec in ACTIONS.items():
        params = []
        for p in spec[3]:
            item = {"name": p[0], "kind": p[1], "optional": bool(len(p) > 3 and p[3])}
            if p[1] == "enum":
                item["choices"] = list(p[2])
            elif p[1] in ("int", "float"):
                item["min"], item["max"] = p[2]
            elif p[1] == "text":
                item["max"] = p[2][0]
            params.append(item)
        out[name] = {"section": spec[0], "label": spec[1], "params": params, "flags": sorted(flags(name))}
    return out
