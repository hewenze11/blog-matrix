"""
构建任务队列管理器
- 全局 asyncio.Semaphore(1) 保证同一时刻只有 1 个博客在编译（防 OOM）
- 任务状态全程写入 build_tasks 表，供前端实时查看
- 提供队列位置信息，让运营人员知道自己在第几个
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.task import BuildTask, TaskStatus
from app.models.blog import Blog, BlogStatus
from app.models.account import CFAccount
from app.services import cf_service, build_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────
# 核心防 OOM 信号量：同时只允许 1 个编译任务执行
# 修改这里的数值可调整并发数（建议服务器内存 < 4G 保持为 1）
# ────────────────────────────────────────────────────────────────
BUILD_SEMAPHORE = asyncio.Semaphore(1)


def _make_db_session(db_url: str):
    engine = create_engine(db_url, pool_pre_ping=True)
    return sessionmaker(bind=engine)()


def _update_queue_positions(db: Session):
    """重新计算所有 pending 任务的排队位置"""
    pending_tasks = (
        db.query(BuildTask)
        .filter(BuildTask.status == TaskStatus.pending)
        .order_by(BuildTask.created_at)
        .all()
    )
    for i, task in enumerate(pending_tasks):
        task.queue_position = i + 1  # 1-indexed，表示"前面还有几个"
    db.commit()


async def enqueue_build(
    blog_id: str,
    blog_name: str,
    theme: str,
    db_url: str,
    content_markdown: str = None
) -> str:
    """
    将构建任务加入队列并异步执行
    返回 task_id
    """
    import uuid
    task_id = str(uuid.uuid4())

    # 创建任务记录
    db = _make_db_session(db_url)
    try:
        # 计算当前队列长度（pending + running）
        active_count = db.query(BuildTask).filter(
            BuildTask.status.in_([TaskStatus.pending, TaskStatus.running])
        ).count()

        task = BuildTask(
            id=task_id,
            blog_id=blog_id,
            blog_name=blog_name,
            theme=theme,
            status=TaskStatus.pending,
            queue_position=active_count + 1,
            log=f"任务已加入队列，前方有 {active_count} 个任务，请等待..."
        )
        db.add(task)
        db.commit()
        logger.info(f"任务入队: {task_id} blog={blog_name} 队列位置={active_count + 1}")
    finally:
        db.close()

    # 异步执行（不阻塞请求）
    asyncio.create_task(_run_build_with_queue(task_id, blog_id, db_url))

    return task_id


async def _run_build_with_queue(task_id: str, blog_id: str, db_url: str):
    """
    等待信号量，串行执行构建
    """
    logger.info(f"任务 {task_id} 等待信号量...")

    async with BUILD_SEMAPHORE:
        # 拿到信号量后，立即更新队列位置信息
        db = _make_db_session(db_url)
        try:
            task = db.query(BuildTask).filter(BuildTask.id == task_id).first()
            if not task:
                return
            task.status = TaskStatus.running
            task.queue_position = 0
            task.started_at = datetime.utcnow()
            task.log = "🔨 已获得构建令牌，开始编译..."
            db.commit()
            _update_queue_positions(db)
        finally:
            db.close()

        logger.info(f"任务 {task_id} 开始执行")
        await _execute_build(task_id, blog_id, db_url)

    # 释放信号量后，更新剩余 pending 任务的队列位置
    db = _make_db_session(db_url)
    try:
        _update_queue_positions(db)
    finally:
        db.close()

    logger.info(f"任务 {task_id} 完成，信号量已释放")


async def _execute_build(task_id: str, blog_id: str, db_url: str):
    """实际的构建逻辑（含 CF 部署）"""

    def _update_log(db, task, msg, status=None):
        task.log = msg
        if status:
            task.status = status
        if status in (TaskStatus.success, TaskStatus.failed):
            task.finished_at = datetime.utcnow()
        db.commit()

    db = _make_db_session(db_url)
    try:
        task = db.query(BuildTask).filter(BuildTask.id == task_id).first()
        blog = db.query(Blog).filter(Blog.id == blog_id).first()
        if not task or not blog:
            return

        account = db.query(CFAccount).filter(CFAccount.id == blog.cf_account_id).first()
        if not account:
            _update_log(db, task, "❌ CF账号不存在", TaskStatus.failed)
            blog.status = BlogStatus.error
            blog.build_log = "CF账号不存在"
            db.commit()
            return

        # Step 1: 构建静态包
        blog.status = BlogStatus.building
        blog.build_log = "构建静态包中..."
        _update_log(db, task, "📦 正在生成静态文件包（反同质化编译中）...")
        db.commit()

        try:
            zip_path, build_id = build_service.build_blog(
                blog_name=blog.name,
                domain=blog.custom_domain or f"{blog.slug}.pages.dev",
                theme=blog.theme.value,
                content_markdown=blog.content_markdown,
                blog_id=blog.id
            )
        except ValueError as e:
            _update_log(db, task, f"❌ SEO校验阻断: {e}", TaskStatus.failed)
            blog.status = BlogStatus.error
            blog.build_log = str(e)
            db.commit()
            return
        except Exception as e:
            _update_log(db, task, f"❌ 构建异常: {e}", TaskStatus.failed)
            blog.status = BlogStatus.error
            blog.build_log = str(e)
            db.commit()
            return

        # Step 2: 创建 CF Pages 项目
        blog.status = BlogStatus.deploying
        _update_log(db, task, f"✅ 静态包构建完成 (build:{build_id})，正在创建 CF Pages 项目...")
        db.commit()

        try:
            project_info = await cf_service.create_pages_project(
                account_id=account.account_id,
                api_token=account.api_token,
                project_name=blog.slug
            )
            blog.cf_project_name = project_info["project_name"]
            blog.pages_domain = project_info["pages_domain"]
            db.commit()
        except Exception as e:
            logger.warning(f"创建项目异常（可能已存在，继续上传）: {e}")
            blog.cf_project_name = blog.slug
            blog.pages_domain = f"{blog.slug}.pages.dev"
            db.commit()

        # Step 3: 上传静态包
        _update_log(db, task, f"🚀 正在上传静态包至 CF Pages ({blog.pages_domain})...")
        db.commit()

        try:
            deploy_result = await cf_service.upload_static_bundle(
                account_id=account.account_id,
                api_token=account.api_token,
                project_name=blog.cf_project_name,
                bundle_path=zip_path
            )
            _update_log(
                db, task,
                f"🎉 部署成功！deployment_id={deploy_result.get('deployment_id','N/A')} | 访问: https://{blog.pages_domain}",
                TaskStatus.success
            )
        except Exception as e:
            _update_log(db, task, f"❌ 上传失败: {e}", TaskStatus.failed)
            blog.status = BlogStatus.error
            blog.build_log = f"上传失败: {e}"
            build_service.cleanup_build(zip_path)
            db.commit()
            return

        build_service.cleanup_build(zip_path)

        # Step 4: 全部成功
        blog.status = BlogStatus.online
        blog.last_deployed_at = datetime.utcnow()
        blog.build_log = f"部署成功: {blog.pages_domain}"
        account.site_count = str(int(account.site_count or "0") + 1)
        db.commit()

    except Exception as e:
        logger.error(f"构建任务 {task_id} 意外崩溃: {e}", exc_info=True)
        try:
            task = db.query(BuildTask).filter(BuildTask.id == task_id).first()
            blog = db.query(Blog).filter(Blog.id == blog_id).first()
            if task:
                _update_log(db, task, f"💥 意外崩溃: {e}", TaskStatus.failed)
            if blog:
                blog.status = BlogStatus.error
                blog.build_log = f"意外崩溃: {e}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
