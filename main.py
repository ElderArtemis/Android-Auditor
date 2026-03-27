"""
AndroidAuditor v1.0.0 — Mobile Security Audit Tool
FastAPI backend — uses ADB for device analysis
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn, os
from dotenv import load_dotenv

load_dotenv()

from app.routers import scan, device, apps, network, certs

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✦ AndroidAuditor v1.0.0 starting...")
    from app.utils import find_adb
    adb = find_adb()
    print(f"✦ ADB: {adb or 'NOT FOUND'}")
    yield
    print("✦ AndroidAuditor shutting down.")

app = FastAPI(title="AndroidAuditor", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(scan.router,    prefix="/api/scan",    tags=["scan"])
app.include_router(device.router,  prefix="/api/device",  tags=["device"])
app.include_router(apps.router,    prefix="/api/apps",    tags=["apps"])
app.include_router(network.router, prefix="/api/network", tags=["network"])
app.include_router(certs.router,   prefix="/api/certs",   tags=["certs"])

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health():
    from app.utils import find_adb
    return {"status": "online", "version": "1.0.0", "adb": find_adb() or "not found"}

if __name__ == "__main__":
    uvicorn.run("main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", 8000)),
        reload=os.getenv("DEBUG", "true").lower() == "true")
