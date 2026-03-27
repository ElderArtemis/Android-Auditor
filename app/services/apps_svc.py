"""
Apps service — lists installed apps, their permissions and sideloaded APKs.
"""

import asyncio
from app.utils import adb_shell, DANGEROUS_PERMISSIONS, level_score

# Known system/trusted packages to exclude from suspicious list
TRUSTED_PACKAGES = {
    "com.google", "com.android", "com.samsung", "com.huawei",
    "com.xiaomi", "com.oneplus", "com.oppo", "com.vivo",
    "com.miui", "com.sec", "com.qualcomm",
}


async def run() -> dict:
    try:
        # Get all packages
        all_pkgs_raw    = await adb_shell("pm list packages -f")
        third_pkgs_raw  = await adb_shell("pm list packages -3")
        system_pkgs_raw = await adb_shell("pm list packages -s")

        # Parse package lists
        def parse_packages(raw: str) -> list[str]:
            pkgs = []
            for line in raw.strip().split("\n"):
                if "=" in line:
                    pkg = line.split("=")[-1].strip()
                    if pkg:
                        pkgs.append(pkg)
                elif line.startswith("package:"):
                    pkg = line.replace("package:", "").strip()
                    if pkg:
                        pkgs.append(pkg)
            return pkgs

        all_packages    = parse_packages(all_pkgs_raw)
        third_packages  = parse_packages(third_pkgs_raw)
        system_packages = parse_packages(system_pkgs_raw)

        # Find sideloaded APKs (not from Play Store)
        # APKs installed from unknown sources have path outside /data/app with no Play Store marker
        unknown_sources = []
        for line in all_pkgs_raw.strip().split("\n"):
            if "package:" not in line:
                continue
            parts = line.replace("package:", "").split("=")
            if len(parts) == 2:
                path, pkg = parts[0].strip(), parts[1].strip()
                if "/data/app" not in path and "/system" not in path and pkg in third_packages:
                    unknown_sources.append({"package": pkg, "path": path})

        # Analyze permissions for third party apps (limit to 30 for performance)
        apps_with_perms = []
        critical_perm_count = 0

        tasks = [_get_app_permissions(pkg) for pkg in third_packages[:30]]
        perm_results = await asyncio.gather(*tasks, return_exceptions=True)

        for pkg, result in zip(third_packages[:30], perm_results):
            if isinstance(result, Exception):
                continue
            dangerous = result.get("dangerous", [])
            if dangerous:
                max_level = max(dangerous, key=lambda p: level_score(p.get("level","low")))
                critical_perm_count += sum(1 for p in dangerous if p.get("level") == "critical")
                apps_with_perms.append({
                    "package":    pkg,
                    "name":       pkg.split(".")[-1].replace("_", " ").title(),
                    "dangerous":  dangerous,
                    "max_level":  max_level.get("level", "low"),
                    "perm_count": len(dangerous),
                })

        # Sort by risk
        apps_with_perms.sort(key=lambda x: level_score(x["max_level"]), reverse=True)

        return {
            "total_packages":          len(all_packages),
            "third_party_count":       len(third_packages),
            "system_count":            len(system_packages),
            "unknown_sources_count":   len(unknown_sources),
            "unknown_sources":         unknown_sources[:20],
            "critical_permission_count": critical_perm_count,
            "risky_apps":              apps_with_perms[:20],
            "total_risky":             len(apps_with_perms),
        }

    except Exception as e:
        return {"error": str(e)}


async def _get_app_permissions(package: str) -> dict:
    """Get dangerous permissions granted to a package."""
    raw = await adb_shell(f"dumpsys package {package} | grep 'granted=true'")
    dangerous = []
    for line in raw.split("\n"):
        line = line.strip()
        for perm, info in DANGEROUS_PERMISSIONS.items():
            if perm in line and "granted=true" in line:
                dangerous.append({
                    "permission": perm,
                    "label":      info["label"],
                    "level":      info["level"],
                })
    return {"dangerous": dangerous}
