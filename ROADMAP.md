# Roadmap

## Present in v0.0.1 (prototype)
- whiptail installer (dump1090-fa, FR24, PiAware, ADSBx, Planefinder, ACARS packages)
- FastAPI backend reading `/run/dump1090-fa/aircraft.json`, radius filter, Planespotters photo
- Basic dot-matrix page (VT323 font)

## Known gaps (to fix next)
- [ ] Unit choice (metric/imperial) at install + change later (`/etc/zenithboard/config.env`, `sudo zenithboard-config`)
- [ ] readsb as primary decoder; dump1090-fa fallback; feeders adapted to both
- [ ] ADSB Exchange mandatory; single shared MLAT process
- [ ] Radius selector 1/2/5/10/15/30/50 (km or mi) in UI; lat/lon no longer patched by `sed` into code
- [ ] Safer uninstall (never purge the decoder silently)
- [ ] Pin tested package versions; arm64 Planefinder package (current URL is armhf)
- [ ] ACARS: real acarsdec → InfluxDB/Grafana pipeline, 7-day retention job
- [ ] Self-host the VT323 font (tablet may be offline from Google Fonts)
- [ ] Responsive wall for tablets, auto-refresh / wake-lock
- [ ] Do not run the web service as root
