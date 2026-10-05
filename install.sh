#!/bin/bash
if [ "$EUID" -ne 0 ]; then
  echo "Please run this script as root (sudo ./install.sh)"
  exit
fi

# Detect current state to pre-fill the checklist and allow easy additions/removals
systemctl is-active --quiet dump1090-fa && S_DUMP="ON" || S_DUMP="OFF"
systemctl is-active --quiet flightinfo && S_INFO="ON" || S_INFO="OFF"
systemctl is-active --quiet fr24feed && S_FR24="ON" || S_FR24="OFF"
systemctl is-active --quiet piaware && S_FA="ON" || S_FA="OFF"
systemctl is-active --quiet adsbexchange-feed && S_ADSBX="ON" || S_ADSBX="OFF"
systemctl is-active --quiet pfclient && S_PF="ON" || S_PF="OFF"
systemctl is-active --quiet grafana-server && S_ACARS="ON" || S_ACARS="OFF"

LAT=$(whiptail --inputbox "Enter your Latitude" 8 39 "49.246" --title "GPS Configuration" 3>&1 1>&2 2>&3)
LON=$(whiptail --inputbox "Enter your Longitude" 8 39 "6.223" --title "GPS Configuration" 3>&1 1>&2 2>&3)

CHOICES=$(whiptail --title "ADSB FlightInfo - Component Manager" --checklist \
"Select components to install. Unchecking a previously installed component will REMOVE or DISABLE it.\nNOTE: ACARS requires a 2nd SDR dongle (131 MHz)." 20 78 8 \
"DUMP1090" "Base ADS-B Decoder (Required)" $S_DUMP \
"FLIGHTINFO" "Dot Matrix Web Dashboard" $S_INFO \
"ACARS" "ACARS Decoding + Grafana" $S_ACARS \
"FR24" "FlightRadar24 Feeder" $S_FR24 \
"FLIGHTAWARE" "FlightAware Feeder (PiAware)" $S_FA \
"ADSBX" "ADSB Exchange Feeder" $S_ADSBX \
"PLANEFINDER" "PlaneFinder Feeder" $S_PF 3>&1 1>&2 2>&3)

if [ $? -ne 0 ]; then
    echo "Installation cancelled."
    exit 0
fi

apt-get update

# DUMP1090
if [[ $CHOICES == *"DUMP1090"* ]]; then
    echo "=== Installing/Updating dump1090-fa ==="
    wget -q https://flightaware.com/adsb/piaware/files/packages/pool/piaware/p/piaware-support/piaware-repository_9.0.1_all.deb
    dpkg -i piaware-repository_9.0.1_all.deb
    apt-get update
    apt-get install -y dump1090-fa
    sed -i "s/RECEIVER_OPTIONS=\".*\"/RECEIVER_OPTIONS=\"--lat $LAT --lon $LON \"/" /etc/default/dump1090-fa
    systemctl enable --now dump1090-fa
    systemctl restart dump1090-fa
else
    echo "=== Removing dump1090-fa ==="
    apt-get purge -y dump1090-fa
fi

# FLIGHTINFO
if [[ $CHOICES == *"FLIGHTINFO"* ]]; then
    echo "=== Installing/Updating FlightInfo ==="
    apt-get install -y python3-pip python3-venv
    systemctl stop flightinfo 2>/dev/null
    rm -rf /opt/flightinfo
    cp -r $(pwd)/flightinfo /opt/flightinfo
    cd /opt/flightinfo
    python3 -m venv venv
    ./venv/bin/pip install -r requirements.txt
    
    cat << 'EOF' > /etc/systemd/system/flightinfo.service
[Unit]
Description=FlightInfo API & Web Server
After=network.target dump1090-fa.service

[Service]
User=root
WorkingDirectory=/opt/flightinfo
Environment="PATH=/opt/flightinfo/venv/bin"
ExecStart=/opt/flightinfo/venv/bin/uvicorn backend:app --host 0.0.0.0 --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    
    sed -i "s/LAT_DEFAULT = 49.0/LAT_DEFAULT = $LAT/" /opt/flightinfo/backend.py
    sed -i "s/LON_DEFAULT = 6.0/LON_DEFAULT = $LON/" /opt/flightinfo/backend.py
    
    systemctl daemon-reload
    systemctl enable --now flightinfo
else
    echo "=== Removing FlightInfo ==="
    systemctl disable --now flightinfo 2>/dev/null
    rm -rf /opt/flightinfo
    rm -f /etc/systemd/system/flightinfo.service
    systemctl daemon-reload
fi

# FR24
if [[ $CHOICES == *"FR24"* ]]; then 
    echo "=== Installing FR24 ==="
    bash -c "$(wget -O - https://repo-feed.flightradar24.com/install_fr24_rpi.sh)"
else
    echo "=== Disabling FR24 ==="
    systemctl disable --now fr24feed 2>/dev/null
    apt-get remove -y fr24feed 2>/dev/null
fi

# FLIGHTAWARE
if [[ $CHOICES == *"FLIGHTAWARE"* ]]; then 
    echo "=== Installing FlightAware ==="
    apt-get install -y piaware
    piaware-config allow-auto-updates yes
    systemctl enable --now piaware
else
    echo "=== Disabling FlightAware ==="
    systemctl disable --now piaware 2>/dev/null
    apt-get remove -y piaware 2>/dev/null
fi

# ADSBX
if [[ $CHOICES == *"ADSBX"* ]]; then 
    echo "=== Installing ADSB Exchange ==="
    curl -L -o /tmp/axsetup.sh https://adsbexchange.com/feed.sh
    sudo bash /tmp/axsetup.sh
else
    echo "=== Disabling ADSB Exchange ==="
    systemctl disable --now adsbexchange-feed 2>/dev/null
fi

# PLANEFINDER
if [[ $CHOICES == *"PLANEFINDER"* ]]; then 
    echo "=== Installing PlaneFinder ==="
    wget -q http://client.planefinder.net/pfclient_5.0.162_armhf.deb
    dpkg -i pfclient_5.0.162_armhf.deb
    systemctl enable --now pfclient
else
    echo "=== Disabling PlaneFinder ==="
    systemctl disable --now pfclient 2>/dev/null
    apt-get remove -y pfclient 2>/dev/null
fi

# ACARS
if [[ $CHOICES == *"ACARS"* ]]; then 
    echo "=== Installing ACARS Stack ==="
    apt-get install -y acarsdec influxdb grafana
    systemctl enable --now influxdb grafana-server
else
    echo "=== Disabling ACARS Stack ==="
    systemctl disable --now acarsdec influxdb grafana-server 2>/dev/null
fi

echo "=== INSTALLATION COMPLETE ==="
if [[ $CHOICES == *"FLIGHTINFO"* ]]; then
    echo "Access FlightInfo at http://$(hostname -I | awk '{print $1}'):8080"
fi
