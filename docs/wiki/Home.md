# ZenithBoard

A Raspberry Pi that listens to the aircraft overhead and shows them on a tablet or a TV as a dot-matrix wall or an airport split-flap board. It can also feed what it hears to ADSB Exchange, FlightAware, Flightradar24 and Plane Finder, and collect ACARS messages.

Current version: **0.10.4** · Licence: **GPL-3.0-or-later** · [Repository](https://github.com/regis57/ZenithBoard)

## Installing it

Installation, the menus and every setting are in the [README](https://github.com/regis57/ZenithBoard#readme). This wiki does not repeat them. What it holds is the three things a README is a poor place for: where the project is going, what has really been proven, and how the software works inside.

## Where it is going

* **[Roadmap](Roadmap)** — what is being worked on now, what comes next, and what will never be built.
* **[Project status](Project-status)** — what runs on real hardware today, what is only unit-tested, and the field log.

## How it works

* **[Architecture](Architecture)** — the processes, the ports, the files, and who writes what.
* **[Configuration reference](Configuration-reference)** — every setting in `config.env`.
* **[Command reference](Command-reference)** — the whole `zenithboard` command, with examples.
* **[The wall](The-wall)** — the dot grid, the boxes, the two looks, the per-tablet links.

## Running it

* **[Routes, photos and data](Routes-photos-and-data)** — the outside services, the caches, and what happens when they are down.
* **[Reliability and diagnostics](Reliability-and-diagnostics)** — the watchdogs, the health screen, and how to read a bad night.
* **[Gain tuning](Gain-tuning)** — getting the dongle's gain right.

## Working on it

* **[Code tour](Code-tour)** — a map of the modules and the systemd units.
* **[Testing](Testing)** — the test suite and the two patterns it is built on.
* **[Release process](Release-process)** — versions, changelog, and how a change reaches a Pi.
* **[Contributing](Contributing)** — how to propose a change, and the house style.
