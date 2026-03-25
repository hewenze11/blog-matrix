"""腾讯云域名注册 + DNSPod DNS 管理服务"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def verify_credentials(secret_id: str, secret_key: str) -> bool:
    """验证腾讯云凭证是否有效"""
    def _sync():
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
            from tencentcloud.domain.v20180808 import domain_client, models
            cred = credential.Credential(secret_id, secret_key)
            client = domain_client.DomainClient(cred, "")
            req = models.DescribeDomainNameListRequest()
            req.Limit = 1
            req.Offset = 0
            client.DescribeDomainNameList(req)
            return True
        except Exception as e:
            logger.warning(f"腾讯云凭证验证失败: {e}")
            return False
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def check_domain_available(secret_id: str, secret_key: str, domain: str) -> dict:
    """查询域名是否可注册及价格"""
    def _sync():
        try:
            from tencentcloud.common import credential
            from tencentcloud.domain.v20180808 import domain_client, models
            cred = credential.Credential(secret_id, secret_key)
            client = domain_client.DomainClient(cred, "")
            req = models.CheckDomainRequest()
            req.DomainName = domain
            req.Period = 1
            resp = client.CheckDomain(req)
            available = resp.Available
            price = 0.0
            if hasattr(resp, "Price") and resp.Price:
                price = float(resp.Price) / 100.0
            return {"available": available, "price": price, "currency": "CNY"}
        except Exception as e:
            logger.error(f"腾讯云查询域名 {domain} 失败: {e}")
            return {"available": False, "price": 0, "currency": "CNY", "error": str(e)}
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def get_template_id(secret_id: str, secret_key: str) -> Optional[str]:
    """获取第一个可用的域名注册模板ID"""
    def _sync():
        try:
            from tencentcloud.common import credential
            from tencentcloud.domain.v20180808 import domain_client, models
            cred = credential.Credential(secret_id, secret_key)
            client = domain_client.DomainClient(cred, "")
            req = models.DescribeTemplateListRequest()
            req.Limit = 10
            req.Offset = 0
            resp = client.DescribeTemplateList(req)
            if resp.TemplateSet and len(resp.TemplateSet) > 0:
                return resp.TemplateSet[0].TemplateId
            return None
        except Exception as e:
            logger.error(f"获取腾讯云模板失败: {e}")
            return None
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def register_domain(secret_id: str, secret_key: str, domain: str) -> str:
    """购买域名，返回 order_id"""
    template_id = await get_template_id(secret_id, secret_key)
    if not template_id:
        raise ValueError("腾讯云账号下没有可用的域名注册模板，请先在控制台创建实名模板")
    def _sync():
        from tencentcloud.common import credential
        from tencentcloud.domain.v20180808 import domain_client, models
        cred = credential.Credential(secret_id, secret_key)
        client = domain_client.DomainClient(cred, "")
        req = models.RegisterDomainRequest()
        req.Domain = domain
        req.Period = 1
        req.TemplateId = template_id
        req.BuyDomain = True
        req.AutoRenewFlag = 0
        resp = client.RegisterDomain(req)
        return resp.OrderId if hasattr(resp, "OrderId") and resp.OrderId else "unknown"
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def get_domain_status(secret_id: str, secret_key: str, domain: str) -> dict:
    """查询域名注册状态"""
    def _sync():
        try:
            from tencentcloud.common import credential
            from tencentcloud.domain.v20180808 import domain_client, models
            cred = credential.Credential(secret_id, secret_key)
            client = domain_client.DomainClient(cred, "")
            req = models.DescribeDomainNameListRequest()
            req.Limit = 100
            req.Offset = 0
            resp = client.DescribeDomainNameList(req)
            for d in (resp.DomainSet or []):
                if d.DomainName == domain:
                    return {"registered": True, "status": d.BuyStatus, "expire": d.ExpirationDate}
            return {"registered": False, "status": "unknown"}
        except Exception as e:
            return {"registered": False, "status": "error", "error": str(e)}
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def add_cname_record(secret_id: str, secret_key: str, domain: str, subdomain: str, value: str) -> bool:
    """通过 DNSPod 添加 CNAME 记录"""
    def _sync():
        try:
            from tencentcloud.common import credential
            from tencentcloud.dnspod.v20210323 import dnspod_client, models
            cred = credential.Credential(secret_id, secret_key)
            client = dnspod_client.DnspodClient(cred, "")
            req = models.CreateRecordRequest()
            req.Domain = domain
            req.SubDomain = subdomain
            req.RecordType = "CNAME"
            req.RecordLine = "默认"
            req.Value = value
            client.CreateRecord(req)
            return True
        except Exception as e:
            logger.error(f"DNSPod 添加 CNAME 失败 {domain}: {e}")
            return False
    return await asyncio.get_event_loop().run_in_executor(None, _sync)
