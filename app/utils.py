"""
ADB utility wrapper — finds ADB and executes commands asynchronously.
"""

import os
import asyncio
import subprocess
from pathlib import Path

# Known ADB locations on Windows with Android Studio
ADB_CANDIDATES = [
    os.getenv("ADB_PATH", ""),
    r"C:\Users\{user}\AppData\Local\Android\Sdk\platform-tools\adb.exe",
    r"C:\Android\Sdk\platform-tools\adb.exe",
    r"C:\Program Files\Android\android-sdk\platform-tools\adb.exe",
    "adb",  # If in PATH
    "adb.exe",
]

_adb_path: str | None = None


def find_adb() -> str | None:
    global _adb_path
    if _adb_path:
        return _adb_path

    user = os.environ.get("USERNAME", os.environ.get("USER", ""))

    for candidate in ADB_CANDIDATES:
        if not candidate:
            continue
        # Expand {user} placeholder
        candidate = candidate.replace("{user}", user)

        try:
            result = subprocess.run(
                [candidate, "version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                _adb_path = candidate
                return _adb_path
        except Exception:
            continue

    return None


async def adb(args: list[str], timeout: int = 30) -> tuple[str, str, int]:
    """Run an ADB command asynchronously. Returns (stdout, stderr, returncode)."""
    adb_bin = find_adb()
    if not adb_bin:
        return "", "ADB not found. Please install Android SDK platform-tools.", 1

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                [adb_bin] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"ADB command timed out after {timeout}s", 1
    except Exception as e:
        return "", str(e), 1


async def adb_shell(cmd: str, timeout: int = 30) -> str:
    """Run adb shell command and return stdout."""
    stdout, stderr, rc = await adb(["shell", cmd], timeout=timeout)
    return stdout.strip()


# Dangerous Android permissions
DANGEROUS_PERMISSIONS = {
    "android.permission.READ_CONTACTS":          {"level": "high",     "label": "Read Contacts"},
    "android.permission.WRITE_CONTACTS":         {"level": "high",     "label": "Write Contacts"},
    "android.permission.READ_CALL_LOG":          {"level": "critical", "label": "Read Call Log"},
    "android.permission.WRITE_CALL_LOG":         {"level": "critical", "label": "Write Call Log"},
    "android.permission.PROCESS_OUTGOING_CALLS": {"level": "critical", "label": "Intercept Calls"},
    "android.permission.READ_SMS":               {"level": "critical", "label": "Read SMS"},
    "android.permission.SEND_SMS":               {"level": "critical", "label": "Send SMS"},
    "android.permission.RECEIVE_SMS":            {"level": "critical", "label": "Receive SMS"},
    "android.permission.ACCESS_FINE_LOCATION":   {"level": "high",     "label": "GPS Location"},
    "android.permission.ACCESS_COARSE_LOCATION": {"level": "medium",   "label": "Network Location"},
    "android.permission.ACCESS_BACKGROUND_LOCATION": {"level": "critical", "label": "Background Location"},
    "android.permission.CAMERA":                 {"level": "high",     "label": "Camera"},
    "android.permission.RECORD_AUDIO":           {"level": "high",     "label": "Microphone"},
    "android.permission.READ_EXTERNAL_STORAGE":  {"level": "medium",   "label": "Read Storage"},
    "android.permission.WRITE_EXTERNAL_STORAGE": {"level": "medium",   "label": "Write Storage"},
    "android.permission.READ_PHONE_STATE":       {"level": "high",     "label": "Phone State/IMEI"},
    "android.permission.CALL_PHONE":             {"level": "high",     "label": "Make Calls"},
    "android.permission.USE_BIOMETRIC":          {"level": "high",     "label": "Biometric"},
    "android.permission.USE_FINGERPRINT":        {"level": "high",     "label": "Fingerprint"},
    "android.permission.GET_ACCOUNTS":           {"level": "medium",   "label": "Get Accounts"},
    "android.permission.MANAGE_ACCOUNTS":        {"level": "high",     "label": "Manage Accounts"},
    "android.permission.READ_SYNC_SETTINGS":     {"level": "low",      "label": "Sync Settings"},
    "android.permission.BLUETOOTH":              {"level": "low",      "label": "Bluetooth"},
    "android.permission.BLUETOOTH_SCAN":         {"level": "medium",   "label": "Bluetooth Scan"},
    "android.permission.BLUETOOTH_CONNECT":      {"level": "medium",   "label": "Bluetooth Connect"},
    "android.permission.BODY_SENSORS":           {"level": "medium",   "label": "Body Sensors"},
    "android.permission.ACTIVITY_RECOGNITION":   {"level": "medium",   "label": "Activity Recognition"},
    "android.permission.NEARBY_WIFI_DEVICES":    {"level": "medium",   "label": "Nearby WiFi"},
}

def level_score(level: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(level, 0)

def calculate_security_score(device: dict, apps_data: dict, network: dict, certs: dict) -> dict:
    score = 100
    findings = []

    # Device checks
    patch = device.get("security_patch", "")
    if patch:
        from datetime import datetime
        try:
            patch_date = datetime.strptime(patch, "%Y-%m-%d")
            days_old = (datetime.now() - patch_date).days
            if days_old > 365:
                score -= 20
                findings.append({"label": f"Security patch {days_old}d old", "level": "critical"})
            elif days_old > 180:
                score -= 10
                findings.append({"label": f"Security patch {days_old}d old", "level": "high"})
            elif days_old > 90:
                score -= 5
                findings.append({"label": f"Security patch outdated", "level": "medium"})
        except Exception:
            pass

    if device.get("usb_debugging"):
        score -= 15
        findings.append({"label": "USB debugging enabled", "level": "high"})

    if device.get("dev_options"):
        score -= 10
        findings.append({"label": "Developer options enabled", "level": "medium"})

    if not device.get("encrypted"):
        score -= 20
        findings.append({"label": "Device not encrypted", "level": "critical"})

    if not device.get("screen_lock"):
        score -= 15
        findings.append({"label": "No screen lock", "level": "critical"})

    # Apps checks
    unknown_apks = apps_data.get("unknown_sources_count", 0)
    if unknown_apks > 0:
        score -= min(20, unknown_apks * 5)
        findings.append({"label": f"{unknown_apks} sideloaded APKs", "level": "high"})

    critical_perms = apps_data.get("critical_permission_count", 0)
    if critical_perms > 5:
        score -= 10
        findings.append({"label": f"{critical_perms} critical permissions granted", "level": "high"})

    # Certs
    user_certs = certs.get("user_cert_count", 0)
    if user_certs > 0:
        score -= user_certs * 10
        findings.append({"label": f"{user_certs} user-installed CA cert(s)", "level": "critical"})

    score = max(0, min(100, score))
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C" if score >= 60 else "D" if score >= 50 else "F"

    return {"score": score, "grade": grade, "findings": findings}