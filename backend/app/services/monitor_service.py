"""
探活监控服务
异步定时检查所有 online 博客的存活状态
连续 3 次失败触发飞书告警
"""
import asyncio
import httpx
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.blog import Blog, BlogStatus
from app.services.feishu_service import send_offline_alert
from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_single_blog(blog: Blog) -> tuple[bool, int]:
    """
    检测单个博客存活
    返回 (is_online, status_code)
    """
    url = f"https://{blog.custom_domain or blog.pages_domain}"
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            is_online = resp.status_code in range(200, 400)
            return is_online, resp.status_code
    except Exception as e:
        logger.warning(f"探活失败 [{blog.name}] {url}: {e}")
        return False, 0


async def run_monitor_cycle(db: Session):
    """
    执行一轮监控
    """
    blogs = db.query(Blog).filter(
        Blog.status.in_([BlogStatus.online, BlogStatus.offline])
    ).all()

    if not blogs:
        return

    tasks = [check_single_blog(b) for b in blogs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for blog, result in zip(blogs, results):
        if isinstance(result, Exception):
            is_online, code = False, 0
        else:
            is_online, code = result

        blog.last_checked_at = datetime.utcnow()

        if is_online:
            blog.fail_count = 0
            if blog.status == BlogStatus.offline:
                blog.status = BlogStatus.online
                logger.info(f"站点恢复上线: {blog.name}")
        else:
            blog.fail_count = (blog.fail_count or 0) + 1
            logger.warning(f"站点探活失败 [{blog.name}] fail_count={blog.fail_count} code={code}")

            if blog.fail_count >= settings.MONITOR_FAIL_THRESHOLD:
                if blog.status != BlogStatus.offline:
                    blog.status = BlogStatus.offline
                    domain = blog.custom_domain or blog.pages_domain or "unknown"
                    asyncio.create_task(
                        send_offline_alert(
                            settings.FEISHU_WEBHOOK_URL,
                            blog.name,
                            domain,
                            blog.fail_count
                        )
                    )

    db.commit()
    logger.info(f"监控轮次完成，共检查 {len(blogs)} 个站点")
