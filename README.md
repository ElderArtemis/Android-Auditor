# AndroidAuditor v1.0.0

Mobile Security Audit Tool — uses ADB to audit Android devices.

## Requirements
- Android Studio (includes ADB)
- Python 3.13+
- Android device with USB Debugging enabled

## Setup
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open: http://localhost:8000

## Note
This tool runs locally only — no K8s deployment needed.
