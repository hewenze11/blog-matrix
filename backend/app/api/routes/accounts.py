from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.account import CFAccount, AccountStatus
from app.schemas import CFAccountCreate, CFAccountOut
from app.services import cf_service
import uuid

router = APIRouter(prefix="/accounts", tags=["CF账号池"])


@router.get("", response_model=List[CFAccountOut], summary="获取所有CF账号")
async def list_accounts(
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    accounts = db.query(CFAccount).order_by(CFAccount.created_at.desc()).all()
    return accounts


@router.post("", response_model=CFAccountOut, summary="添加CF账号")
async def add_account(
    req: CFAccountCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    # 验证 Token
    is_valid = await cf_service.verify_token(req.api_token)
    if not is_valid:
        raise HTTPException(status_code=400, detail="CF API Token 无效，请检查后重试")

    # 检查是否已存在
    existing = db.query(CFAccount).filter(CFAccount.account_id == req.account_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="该 Account ID 已存在")

    from datetime import datetime
    account = CFAccount(
        id=str(uuid.uuid4()),
        name=req.name,
        account_id=req.account_id,
        api_token=req.api_token,
        status=AccountStatus.active,
        site_count="0",
        last_verified_at=datetime.utcnow()
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", summary="删除CF账号")
async def delete_account(
    account_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    account = db.query(CFAccount).filter(CFAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(account)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{account_id}/verify", summary="重新验证CF账号Token")
async def verify_account(
    account_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    account = db.query(CFAccount).filter(CFAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    is_valid = await cf_service.verify_token(account.api_token)
    from datetime import datetime
    account.status = AccountStatus.active if is_valid else AccountStatus.error
    account.last_verified_at = datetime.utcnow()
    db.commit()

    # 同步更新站点数量
    if is_valid:
        projects = await cf_service.get_pages_projects(account.account_id, account.api_token)
        account.site_count = str(len(projects))
        db.commit()

    return {
        "account_id": account_id,
        "is_valid": is_valid,
        "status": account.status,
        "site_count": account.site_count
    }


@router.get("/{account_id}/sites", summary="获取账号下的CF Pages站点")
async def get_account_sites(
    account_id: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    account = db.query(CFAccount).filter(CFAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    projects = await cf_service.get_pages_projects(account.account_id, account.api_token)
    return {
        "account_name": account.name,
        "account_id": account.account_id,
        "projects": projects
    }


@router.patch("/{account_id}", summary="重命名账号")
def rename_account(
    account_id: str,
    body: dict,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    from app.models.account import CFAccount
    acct = db.query(CFAccount).filter(CFAccount.id == account_id).first()
    if not acct:
        from fastapi import HTTPException
        raise HTTPException(404, "账号不存在")
    if "name" in body:
        acct.name = body["name"]
        db.commit()
        db.refresh(acct)
    return {"id": str(acct.id), "name": acct.name, "status": acct.status}

