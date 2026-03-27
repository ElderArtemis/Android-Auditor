"""
Device service — extracts device info via ADB shell commands.
"""

from app.utils import adb_shell


async def run() -> dict:
    try:
        # Run all commands in parallel
        import asyncio
        results = await asyncio.gather(
            adb_shell("getprop ro.product.model"),
            adb_shell("getprop ro.product.manufacturer"),
            adb_shell("getprop ro.build.version.release"),
            adb_shell("getprop ro.build.version.sdk"),
            adb_shell("getprop ro.build.version.security_patch"),
            adb_shell("getprop ro.build.fingerprint"),
            adb_shell("getprop ro.serialno"),
            adb_shell("getprop ro.product.brand"),
            adb_shell("settings get global development_settings_enabled"),
            adb_shell("settings get global adb_enabled"),
            adb_shell("getprop ro.crypto.state"),
            adb_shell("settings get secure screen_lock_timeout"),
            adb_shell("dumpsys deviceidle | grep mScreenOn"),
            adb_shell("settings get secure lockscreen.disabled"),
            adb_shell("getprop ro.build.type"),
            adb_shell("getprop ro.debuggable"),
            adb_shell("settings get global install_non_market_apps"),
            adb_shell("dumpsys battery | grep level"),
            adb_shell("getprop ro.product.cpu.abi"),
        )

        model        = results[0]
        manufacturer = results[1]
        android_ver  = results[2]
        sdk_ver      = results[3]
        sec_patch    = results[4]
        fingerprint  = results[5]
        serial       = results[6]
        brand        = results[7]
        dev_options  = results[8] == "1"
        adb_enabled  = results[9] == "1"
        crypto_state = results[10]
        lock_timeout = results[11]
        screen_on    = results[12]
        lock_disabled= results[13]
        build_type   = results[14]
        debuggable   = results[15]
        non_market   = results[16]
        battery_raw  = results[17]
        cpu_abi      = results[18]

        encrypted   = crypto_state in ("encrypted", "")
        screen_lock = lock_disabled != "1" and lock_timeout not in ("0", "-1", "")
        is_rooted   = await _check_root()

        # Battery level
        battery = None
        for line in battery_raw.split("\n"):
            if "level" in line:
                try: battery = int(line.split(":")[1].strip())
                except: pass

        return {
            "model":          f"{manufacturer} {model}".strip(),
            "manufacturer":   manufacturer,
            "brand":          brand,
            "android_version": android_ver,
            "sdk_version":    sdk_ver,
            "security_patch": sec_patch,
            "fingerprint":    fingerprint[:60] if fingerprint else None,
            "serial":         serial,
            "cpu_abi":        cpu_abi,
            "battery":        battery,
            "encrypted":      encrypted,
            "screen_lock":    screen_lock,
            "usb_debugging":  adb_enabled,
            "dev_options":    dev_options,
            "non_market_apps": non_market == "1",
            "build_type":     build_type,
            "debuggable":     debuggable == "1",
            "rooted":         is_rooted,
        }

    except Exception as e:
        return {"error": str(e)}


async def _check_root() -> bool:
    """Check if device is rooted."""
    try:
        # Try su command
        result = await adb_shell("su -c 'id' 2>/dev/null || which su 2>/dev/null")
        if "uid=0" in result or "/su" in result or "/sbin/su" in result:
            return True
        # Check for common root apps
        result2 = await adb_shell("pm list packages | grep -i 'magisk\\|supersu\\|kingroot'")
        return bool(result2.strip())
    except Exception:
        return False
