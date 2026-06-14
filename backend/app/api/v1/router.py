"""Top-level v1 API router."""

from fastapi import APIRouter

from app.api.v1 import agents, chat, readme, repos

api_router = APIRouter()
api_router.include_router(repos.router)
api_router.include_router(chat.router)
api_router.include_router(readme.router)
api_router.include_router(agents.router)

__all__ = ["api_router"]
