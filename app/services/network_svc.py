"""
Network service — WiFi networks, VPN, proxy configuration.
"""

from app.utils import adb_shell


async def run() -> dict:
    try:
        import asyncio
        results = await asyncio.gather(
            adb_shell("dumpsys wifi | grep -E 'mSSID|SSID|savedNetworks|configured' | head -40"),
            adb_shell("dumpsys connectivity | grep -E 'VPN|vpn' | head -20"),
            adb_shell("settings get global http_proxy"),
            adb_shell("dumpsys wifi | grep 'mWifiInfo'"),
            adb_shell("ip route"),
            adb_shell("dumpsys wifi | grep -i 'networkId\\|SSID\\|BSSID' | head -60"),
        )

        wifi_raw    = results[0]
        vpn_raw     = results[1]
        proxy       = results[2]
        wifi_info   = results[3]
        routes_raw  = results[4]
        networks_raw= results[5]

        # Parse saved WiFi networks
        saved_networks = _parse_wifi_networks(networks_raw)

        # Current connection
        current_wifi = None
        for line in wifi_info.split("\n"):
            if "SSID" in line and "mWifiInfo" in line:
                import re
                m = re.search(r'SSID: ([^,]+)', line)
                if m:
                    current_wifi = m.group(1).strip()

        # VPN check
        vpn_active = any(
            keyword in vpn_raw.lower()
            for keyword in ["vpn", "tun0", "connected"]
            if vpn_raw
        )

        # Proxy
        proxy_configured = bool(proxy and proxy not in ("null", ""))

        return {
            "saved_networks":     saved_networks,
            "saved_count":        len(saved_networks),
            "current_wifi":       current_wifi,
            "vpn_active":         vpn_active,
            "proxy_configured":   proxy_configured,
            "proxy_value":        proxy if proxy_configured else None,
        }

    except Exception as e:
        return {"error": str(e)}


def _parse_wifi_networks(raw: str) -> list[dict]:
    """Parse WiFi saved networks from dumpsys output."""
    networks = []
    seen = set()
    current = {}

    for line in raw.split("\n"):
        line = line.strip()
        if "SSID" in line and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                ssid = parts[1].strip().strip('"')
                if ssid and ssid not in seen and ssid != "<unknown ssid>":
                    seen.add(ssid)
                    # Check if it looks like an open network
                    is_open = "allowedKeyManagement" in raw and "NONE" in raw
                    networks.append({
                        "ssid": ssid,
                        "open": False,  # Hard to determine without more parsing
                    })

    return networks[:30]
