# Telegram

Since 0.99.6 (30 October 2026, asked for by the owner). Off by default.

ZenithBoard can write to **your own Telegram chat**, or to a group of yours: a short text message

* for **each aircraft crossing the sharing radius**, the same radius and the same rule as the Bluesky posts (one message per crossing; an hour outside the radius ends it). Every crossing, or only military aircraft, helicopters or heavies;
* for **each emergency squawk** the antenna hears, **anywhere in its range**, not only in the radius: 7500 (unlawful interference), 7600 (radio failure), 7700 (general emergency). Once per flight and code, with what the code means and where the aircraft is.

The squawks go to that chat and **nowhere else: Bluesky never posts them**. An emergency is not a fact to broadcast: the crew and the rescue services are not an audience, and a code can be set by mistake.

## Setting it up

You need a bot of your own, made in Telegram in a minute, and its **token**. The token stays on the Pi; it is typed in the terminal, never in the web console.

1. In Telegram, open **@BotFather** and send `/newbot`. Give it a name, then a username ending in `bot`. BotFather answers with the token (`123456789:AA…`).
2. On the Pi: `sudo zenithboard telegram setup` (or menu *7 Options → 5 Telegram → 2 The bot and the chat*). Paste the token when asked: it is hidden, and tried at once with Telegram (*OK: the bot @… answers*).
3. The chat: **for you alone**, open your bot in Telegram and send it `/start`; **for a group**, add the bot to the group, then send `/start@yourbot` in it. Press OK: the Pi lists the chats that wrote to the bot, you choose one. Nothing is typed: the list comes from Telegram.
4. The bot writes *ZenithBoard is connected to this chat…* there, and the Pi offers to switch the messages on.

The rest is set in the web console, *Sharing → Telegram*, or with the commands below.

## What a message says

The words come from templates in the posts' language (or the messages' own, `telegram lang`), with the same tags as the posts' own templates, plus three:

| Tag | What it gives |
|---|---|
| `{near}` | Where the aircraft is, from its own position: *near Thionville* (the town of 5 000 inhabitants or more nearest it, within 15 km), else *35 km from Luxembourg (Luxembourg)* (the city of 100 000 or more nearest it, and how far from it). **Never from the antenna** |
| `{meaning}` | What the squawk means, in the messages' language: *General emergency* |
| `{hex}` | The aircraft's ICAO address |

The default crossing message:

```
✈ EZY17QZ · easyJet
Airbus A320 · G-EZWA 🇬🇧
Manchester (MAN) → Verona (VRN)
10 970 m · 834 km/h · level
14:05 · above Trémery
https://globe.adsbexchange.com/?icao=4ca7b1
```

The default squawk message:

```
🚨 Squawk 7700: General emergency
EZY17QZ · easyJet · Airbus A320 · G-EZWA 🇬🇧
Manchester (MAN) → Verona (VRN)
3 660 m · 556 km/h · descending
near Kelsterbach
14:05 · https://globe.adsbexchange.com/?icao=4ca7b1
```

A part in `[brackets]` goes when a tag inside it is empty, and so does a line left empty: an aircraft with no known route has no route line. The crossing message says your place name (`{area}`, *above Trémery*), never a town near the antenna; `{near}` is there for a crossing too if you want it, knowing that inside the sharing radius it names a town near you.

**Your own messages**: the console's *Your own Telegram messages* (one for the crossings, one for the squawks; lines kept; the tags a click away; tried on an aircraft overhead before it is saved), or `sudo zenithboard telegram template crossing set -- "TEXT"`. The one before is kept as `.bak` (`telegram template crossing undo`); `set none` gives the default back. A template that cannot be used (an unknown tag, a bracket left open) is refused when saved, and the default is used if one gets broken by hand.

## How a squawk is believed

The service reads the decoder's `aircraft.json` every five seconds. A code is believed when it is heard on **two reads in a row** (one reply decoded wrongly once never sends a message), or at once when the aircraft's own emergency status says the same (readsb's `emergency`: `general`, `nordo`, `unlawful`). Once per flight and code: the same aircraft squawking 7700 for twenty minutes is one message; 7700 then 7600 is two (the radio failed after the emergency); the same airframe as another flight, or the same code more than an hour after it was last heard, is a new event.

What the message knows comes from the wall (airline, model, route, as for the posts) when the aircraft has a position, else from `aircraft.json` alone; without a position, `{near}` says *position not known*.

## Sending

* **Paced as Telegram asks**: one message every 3.1 seconds at most, about 20 a minute into a group (Telegram's limit; one a second into a private chat). A burst waits its turn, an emergency first.
* A **429** (*too many requests*) waits the time Telegram gives. Telegram not reachable: tried again a minute later. A token or a chat refused (the bot removed from the group, the token revoked): tried again ten minutes later, said once in the journal.
* A message that cannot go out is dropped after **ten minutes** for a crossing, **an hour** for a squawk; the journal says so.
* A group that becomes a supergroup gets a new id: the service follows it until it restarts; `sudo zenithboard telegram chat` keeps it for good.
* Link previews are off: a link is a link, no picture is fetched.

## Commands

| Command | |
|---|---|
| `sudo zenithboard telegram setup` | The bot (its token) and the chat |
| `sudo zenithboard telegram on` · `off` · `status` | Switch the messages; what it sends, what it sent today and in seven days, the last refusal |
| `sudo zenithboard telegram chat` | Choose the chat again |
| `sudo zenithboard telegram check` · `hello` | Does the token answer; send the *connected* message |
| `zenithboard telegram test [crossing\|squawk] [send]` | Each message filled now, sent nowhere; `send`: to the chat, marked as a test |
| `sudo zenithboard telegram crossings on` · `off`, `squawks on` · `off` | Each kind of message |
| `sudo zenithboard telegram rules all` · `military,helicopter,heavy` | Which crossings |
| `sudo zenithboard telegram lang CODE` · `posts`, `units NAME` · `posts` | The messages' language and units; `posts`: the posts' own |
| `sudo zenithboard telegram template crossing\|squawk …` | Your own messages: `show`, `default`, `tags`, `set TEXT`, `test [TEXT]`, `undo` |
| `sudo zenithboard telegram remove` | Forget the token and the chat, stop the service (asks you to type `remove`) |
| `zenithboard logs telegram` | Its journal |

## What it keeps, and where

| | |
|---|---|
| `/etc/zenithboard/telegram.env` | The token and the chat (its id and name). root:zenithboard, mode 0640. Never in `config.env`, a log, a backup, the console or a command line |
| `/etc/zenithboard/telegram-crossing.txt`, `telegram-squawk.txt` | Your own messages, your words (a backup keeps them) |
| `/var/lib/zenithboard/telegram/state.json` | The crossings and squawks already written about (an hour), the counts of seven days, the last refusal |
| `config.env` | `TELEGRAM`, `TELEGRAM_CROSSINGS`, `TELEGRAM_SQUAWKS`, `TELEGRAM_RULES`, `TELEGRAM_LANG`, `TELEGRAM_UNITS` ([Configuration reference](Configuration-reference)) |

The service, `zenithboard-telegram`, runs as the wall's user in the same sandbox as the Bluesky service, text only (about 25 MB). It reaches `api.telegram.org` and the wall on the loopback, nothing else. A backup keeps the switch and your templates; restored on a new card, it asks for the token again (`telegram setup`).

**Not yet sent from a Pi** ([Project status](Project-status)): the messages, the squawk rule, the pacing and Telegram's answers are tested against a stand-in for its Bot API. A real emergency squawk is rare; `sudo zenithboard telegram test squawk send` shows its shape.
