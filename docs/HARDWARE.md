# Hardware notes

## One dongle (ADS-B only)
Plug it in, run the installer, done. Use a 1090 MHz antenna placed as high and as clear as possible (window sill is fine to start, outdoors is far better). A filtered dongle (built-in 1090 MHz SAW filter) noticeably improves range in cities.

## Two dongles (ADS-B + 978 MHz UAT, United States)

Both dongles look identical to the Pi, so give each one a **unique serial number**, otherwise the wrong one may be picked after a reboot.

```bash
sudo apt install -y rtl-sdr
rtl_test -t                       # lists the dongles (index 0, 1, ...)
```
Plug in **only the ADS-B dongle**, then `sudo rtl_eeprom -d 0 -s 00001090`; unplug it, plug in **only the UAT dongle**, then `sudo rtl_eeprom -d 0 -s 00000978`. Unplug and re-plug **both**, and enter `00001090` as the ADS-B dongle (menu 1) and `00000978` as the UAT dongle. 978 MHz UAT ideally gets its own 978 MHz antenna.

## Antennas
* ADS-B: 1090 MHz (λ/4 ≈ 6.9 cm). A cheap collinear or ground-plane antenna works well.
* UAT: 978 MHz (λ/4 ≈ 7.7 cm), its own antenna for real range.

## Power and USB
Use the official Pi power supply. Plug dongles into USB 2.0 ports (the blue USB 3 ports can radiate interference around 1 GHz). A short extension cable or powered hub helps keep the dongles away from the Pi.

ACARS (a second dongle at 131 MHz) was part of ZenithBoard until 0.29.0 and left it in 0.30.0.
