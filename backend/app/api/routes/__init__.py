from fastapi import APIRouter
from app.api.routes.v1.routes import router as main_routers

router = APIRouter()

router.include_router(main_routers)
