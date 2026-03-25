"""域名自动化流水线：注册完成 → DNS配置 → CF绑定"""
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def run_domain_pipeline(domain_id: str, cf_pages_target: str, db_url: str):
    """
    全自动域名配置流水线（后台异步任务）
    1. 等待域名注册完成（轮询，最多10分钟）
    2. 添加 CNAME 记录（@ → cf_pages_target）
    3. 等待 DNS 生效（最多5分钟）
    4. 调用 CF bind_custom_domain
    5. 更新 domain.status = active
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.registrar import Domain, DomainStatus, RegistrarAccount, RegistrarProvider
    from app.core.crypto import decrypt
    from app.services import cf_service

    engine = create_engine(db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            logger.error(f"Domain {domain_id} not found")
            return

        registrar = db.query(RegistrarAccount).filter(
            RegistrarAccount.id == domain.registrar_account_id
        ).first()
        if not registrar:
            domain.status = DomainStatus.error
            domain.error_msg = "注册商账号不存在"
            db.commit()
            return

        secret_id = decrypt(registrar.secret_id)
        secret_key = decrypt(registrar.secret_key)

        # 1. 等待域名注册完成（最多 10 分钟轮询）
        domain.status = DomainStatus.registering
        db.commit()
        registered = False
        for _ in range(20):
            await asyncio.sleep(30)
            if registrar.provider == RegistrarProvider.tencent:
                from app.services import tencent_domain_service as svc
                result = await svc.get_domain_status(secret_id, secret_key, domain.domain_name)
            else:
                from app.services import aliyun_domain_service as svc
                result = await svc.get_domain_status(secret_id, secret_key, domain.domain_name)
            if result.get("registered"):
                registered = True
                break

        if not registered:
            domain.status = DomainStatus.error
            domain.error_msg = "域名注册超时（10分钟内未完成），请手动检查"
            db.commit()
            return

        domain.status = DomainStatus.registered
        db.commit()

        # 2. 添加 CNAME 记录
        domain.status = DomainStatus.dns_configuring
        db.commit()
        if registrar.provider == RegistrarProvider.tencent:
            from app.services import tencent_domain_service as svc
            cname_ok = await svc.add_cname_record(
                secret_id, secret_key, domain.domain_name, "@", cf_pages_target
            )
            await svc.add_cname_record(
                secret_id, secret_key, domain.domain_name, "www", cf_pages_target
            )
        else:
            from app.services import aliyun_domain_service as svc
            cname_ok = await svc.add_cname_record(
                secret_id, secret_key, domain.domain_name, "@", cf_pages_target
            )
            await svc.add_cname_record(
                secret_id, secret_key, domain.domain_name, "www", cf_pages_target
            )

        if not cname_ok:
            domain.status = DomainStatus.error
            domain.error_msg = "DNS CNAME 记录添加失败"
            db.commit()
            return

        domain.status = DomainStatus.dns_configured
        db.commit()

        # 3. 等待 DNS 生效（最多 5 分钟）
        import socket
        dns_ok = False
        for _ in range(10):
            await asyncio.sleep(30)
            try:
                answers = socket.getaddrinfo(domain.domain_name, None)
                if answers:
                    dns_ok = True
                    break
            except Exception:
                pass

        # DNS 即使没完全生效，也继续 CF 绑定（CF 会异步验证）

        # 4. 调用 CF 绑定
        if domain.blog_id:
            from app.models.blog import Blog
            from app.models.account import CFAccount
            blog = db.query(Blog).filter(Blog.id == domain.blog_id).first()
            if blog:
                cf_account = db.query(CFAccount).filter(CFAccount.id == blog.cf_account_id).first()
                if cf_account and blog.cf_project_name:
                    domain.status = DomainStatus.cf_binding
                    db.commit()
                    try:
                        await cf_service.bind_custom_domain(
                            cf_account.account_id,
                            cf_account.api_token,
                            blog.cf_project_name,
                            domain.domain_name
                        )
                        blog.custom_domain = domain.domain_name
                        db.commit()
                    except Exception as e:
                        logger.warning(f"CF 绑定失败（可能需要等待DNS生效后重试）: {e}")

        domain.status = DomainStatus.active
        domain.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"域名流水线完成: {domain.domain_name}")

    except Exception as e:
        logger.error(f"域名流水线异常 domain_id={domain_id}: {e}")
        try:
            domain = db.query(Domain).filter(Domain.id == domain_id).first()
            if domain:
                domain.status = DomainStatus.error
                domain.error_msg = f"流水线异常: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
