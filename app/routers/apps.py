from fastapi import APIRouter
from app.services import apps_svc

router = APIRouter()

@router.get("")
async def run():
    return await apps_svc.run()
