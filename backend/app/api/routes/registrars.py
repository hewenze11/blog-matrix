"""域名注册商账号管理 + 域名注册 API 路由"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.crypto import encrypt, decrypt
from app.core.config import settings
from app.models.registrar import (
    RegistrarAccount,
    RegistrarStatus,
    RegistrarProvider,
    Domain,
    DomainStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["域名管理"])


# ─────────────────────── Pydantic Models ───────────────────────

class RegistrarAccountCreate(BaseModel):
    name: str
    provider: RegistrarProvider
    secret_id: str
    secret_key: str


class RegistrarAccountOut(BaseModel):
    id: str
    name: str
    provider: RegistrarProvider
    status: RegistrarStatus
    domain_count: int
    last_verified_at: Optional[datetime]
    secret_id_masked: str

    class Config:
        from_attributes = True


class DomainCheckRequest(BaseModel):
    domain: str
    registrar_account_id: str


class DomainRegisterRequest(BaseModel):
    domain_name: str
    registrar_account_id: str
    blog_id: Optional[str] = None


class DomainBindBlogRequest(BaseModel):
    blog_id: str


class DomainOut(BaseModel):
    id: str
    domain_name: str
    registrar_account_id: str
    blog_id: Optional[str]
    status: DomainStatus
    cf_pages_target: Optional[str]
    registrar_order_id: Optional[str]
    expire_at: Optional[datetime]
    error_msg: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─────────────────────── Helpers ───────────────────────

def _mask_secret(secret: str) -> str:
    """脱敏：显示前4位 + ***"""
    if not secret:
        return "****"
    try:
        plain = decrypt(secret)
    except Exception:
        plain = secret
    if len(plain) <= 4:
        return plain + "***"
    return plain[:4] + "***"


def _registrar_to_out(r: RegistrarAccount) -> RegistrarAccountOut:
    return RegistrarAccountOut(
        id=r.id,
        name=r.name,
        provider=r.provider,
        status=r.status,
        domain_count=r.domain_count,
        last_verified_at=r.last_verified_at,
        secret_id_masked=_mask_secret(r.secret_id),
    )


async def _get_svc(provider: RegistrarProvider):
    if provider == RegistrarProvider.tencent:
        from app.services import tencent_domain_service as svc
    else:
        from app.services import aliyun_domain_service as svc
    return svc


# ─────────────────────── Registrar Endpoints ───────────────────────

@router.get("/registrars", response_model=List[RegistrarAccountOut], summary="列出所有注册商账号")
async def list_registrars(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    rows = db.query(RegistrarAccount).order_by(RegistrarAccount.created_at.desc()).all()
    return [_registrar_to_out(r) for r in rows]


@router.post("/registrars", response_model=RegistrarAccountOut, status_code=status.HTTP_201_CREATED, summary="新增注册商账号")
async def create_registrar(
    body: RegistrarAccountCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    ra = RegistrarAccount(
        name=body.name,
        provider=body.provider,
        secret_id=encrypt(body.secret_id),
        secret_key=encrypt(body.secret_key),
    )
    db.add(ra)
    db.commit()
    db.refresh(ra)
    return _registrar_to_out(ra)


@router.post("/registrars/{registrar_id}/verify", summary="验证注册商凭证")
async def verify_registrar(
    registrar_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    ra = db.query(RegistrarAccount).filter(RegistrarAccount.id == registrar_id).first()
    if not ra:
        raise HTTPException(status_code=404, detail="注册商账号不存在")
    svc = await _get_svc(ra.provider)
    secret_id = decrypt(ra.secret_id)
    secret_key = decrypt(ra.secret_key)
    ok = await svc.verify_credentials(secret_id, secret_key)
    ra.status = RegistrarStatus.active if ok else RegistrarStatus.error
    ra.last_verified_at = datetime.utcnow()
    db.commit()
    return {"valid": ok, "status": ra.status}


@router.delete("/registrars/{registrar_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除注册商账号")
async def delete_registrar(
    registrar_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    ra = db.query(RegistrarAccount).filter(RegistrarAccount.id == registrar_id).first()
    if not ra:
        raise HTTPException(status_code=404, detail="注册商账号不存在")
    db.delete(ra)
    db.commit()


# ─────────────────────── Domain Endpoints ───────────────────────

@router.get("/domains", response_model=List[DomainOut], summary="列出所有域名")
async def list_domains(
    blog_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Domain)
    if blog_id:
        q = q.filter(Domain.blog_id == blog_id)
    return q.order_by(Domain.created_at.desc()).all()


@router.post("/domains/check", summary="查询域名是否可购买")
async def check_domain(
    body: DomainCheckRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    ra = db.query(RegistrarAccount).filter(RegistrarAccount.id == body.registrar_account_id).first()
    if not ra:
        raise HTTPException(status_code=404, detail="注册商账号不存在")
    svc = await _get_svc(ra.provider)
    secret_id = decrypt(ra.secret_id)
    secret_key = decrypt(ra.secret_key)
    result = await svc.check_domain_available(secret_id, secret_key, body.domain)
    return result


@router.post("/domains/register", response_model=DomainOut, status_code=status.HTTP_201_CREATED, summary="发起域名注册")
async def register_domain(
    body: DomainRegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    # 检查注册商
    ra = db.query(RegistrarAccount).filter(RegistrarAccount.id == body.registrar_account_id).first()
    if not ra:
        raise HTTPException(status_code=404, detail="注册商账号不存在")

    # 检查域名是否已存在
    existing = db.query(Domain).filter(Domain.domain_name == body.domain_name).first()
    if existing:
        raise HTTPException(status_code=409, detail="域名已存在")

    # 获取 blog 的 pages_domain 作为 cf_pages_target
    cf_pages_target = None
    if body.blog_id:
        from app.models.blog import Blog
        blog = db.query(Blog).filter(Blog.id == body.blog_id).first()
        if blog and blog.pages_domain:
            cf_pages_target = blog.pages_domain

    # 调用注册商 API 发起注册
    svc = await _get_svc(ra.provider)
    secret_id = decrypt(ra.secret_id)
    secret_key = decrypt(ra.secret_key)
    try:
        order_id = await svc.register_domain(secret_id, secret_key, body.domain_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 写入数据库
    domain = Domain(
        domain_name=body.domain_name,
        registrar_account_id=body.registrar_account_id,
        blog_id=body.blog_id,
        status=DomainStatus.registering,
        cf_pages_target=cf_pages_target,
        registrar_order_id=order_id,
    )
    db.add(domain)
    # 更新注册商域名计数
    ra.domain_count = (ra.domain_count or 0) + 1
    db.commit()
    db.refresh(domain)

    # 如果提供了 blog_id，启动后台流水线
    if body.blog_id and cf_pages_target:
        from app.services.domain_pipeline_service import run_domain_pipeline
        db_url = str(settings.DATABASE_URL)
        background_tasks.add_task(run_domain_pipeline, domain.id, cf_pages_target, db_url)

    return domain


@router.get("/domains/{domain_id}", response_model=DomainOut, summary="查询单个域名详情")
async def get_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    return domain


@router.post("/domains/{domain_id}/bind-blog", response_model=DomainOut, summary="绑定博客并触发流水线")
async def bind_blog(
    domain_id: str,
    body: DomainBindBlogRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")

    from app.models.blog import Blog
    blog = db.query(Blog).filter(Blog.id == body.blog_id).first()
    if not blog:
        raise HTTPException(status_code=404, detail="博客不存在")

    cf_pages_target = blog.pages_domain or ""
    domain.blog_id = body.blog_id
    domain.cf_pages_target = cf_pages_target
    db.commit()
    db.refresh(domain)

    if cf_pages_target:
        from app.services.domain_pipeline_service import run_domain_pipeline
        db_url = str(settings.DATABASE_URL)
        background_tasks.add_task(run_domain_pipeline, domain.id, cf_pages_target, db_url)

    return domain


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除域名记录")
async def delete_domain(
    domain_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="域名不存在")
    db.delete(domain)
    db.commit()
