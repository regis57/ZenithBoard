# Hardware notes

## One dongle (ADS-B only)
Plug it in, run the installer, done. Use a 1090 MHz antenna placed as high and as clear as possible (window sill is fine to start, outdoors is far better). A filtered dongle (built-in 1090 MHz SAW filter) noticeably improves range in cities.

## Two dongles (ADS-B + ACARS)
Both dongles look identical to the Pi, so give each one a **unique serial number**, otherwise the wrong one may be picked after a reboot.

```bash
sudo apt install -y rtl-sdr
rtl_test -t                       # lists the dongles (index 0, 1, ...)
```
Plug in **only the ADS-B dongle**, then:
```bash
sudo rtl_eeprom -d 0 -s 00001090
```
Unplug it, plug in **only the ACARS dongle**, then:
```bash
sudo rtl_eeprom -d 0 -s 00000131
```
Unplug and re-plug **both**. Now enter `00001090` as the ADS-B dongle (menu 1) and `00000131` as the ACARS dongle (menu 3). (If a dongle refuses a serial change, use its index `0` / `1` instead.)

## Antennas
* ADS-B: 1090 MHz (λ/4 ≈ 6.9 cm). A cheap collinear or ground-plane antenna works well.
* ACARS: 131 MHz band (λ/4 ≈ 57 cm). A simple vertical wire or a telescopic whip at ~57 cm works to start. Do not share one antenna between the two.

## Power and USB
Use the official Pi power supply. Plug dongles into USB 2.0 ports (the blue USB 3 ports can radiate interference around 1 GHz). A short extension cable or powered hub helps keep the dongles away from the Pi.

## ACARS frequencies
Europe: `131.525 131.725 131.825` (default) · USA: `131.550 130.025 129.125`. A single dongle covers about 2 MHz of spectrum, so all frequencies must lie within that window.
