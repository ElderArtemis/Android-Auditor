from fastapi import APIRouter
from app.services import certs_svc

router = APIRouter()

@router.get("")
async def run():
    return await certs_svc.run()
