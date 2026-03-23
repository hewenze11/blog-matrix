import asyncio
import random
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.blog import Blog, BlogStatus, ThemeType
from app.models.account import CFAccount, AccountStatus
from app.schemas import BlogCreate, BlogOut, CNAMEBindRequest
from app.services import cf_service, build_service
from app.services.queue_service import enqueue_build

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/blogs", tags=["博客管理"])


def _pick_account(db: Session, preferred_account_id: Optional[str] = None) -> CFAccount:
    """选择 CF 账号：优先使用指定账号，否则自动分配站点数最少的健康账号"""
    if preferred_account_id:
        account = db.query(CFAccount).filter(
            CFAccount.id == preferred_account_id,
            CFAccount.status == AccountStatus.active
        ).first()
        if not account:
            raise HTTPException(status_code=400, detail="指定的 CF 账号不存在或不可用")
        return account

    accounts = db.query(CFAccount).filter(CFAccount.status == AccountStatus.active).all()
    if not accounts:
        raise HTTPException(status_code=400, detail="没有可用的 CF 账号，请先添加账号")

    # 按站点数量排序，取最少的
    accounts.sort(key=lambda a: int(a.site_count or "0"))
    return accounts[0]


async def _deploy_pipeline(blog_id: str, db_url: str):
    """
    后台异步建站流水线：
    1. 构建静态包（反同质化）
    2. SEO 校验
    3. 创建 CF Pages 项目
    4. 上传静态包
    5. 更新数据库状态
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        blog = db.query(Blog).filter(Blog.id == blog_id).first()
        if not blog:
            logger.error(f"Blog {blog_id} 不存在")
            return

        account = db.query(CFAccount).filter(CFAccount.id == blog.cf_account_id).first()
        if not account:
            blog.status = BlogStatus.error
            blog.build_log = "CF账号不存在"
            db.commit()
            return

        # 1. 构建静态包
        blog.status = BlogStatus.building
        blog.build_log = "正在构建静态包..."
        db.commit()

        try:
            zip_path, build_id = build_service.build_blog(
                blog_name=blog.name,
                domain=blog.custom_domain or f"{blog.slug}.pages.dev",
                theme=blog.theme.value,
                content_markdown=None
            )
        except ValueError as e:
            blog.status = BlogStatus.error
            blog.build_log = f"SEO 校验阻断: {str(e)}"
            db.commit()
            return

        # 2. 创建 CF Pages 项目
        blog.status = BlogStatus.deploying
        blog.build_log = f"构建完成 (build:{build_id})，正在创建 CF Pages 项目..."
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
            # 项目可能已存在，尝试继续
            logger.warning(f"创建 CF Pages 项目异常（可能已存在）: {e}")
            blog.cf_project_name = blog.slug
            blog.pages_domain = f"{blog.slug}.pages.dev"
            db.commit()

        # 3. 上传静态包
        blog.build_log = f"正在上传静态包到 CF Pages..."
        db.commit()

        try:
            deploy_result = await cf_service.upload_static_bundle(
                account_id=account.account_id,
                api_token=account.api_token,
                project_name=blog.cf_project_name,
                bundle_path=zip_path
            )
            blog.build_log = f"部署成功。deployment_id={deploy_result.get('deployment_id','N/A')}"
        except Exception as e:
            blog.status = BlogStatus.error
            blog.build_log = f"上传失败: {str(e)}"
            db.commit()
            build_service.cleanup_build(zip_path)
            return

        build_service.cleanup_build(zip_path)

        # 4. 更新状态
        blog.status = BlogStatus.online
        blog.last_deployed_at = datetime.utcnow()
        # 更新账号站点数
        account.site_count = str(int(account.site_count or "0") + 1)
        db.commit()
        logger.info(f"博客 [{blog.name}] 部署完成: {blog.pages_domain}")

    except Exception as e:
        logger.error(f"建站流水线异常 blog_id={blog_id}: {e}")
        try:
            blog = db.query(Blog).filter(Blog.id == blog_id).first()
            if blog:
                blog.status = BlogStatus.error
                blog.build_log = f"流水线异常: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("", response_model=List[BlogOut], summary="获取博客列表")
async def list_blogs(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blogs = db.query(Blog).order_by(Blog.created_at.desc()).all()
    return blogs


@router.post("", response_model=BlogOut, summary="创建博客（触发建站流水线）")
async def create_blog(
    req: BlogCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    from slugify import slugify

    # 生成唯一 slug（项目名）
    base_slug = slugify(req.name, separator="-", lowercase=True)
    slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    # 选账号
    account = _pick_account(db, req.cf_account_id)

    blog = Blog(
        id=str(uuid.uuid4()),
        name=req.name,
        slug=slug,
        custom_domain=req.custom_domain,
        cf_account_id=account.id,
        theme=req.theme,
        status=BlogStatus.building,
        fail_count=0,
        build_log="等待队列调度..."
    )
    db.add(blog)
    db.commit()
    db.refresh(blog)

    # 通过任务队列（串行，防OOM）提交构建
    from app.core.config import settings
    task_id = await enqueue_build(
        blog_id=blog.id,
        blog_name=blog.name,
        theme=blog.theme.value,
        db_url=settings.DATABASE_URL
    )

    # 将 task_id 记录回 blog（方便前端追踪）
    blog.build_log = f"已加入队列，task_id={task_id}"
    db.commit()
    db.refresh(blog)

    return blog


@router.get("/{blog_id}", response_model=BlogOut, summary="获取博客详情")
async def get_blog(
    blog_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="博客不存在")
    return blog


@router.get("/{blog_id}/cname-info", summary="获取CNAME引导信息")
async def get_cname_info(
    blog_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="博客不存在")
    if not blog.pages_domain:
        raise HTTPException(status_code=400, detail="站点尚未部署完成，请稍后")
    return {
        "blog_name": blog.name,
        "pages_domain": blog.pages_domain,
        "custom_domain": blog.custom_domain,
        "cname_record": {
            "type": "CNAME",
            "host": "@",
            "value": blog.pages_domain
        },
        "cname_www_record": {
            "type": "CNAME",
            "host": "www",
            "value": blog.pages_domain
        },
        "guide_message": f"请前往您的域名服务商，添加以下 CNAME 解析记录，将 {blog.custom_domain} 指向 {blog.pages_domain}"
    }


@router.post("/{blog_id}/bind-domain", summary="确认CNAME已配置，执行域名绑定")
async def bind_domain(
    blog_id: str,
    req: CNAMEBindRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="博客不存在")
    if not blog.pages_domain or not blog.cf_project_name:
        raise HTTPException(status_code=400, detail="站点尚未部署完成")
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="请确认已完成 CNAME 配置")

    account = db.query(CFAccount).filter(CFAccount.id == blog.cf_account_id).first()
    if not account:
        raise HTTPException(status_code=400, detail="CF账号不存在")

    try:
        result = await cf_service.bind_custom_domain(
            account_id=account.account_id,
            api_token=account.api_token,
            project_name=blog.cf_project_name,
            domain=blog.custom_domain
        )
        return {
            "success": True,
            "message": f"域名 {blog.custom_domain} 绑定请求已提交，DNS 生效通常需要 5-10 分钟",
            "detail": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"域名绑定失败: {str(e)}")


@router.delete("/{blog_id}", summary="删除博客")
async def delete_blog(
    blog_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="博客不存在")
    db.delete(blog)
    db.commit()
    return {"message": "删除成功"}


@router.put("/{blog_id}", summary="更新博客内容并重新发布")
async def update_blog(
    blog_id: str,
    body: dict,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    blog = db.query(Blog).filter(Blog.id == blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="博客不存在")

    if "name" in body:
        blog.name = body["name"]
    if "theme" in body:
        try:
            blog.theme = ThemeType(body["theme"])
        except ValueError:
            raise HTTPException(400, f"无效主题: {body['theme']}")
    if "content_markdown" in body:
        blog.content_markdown = body["content_markdown"]

    blog.status = BlogStatus.building
    blog.build_log = "等待重新构建..."
    db.commit()

    from app.core.config import settings
    task_id = await enqueue_build(
        blog_id=blog.id,
        blog_name=blog.name,
        theme=blog.theme.value,
        db_url=settings.DATABASE_URL,
        content_markdown=body.get("content_markdown")
    )
    blog.build_log = f"已加入重建队列，task_id={task_id}"
    db.commit()
    db.refresh(blog)
    return {"id": str(blog.id), "status": "building", "message": "重新构建已触发", "task_id": task_id}

