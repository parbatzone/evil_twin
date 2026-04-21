# 🚀 EvilTwin Auto-Pwn
### Automated Evil Twin Attack Script for Kali Linux

A streamlined Python script designed to automate the deployment of a Rogue Access Point. It handles interface configuration, process management, and deauthentication with minimal user input.

---

## 🛠️ Requirements
* **OS:** Kali Linux / Parrot OS
* **Hardware:** LB-LINK USB Adapter (or any adapter supporting monitor mode)
* **Interfaces:** `wlan1` (Monitor) and `wlan0` (Fake AP)

---

## 📖 How to Use

### Step 1: Deploy the Script
Save the script to your home directory: <br>
`cp eviltwin_auto.py ~/eviltwin_auto.py`

**Step 2: Set Permissions** <br>
Ensure the script is executable: <br>
`chmod +x ~/eviltwin_auto.py`

**Step 3: Hardware Check** <br>
Plug in your USB adapter and verify that `wlan1` is visible: <br>
`iwconfig`

**Step 4: Launch** <br>
Run the script with root privileges: <br>
`sudo python3 ~/eviltwin_auto.py`

---

## ⚡ Automated Features
The script simplifies the entire attack chain into a few automated steps:

* **Environment Cleanup:** Automatically kills interfering processes like `wpa_supplicant`.
* **Dual-Interface Setup:** Assigns `wlan1` to monitor mode and `wlan0` as the Fake AP.
* **Target Acquisition:** Launches an `airodump-ng` scan. Once you find your target, press `Ctrl+C` to move to configuration.
* **Quick Input:** Requires only 3 inputs: **SSID**, **BSSID**, and **Channel**.
* **Full Stack Deployment:**
    * Spawns a Fake AP with the target SSID.
    * Configures a DHCP server on `192.168.1.1`.
    * Initiates an infinite deauthentication loop to kick users off the legitimate router.
* **Auto-Restore:** Press `Ctrl+C` at any time to stop the attack, clean up processes, and restore network settings.

---

## 🛠️ Troubleshooting
If `hostapd` fails to start correctly, run the following commands to reset the service:

```bash
sudo systemctl stop hostapd
sudo python3 ~/eviltwin_auto.py
