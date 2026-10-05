# ZenithBoard — ADSB Flight Info

> Lean ADS-B feeder installer for Raspberry Pi 4+, plus a dot-matrix "what's flying over my head" wall for an old tablet.

**Status: v0.0.1 — early prototype.** See [ROADMAP.md](ROADMAP.md) for what is done and what is planned.

Inspired by [jprochazka/adsb-receiver](https://github.com/jprochazka/adsb-receiver). This is an independent, from-scratch project with a smaller scope (one decoder, one MLAT instance, one display), not a fork.

## Planned menu

1. **ADSB** — decoder (readsb preferred, dump1090-fa fallback) + feeders: ADSB Exchange (mandatory base layer), FlightAware, Flightradar24, Planefinder… sharing a **single** MLAT client.
2. **FlightInfo** — responsive dot-matrix wall; auto-cycles aircraft inside a chosen radius (1, 2, 5, 10, 15, 30, 50 km or miles).
3. **ACARS** *(optional)* — acarsdec → Grafana, filtered, rolling 7-day retention.

Units (metric / imperial) are chosen at first install and can be changed later.

---

This suite allows you to easily install an ADS-B receiver (dump1090-fa), interface it with various networks (FlightAware, FR24, ADSB Exchange, etc.), and deploy a "Dot Matrix" style display interface (FlightInfo) on a Raspberry Pi 4 or higher.

## Step 1: SD Card Preparation (Raspbian Lite & SSH)

If starting from scratch, here is how to prepare your Raspberry Pi 4 in "headless" mode (no screen or keyboard needed):

1. **Download Raspberry Pi Imager** from the official website: https://www.raspberrypi.com/software/
2. Insert your micro-SD card into your computer.
3. Launch Raspberry Pi Imager:
   - **Device:** Select *Raspberry Pi 4*.
   - **OS:** Go to *Raspberry Pi OS (Other)* and choose **Raspberry Pi OS Lite (64-bit)**.
   - **Storage:** Choose your micro-SD card.
4. **Advanced Configuration:** Click "Next", then select **EDIT SETTINGS** (or the gear icon) to apply custom settings.
   - Under **General**:
     - Check "Set hostname" (e.g., `flightinfo`).
     - Check "Set username and password" (e.g., user `pi` and a secure password).
     - Check "Configure wireless LAN" and enter your Wi-Fi credentials (if not using Ethernet).
     - Check "Set locale settings" (Timezone: `Europe/Paris`, Keyboard: `fr`).
   - Under **Services**:
     - **Check "Enable SSH"** (Use password authentication).
   - Save, click **YES**, and wait for writing/verification.
5. Insert the SD card into the Raspberry Pi 4, plug your SDR dongle into a USB port (USB 2.0 preferred to reduce interference), and power it on. Wait 2-3 minutes.

## Step 2: First SSH Connection

1. Find the Raspberry Pi's IP address on your local network (check your router's admin page or use an IP scanner).
2. Open a terminal on your computer.
3. Connect using:
   ```bash
   ssh pi@YOUR_IP_ADDRESS
   ```
4. Accept the security footprint (`yes`) and enter your password.

## Step 3: Installation & Management

Transfer this archive to the Raspberry Pi and run the installer. The script is dynamic: you can re-run it anytime to add or remove components by simply checking or unchecking them in the menu.

```bash
unzip adsb_flightinfo_suite.zip -d zenithboard
cd zenithboard
chmod +x install.sh
sudo ./install.sh
```
