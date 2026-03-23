from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.blog import Blog, BlogStatus

router = APIRouter(prefix="/monitor", tags=["监控"])


@router.get("/dashboard", summary="监控大盘数据")
async def get_dashboard(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    total = db.query(Blog).count()
    online = db.query(Blog).filter(Blog.status == BlogStatus.online).count()
    offline = db.query(Blog).filter(Blog.status == BlogStatus.offline).count()
    building = db.query(Blog).filter(Blog.status.in_([BlogStatus.building, BlogStatus.deploying])).count()
    error = db.query(Blog).filter(Blog.status == BlogStatus.error).count()

    return {
        "total": total,
        "online": online,
        "offline": offline,
        "building": building,
        "error": error,
        "checked_at": datetime.utcnow().isoformat()
    }


@router.get("/offline-sites", summary="获取离线站点列表")
async def get_offline_sites(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blogs = db.query(Blog).filter(
        Blog.status.in_([BlogStatus.offline, BlogStatus.error])
    ).all()
    return [
        {
            "id": b.id,
            "name": b.name,
            "domain": b.custom_domain or b.pages_domain,
            "status": b.status,
            "fail_count": b.fail_count,
            "last_checked_at": b.last_checked_at
        }
        for b in blogs
    ]


@router.post("/trigger-check", summary="手动触发一次全量探活")
async def trigger_check(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    from app.services.monitor_service import run_monitor_cycle
    import asyncio
    asyncio.create_task(run_monitor_cycle(db))
    return {"message": "探活任务已触发，结果将异步更新"}
