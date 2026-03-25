"""阿里云域名注册 + Alidns DNS 管理服务"""
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def verify_credentials(access_key_id: str, access_key_secret: str) -> bool:
    def _sync():
        try:
            import aliyunsdkcore.client as acsClient
            from aliyunsdkcore.request import CommonRequest
            client = acsClient.AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("domain.aliyuncs.com")
            request.set_version("2018-01-29")
            request.set_action_name("QueryDomainList")
            request.add_query_param("PageNum", "1")
            request.add_query_param("PageSize", "1")
            client.do_action_with_exception(request)
            return True
        except Exception as e:
            logger.warning(f"阿里云凭证验证失败: {e}")
            return False
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def check_domain_available(access_key_id: str, access_key_secret: str, domain: str) -> dict:
    def _sync():
        try:
            import aliyunsdkcore.client as acsClient
            from aliyunsdkcore.request import CommonRequest
            import json
            client = acsClient.AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("domain.aliyuncs.com")
            request.set_version("2018-01-29")
            request.set_action_name("CheckDomain")
            request.add_query_param("DomainName", domain)
            resp = json.loads(client.do_action_with_exception(request))
            avail = resp.get("Avail") == "1" or resp.get("Avail") == 1
            price = 0.0
            if "Price" in resp:
                price = float(resp["Price"])
            return {"available": avail, "price": price, "currency": "CNY"}
        except Exception as e:
            logger.error(f"阿里云查询域名 {domain} 失败: {e}")
            return {"available": False, "price": 0, "currency": "CNY", "error": str(e)}
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def get_registrant_profile_id(access_key_id: str, access_key_secret: str) -> Optional[str]:
    def _sync():
        try:
            import aliyunsdkcore.client as acsClient
            from aliyunsdkcore.request import CommonRequest
            import json
            client = acsClient.AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("domain.aliyuncs.com")
            request.set_version("2018-01-29")
            request.set_action_name("QueryRegistrantProfiles")
            request.add_query_param("PageNum", "1")
            request.add_query_param("PageSize", "5")
            resp = json.loads(client.do_action_with_exception(request))
            profiles = resp.get("RegistrantProfiles", {}).get("RegistrantProfile", [])
            if profiles:
                return str(profiles[0]["RegistrantProfileId"])
            return None
        except Exception as e:
            logger.error(f"获取阿里云注册模板失败: {e}")
            return None
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def register_domain(access_key_id: str, access_key_secret: str, domain: str) -> str:
    profile_id = await get_registrant_profile_id(access_key_id, access_key_secret)
    if not profile_id:
        raise ValueError("阿里云账号下没有可用的注册人信息模板，请先在控制台完成实名认证并创建信息模板")
    def _sync():
        import aliyunsdkcore.client as acsClient
        from aliyunsdkcore.request import CommonRequest
        import json
        client = acsClient.AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
        request = CommonRequest()
        request.set_domain("domain.aliyuncs.com")
        request.set_version("2018-01-29")
        request.set_action_name("RegisterDomain")
        request.add_query_param("DomainName", domain)
        request.add_query_param("SubscriptionDuration", "1")
        request.add_query_param("RegistrantProfileId", profile_id)
        request.add_query_param("EnableDomainProxy", "FALSE")
        resp = json.loads(client.do_action_with_exception(request))
        return resp.get("OrderId", "unknown")
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def get_domain_status(access_key_id: str, access_key_secret: str, domain: str) -> dict:
    def _sync():
        try:
            import aliyunsdkcore.client as acsClient
            from aliyunsdkcore.request import CommonRequest
            import json
            client = acsClient.AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("domain.aliyuncs.com")
            request.set_version("2018-01-29")
            request.set_action_name("QueryDomainByDomainName")
            request.add_query_param("DomainName", domain)
            resp = json.loads(client.do_action_with_exception(request))
            return {
                "registered": True,
                "status": resp.get("DomainStatus", "unknown"),
                "expire": resp.get("ExpirationDate", "")
            }
        except Exception as e:
            err_str = str(e)
            if "InvalidDomain" in err_str or "not exist" in err_str.lower():
                return {"registered": False, "status": "not_registered"}
            return {"registered": False, "status": "error", "error": err_str}
    return await asyncio.get_event_loop().run_in_executor(None, _sync)


async def add_cname_record(access_key_id: str, access_key_secret: str, domain: str, subdomain: str, value: str) -> bool:
    def _sync():
        try:
            import aliyunsdkcore.client as acsClient
            from aliyunsdkcore.request import CommonRequest
            client = acsClient.AcsClient(access_key_id, access_key_secret, "cn-hangzhou")
            request = CommonRequest()
            request.set_domain("alidns.aliyuncs.com")
            request.set_version("2015-01-09")
            request.set_action_name("AddDomainRecord")
            request.add_query_param("DomainName", domain)
            request.add_query_param("RR", subdomain)
            request.add_query_param("Type", "CNAME")
            request.add_query_param("Value", value)
            client.do_action_with_exception(request)
            return True
        except Exception as e:
            logger.error(f"阿里云 DNS 添加 CNAME 失败 {domain}: {e}")
            return False
    return await asyncio.get_event_loop().run_in_executor(None, _sync)
