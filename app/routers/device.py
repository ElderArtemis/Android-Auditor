from fastapi import APIRouter
from app.services import device_svc

router = APIRouter()

@router.get("")
async def run():
    return await device_svc.run()
