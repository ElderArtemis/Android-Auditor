"""
POST /api/scan — Full device audit
"""

import asyncio
from fastapi import APIRouter
from app.utils import calculate_security_score
from app.services import device_svc, apps_svc, network_svc, certs_svc

router = APIRouter()

@router.post("")
async def full_scan():
    device_result, apps_result, network_result, certs_result = await asyncio.gather(
        device_svc.run(),
        apps_svc.run(),
        network_svc.run(),
        certs_svc.run(),
        return_exceptions=True,
    )

    def safe(r):
        return {"error": str(r)} if isinstance(r, Exception) else r

    device_r  = safe(device_result)
    apps_r    = safe(apps_result)
    network_r = safe(network_result)
    certs_r   = safe(certs_result)

    security = calculate_security_score(device_r, apps_r, network_r, certs_r)

    return {
        "security": security,
        "modules": {
            "device":  device_r,
            "apps":    apps_r,
            "network": network_r,
            "certs":   certs_r,
        }
    }

@router.get("/status")
async def adb_status():
    """Check ADB connection status."""
    from app.utils import find_adb, adb
    adb_bin = find_adb()
    if not adb_bin:
        return {"connected": False, "error": "ADB not found", "adb_path": None}

    stdout, stderr, rc = await adb(["devices"])
    lines = [l.strip() for l in stdout.strip().split("\n") if l.strip()]
    devices = [l for l in lines if "\t" in l and "offline" not in l and "unauthorized" not in l]
    unauthorized = [l for l in lines if "unauthorized" in l]
    offline = [l for l in lines if "offline" in l]

    return {
        "connected":    len(devices) > 0,
        "adb_path":     adb_bin,
        "devices":      devices,
        "unauthorized": unauthorized,
        "offline":      offline,
        "raw":          stdout,
    }
