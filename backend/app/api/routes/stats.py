"""
统计数据接口
- POST /collect  (公开，博客页面 JS 上报)
- GET  /blogs/{blog_id}  (需登录，业务人员查询)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.stats import BlogEvent
from app.models.blog import Blog

router = APIRouter(prefix="/stats", tags=["统计监控"])


@router.post("/collect", summary="上报访问/点击事件（公开接口，供博客页面 JS 调用）")
async def collect_event(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        return {"ok": False}

    blog_id = body.get("blog_id", "")
    event_type = body.get("event", "pageview")
    device = body.get("device", "unknown")
    referrer = (body.get("referrer") or "")[:500]

    # 从 CF 头获取国家
    country = request.headers.get("CF-IPCountry") or request.headers.get("X-Country") or "unknown"

    # 验证 blog_id 存在
    if not db.query(Blog).filter(Blog.id == blog_id).first():
        return {"ok": False, "msg": "unknown blog"}

    event = BlogEvent(
        blog_id=blog_id,
        event_type=event_type,
        country=country[:10],
        device=device[:20],
        referrer=referrer,
    )
    db.add(event)
    db.commit()
    return {"ok": True}


@router.get("/blogs/{blog_id}", summary="查询博客统计数据")
async def get_blog_stats(
    blog_id: str,
    period: str = "30d",
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(404, "博客不存在")

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days = int(period.rstrip("d")) if period.endswith("d") else 30
    period_start = now - timedelta(days=days)

    def count(event_type=None, since=None):
        q = db.query(func.count(BlogEvent.id)).filter(BlogEvent.blog_id == blog_id)
        if event_type:
            q = q.filter(BlogEvent.event_type == event_type)
        if since:
            q = q.filter(BlogEvent.created_at >= since)
        return q.scalar() or 0

    total_views   = count("pageview")
    today_views   = count("pageview", today_start)
    period_views  = count("pageview", period_start)
    total_clicks  = count("click_apimart")
    today_clicks  = count("click_apimart", today_start)
    period_clicks = count("click_apimart", period_start)

    ctr = round(total_clicks / total_views * 100, 1) if total_views > 0 else 0

    # 国家分布 top5
    country_rows = (
        db.query(BlogEvent.country, func.count(BlogEvent.id).label("cnt"))
        .filter(BlogEvent.blog_id == blog_id, BlogEvent.event_type == "pageview")
        .group_by(BlogEvent.country)
        .order_by(text("cnt DESC"))
        .limit(5)
        .all()
    )

    # 设备分布
    device_rows = (
        db.query(BlogEvent.device, func.count(BlogEvent.id).label("cnt"))
        .filter(BlogEvent.blog_id == blog_id, BlogEvent.event_type == "pageview")
        .group_by(BlogEvent.device)
        .all()
    )
    total_d = sum(r.cnt for r in device_rows) or 1
    device_pct = {r.device: round(r.cnt / total_d * 100) for r in device_rows}

    # 每日趋势（最近 days 天）
    daily = []
    for i in range(days - 1, -1, -1):
        day = today_start - timedelta(days=i)
        day_end = day + timedelta(days=1)
        v = (
            db.query(func.count(BlogEvent.id))
            .filter(BlogEvent.blog_id == blog_id,
                    BlogEvent.event_type == "pageview",
                    BlogEvent.created_at >= day,
                    BlogEvent.created_at < day_end)
            .scalar() or 0
        )
        cl = (
            db.query(func.count(BlogEvent.id))
            .filter(BlogEvent.blog_id == blog_id,
                    BlogEvent.event_type == "click_apimart",
                    BlogEvent.created_at >= day,
                    BlogEvent.created_at < day_end)
            .scalar() or 0
        )
        daily.append({"date": day.strftime("%Y-%m-%d"), "views": v, "clicks": cl})

    # 来源分布 top5（referrer domain）
    referrer_rows = (
        db.query(BlogEvent.referrer, func.count(BlogEvent.id).label("cnt"))
        .filter(BlogEvent.blog_id == blog_id,
                BlogEvent.event_type == "pageview",
                BlogEvent.referrer != "",
                BlogEvent.referrer != None)
        .group_by(BlogEvent.referrer)
        .order_by(text("cnt DESC"))
        .limit(5)
        .all()
    )

    return {
        "blog_id": blog_id,
        "blog_name": blog.name,
        "summary": {
            "total_views": total_views,
            "today_views": today_views,
            f"views_{period}": period_views,
            "total_clicks": total_clicks,
            "today_clicks": today_clicks,
            f"clicks_{period}": period_clicks,
            "ctr_percent": ctr,
        },
        "top_countries": [{"country": r.country, "count": r.cnt} for r in country_rows],
        "device_breakdown": device_pct,
        "top_referrers": [{"referrer": r.referrer[:80], "count": r.cnt} for r in referrer_rows],
        "daily_trend": daily,
    }
