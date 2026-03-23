"""
Cloudflare Pages API 服务
处理账号验证、项目创建、静态包上传、自定义域名绑定
带 429 退避重试
"""
import httpx
import asyncio
import zipfile
import io
import os
from typing import Optional, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging

logger = logging.getLogger(__name__)

CF_API_BASE = "https://api.cloudflare.com/client/v4"


class CFRateLimitError(Exception):
    pass


class CFApiError(Exception):
    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


def _headers(api_token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }


@retry(
    retry=retry_if_exception_type(CFRateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
)
async def _request(method: str, url: str, api_token: str, **kwargs) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, headers=_headers(api_token), **kwargs)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "5"))
            logger.warning(f"CF API 429 限流，等待 {retry_after}s...")
            await asyncio.sleep(retry_after)
            raise CFRateLimitError(f"Rate limited, retry after {retry_after}s")
        data = resp.json()
        if not data.get("success", True) and resp.status_code >= 400:
            errors = data.get("errors", [])
            raise CFApiError(f"CF API Error: {errors}", errors)
        return data


async def verify_token(api_token: str) -> bool:
    """验证 Token 是否有效"""
    try:
        data = await _request("GET", f"{CF_API_BASE}/user/tokens/verify", api_token)
        return data.get("result", {}).get("status") == "active"
    except Exception:
        return False


async def get_pages_projects(account_id: str, api_token: str) -> list:
    """获取账号下所有 Pages 项目"""
    try:
        data = await _request(
            "GET",
            f"{CF_API_BASE}/accounts/{account_id}/pages/projects",
            api_token,
            params={"per_page": 100}
        )
        return data.get("result", [])
    except Exception as e:
        logger.error(f"获取 Pages 项目失败: {e}")
        return []


async def create_pages_project(account_id: str, api_token: str, project_name: str) -> Dict:
    """创建 Pages 项目"""
    data = await _request(
        "POST",
        f"{CF_API_BASE}/accounts/{account_id}/pages/projects",
        api_token,
        json={
            "name": project_name,
            "production_branch": "main"
        }
    )
    result = data.get("result", {})
    return {
        "project_name": result.get("name"),
        "subdomain": result.get("subdomain"),
        "pages_domain": f"{result.get('subdomain', project_name)}.pages.dev"
    }


async def upload_static_bundle(
    account_id: str,
    api_token: str,
    project_name: str,
    bundle_path: str
) -> Dict:
    """
    Direct Upload 方式上传静态包到 CF Pages
    bundle_path: zip 文件路径
    """
    # Step 1: 创建部署
    deploy_data = await _request(
        "POST",
        f"{CF_API_BASE}/accounts/{account_id}/pages/projects/{project_name}/deployments",
        api_token,
    )
    deployment = deploy_data.get("result", {})
    deployment_id = deployment.get("id")

    # Step 2: 上传文件 (multipart)
    with open(bundle_path, "rb") as f:
        bundle_bytes = f.read()

    async with httpx.AsyncClient(timeout=120) as client:
        files = {"file": (os.path.basename(bundle_path), bundle_bytes, "application/zip")}
        resp = await client.post(
            f"{CF_API_BASE}/accounts/{account_id}/pages/projects/{project_name}/deployments",
            headers={"Authorization": f"Bearer {api_token}"},
            files=files,
        )
        if resp.status_code == 429:
            raise CFRateLimitError("Rate limited during upload")
        upload_data = resp.json()

    result = upload_data.get("result", {})
    return {
        "deployment_id": result.get("id"),
        "url": result.get("url"),
        "pages_domain": f"{project_name}.pages.dev",
        "status": result.get("latest_stage", {}).get("status", "unknown"),
    }


async def bind_custom_domain(
    account_id: str,
    api_token: str,
    project_name: str,
    domain: str
) -> Dict:
    """绑定自定义域名"""
    data = await _request(
        "POST",
        f"{CF_API_BASE}/accounts/{account_id}/pages/projects/{project_name}/domains",
        api_token,
        json={"name": domain}
    )
    return data.get("result", {})
