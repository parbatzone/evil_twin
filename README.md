## How to use it:

Step 1 — Download/copy the script to your Kali
Save it anywhere, example:
bashcp eviltwin_auto.py ~/eviltwin_auto.py
Step 2 — Give it execute permission
bashchmod +x ~/eviltwin_auto.py
Step 3 — Plug in your LB-LINK USB adapter (wlan1 must show in iwconfig)
Step 4 — Run it as root
bashsudo python3 ~/eviltwin_auto.py

What It Does Automatically

Kills interfering processes (wpa_supplicant etc)
Detects your 2 interfaces — assigns wlan1 as monitor, wlan0 as fake AP
Starts airodump scan — you see all networks live
You press Ctrl+C when you spot your target
You enter SSID, BSSID, channel — 3 inputs only
Launches everything automatically:

Fake AP with same SSID as your router
DHCP server on 192.168.1.1
Infinite deauth blocking the real router


Press Ctrl+C to stop — it cleans everything up and restores internet


If hostapd fails
bashsudo systemctl stop hostapd
sudo python3 ~/eviltwin_auto.py
