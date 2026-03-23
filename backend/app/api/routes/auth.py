from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, verify_password, create_access_token, get_password_hash
from app.core.config import settings
from app.models.blog import User
from app.schemas import LoginRequest, TokenResponse
import uuid

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse, summary="登录获取 Token")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    # 检查数据库用户
    user = db.query(User).filter(User.username == req.username).first()

    if user:
        if not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    else:
        # 兜底：检查环境变量中的默认管理员
        if req.username != settings.ADMIN_USERNAME or req.password != settings.ADMIN_PASSWORD:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    token = create_access_token({"sub": req.username, "role": "admin"})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.get("/me", summary="获取当前用户信息")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {"username": current_user.get("sub"), "role": current_user.get("role")}


@router.post("/change-password", summary="修改密码")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    username = current_user.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # 创建用户记录
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            hashed_password=get_password_hash(new_password)
        )
        db.add(user)
        db.commit()
        return {"message": "密码设置成功"}

    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码错误")

    user.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"message": "密码修改成功"}
