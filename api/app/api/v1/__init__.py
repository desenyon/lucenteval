from fastapi import APIRouter

from .accounts import router as accounts_router
from .admin import router as admin_router
from .health import router as health_router
from .keys import router as keys_router
from .leaderboard import router as leaderboard_router
from .prompts import router as prompts_router
from .runs import router as runs_router
from .webhooks import router as webhooks_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(health_router)
api_router.include_router(accounts_router)
api_router.include_router(keys_router)
api_router.include_router(prompts_router)
api_router.include_router(runs_router)
api_router.include_router(webhooks_router)
api_router.include_router(leaderboard_router)
api_router.include_router(admin_router)
