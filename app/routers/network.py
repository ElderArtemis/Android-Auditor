from fastapi import APIRouter
from app.services import network_svc

router = APIRouter()

@router.get("")
async def run():
    return await network_svc.run()
