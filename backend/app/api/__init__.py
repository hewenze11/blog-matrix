from fastapi import APIRouter
from app.api.routes import auth, accounts, blogs, monitor, tasks

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(blogs.router)
api_router.include_router(monitor.router)
api_router.include_router(tasks.router)
