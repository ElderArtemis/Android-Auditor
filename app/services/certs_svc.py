"""
Certificates service — lists user-installed CA certificates (MITM risk).
"""

from app.utils import adb_shell


async def run() -> dict:
    try:
        import asyncio

        # User-installed certs are in /data/misc/user/0/cacerts-added/
        user_certs_raw  = await adb_shell("ls /data/misc/user/0/cacerts-added/ 2>/dev/null || echo 'EMPTY'")
        # System certs
        system_certs_raw = await adb_shell("ls /system/etc/security/cacerts/ 2>/dev/null | wc -l")

        user_cert_files = []
        if user_certs_raw and user_certs_raw != "EMPTY" and "No such" not in user_certs_raw:
            user_cert_files = [f.strip() for f in user_certs_raw.split("\n") if f.strip()]

        # Try to get cert details for user certs
        cert_details = []
        for cert_file in user_cert_files[:10]:
            detail = await adb_shell(
                f"openssl x509 -in /data/misc/user/0/cacerts-added/{cert_file} "
                f"-noout -subject -issuer -dates 2>/dev/null"
            )
            if detail:
                cert_details.append({
                    "file":   cert_file,
                    "detail": detail[:200],
                })
            else:
                cert_details.append({"file": cert_file, "detail": None})

        try:
            system_count = int(system_certs_raw.strip())
        except Exception:
            system_count = 0

        return {
            "user_cert_count":  len(user_cert_files),
            "user_certs":       cert_details,
            "system_cert_count": system_count,
            "mitm_risk":        len(user_cert_files) > 0,
        }

    except Exception as e:
        return {"error": str(e)}
