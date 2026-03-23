from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.task import BuildTask, TaskStatus
from app.services.queue_service import BUILD_SEMAPHORE
import asyncio

router = APIRouter(prefix="/tasks", tags=["任务队列"])


@router.get("", summary="获取任务队列列表")
async def list_tasks(
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    tasks = (
        db.query(BuildTask)
        .order_by(BuildTask.created_at.desc())
        .limit(limit)
        .all()
    )

    # 判断信号量状态（是否有任务正在运行）
    semaphore_locked = BUILD_SEMAPHORE._value == 0

    return {
        "semaphore_locked": semaphore_locked,
        "concurrency_limit": 1,
        "pending_count": sum(1 for t in tasks if t.status == TaskStatus.pending),
        "running_count": sum(1 for t in tasks if t.status == TaskStatus.running),
        "tasks": [
            {
                "id": t.id,
                "blog_id": t.blog_id,
                "blog_name": t.blog_name,
                "theme": t.theme,
                "status": t.status,
                "queue_position": t.queue_position,
                "log": t.log,
                "started_at": t.started_at,
                "finished_at": t.finished_at,
                "created_at": t.created_at,
                "duration_seconds": (
                    int((t.finished_at - t.started_at).total_seconds())
                    if t.finished_at and t.started_at else None
                )
            }
            for t in tasks
        ]
    }


@router.get("/stats", summary="队列统计（轻量级轮询用）")
async def queue_stats(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    from sqlalchemy import func
    counts = (
        db.query(BuildTask.status, func.count(BuildTask.id))
        .group_by(BuildTask.status)
        .all()
    )
    stats = {str(k): v for k, v in counts}
    return {
        "pending": stats.get("pending", 0),
        "running": stats.get("running", 0),
        "success": stats.get("success", 0),
        "failed": stats.get("failed", 0),
        "semaphore_available": BUILD_SEMAPHORE._value,
    }
