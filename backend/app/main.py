"""
Blog Matrix Platform - FastAPI 主应用
"""
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api import api_router
from app.models import account, blog, task  # noqa: ensure models are loaded

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def monitor_task():
    """定时探活任务"""
    from app.services.monitor_service import run_monitor_cycle
    db = SessionLocal()
    try:
        await run_monitor_cycle(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表
    logger.info("🚀 Blog Matrix Platform 启动中...")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ 数据库表初始化完成")

    # 启动监控定时任务
    scheduler.add_job(
        monitor_task,
        "interval",
        seconds=settings.MONITOR_INTERVAL_SECONDS,
        id="monitor_cycle",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"✅ 监控定时任务启动，间隔 {settings.MONITOR_INTERVAL_SECONDS}s")

    yield

    # 关闭
    scheduler.shutdown(wait=False)
    logger.info("👋 Blog Matrix Platform 已停止")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## 企业级静态博客矩阵管理平台

### 功能
- 多 Cloudflare 账号池管理
- 博客自动化发布（反同质化构建）
- CNAME 配置引导
- 资产监控与飞书告警
- SEO 合规拦截

### 鉴权
所有接口（除 `/api/v1/auth/login`）均需 Bearer Token：
```
Authorization: Bearer <your_token>
```
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)

from app.api.routes.registrars import router as registrars_router
app.include_router(registrars_router, prefix="/api/v1")


@app.get("/health", tags=["系统"])
async def health():
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME
    }
