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
    CF Pages Direct Upload V2 - 正确实现
    manifest 必须以 multipart files 字段方式提交（content-type: application/json）
    """
    import hashlib
    import json as _json

    auth_headers = {"Authorization": f"Bearer {api_token}"}

    # Step 1: 解压 zip，读取所有文件
    file_contents: Dict[str, bytes] = {}
    with zipfile.ZipFile(bundle_path, "r") as zf:
        for name in zf.namelist():
            if not name.endswith("/"):
                path = f"/{name}" if not name.startswith("/") else name
                file_contents[path] = zf.read(name)

    # Step 2: 计算 SHA256
    file_hashes = {path: hashlib.sha256(content).hexdigest() for path, content in file_contents.items()}

    # Step 3: POST manifest（multipart files 方式）
    async with httpx.AsyncClient(timeout=60) as client:
        manifest_resp = await client.post(
            f"{CF_API_BASE}/accounts/{account_id}/pages/projects/{project_name}/deployments",
            headers=auth_headers,
            files={"manifest": (None, _json.dumps(file_hashes), "application/json")},
        )
        if manifest_resp.status_code == 429:
            raise CFRateLimitError("Rate limited during manifest")
        manifest_data = manifest_resp.json()
        if not manifest_data.get("success"):
            errors = manifest_data.get("errors", [])
            raise CFApiError(f"Manifest upload failed: {errors}", errors)

        result = manifest_data.get("result", {})
        deployment_id = result.get("id", "")
        required_hashes = set(result.get("required_hashes") or [])

        logger.info(f"Manifest OK, dep_id={deployment_id}, need {len(required_hashes)} files")

        # Step 4: 上传缺失文件（如有）
        if required_hashes:
            hash_to_content = {
                file_hashes[p]: c
                for p, c in file_contents.items()
                if file_hashes[p] in required_hashes
            }
            upload_files = [
                (h, (h, content, "application/octet-stream"))
                for h, content in hash_to_content.items()
            ]
            # 分批上传（每批 ≤ 100）
            batch_size = 100
            for i in range(0, len(upload_files), batch_size):
                batch = upload_files[i:i+batch_size]
                up_resp = await client.post(
                    f"{CF_API_BASE}/accounts/{account_id}/pages/projects/{project_name}/deployments/{deployment_id}/upload-missing-files",
                    headers=auth_headers,
                    files=batch,
                )
                if up_resp.status_code == 429:
                    raise CFRateLimitError("Rate limited during file upload")
                logger.info(f"Uploaded batch {i//batch_size+1}: {len(batch)} files, status={up_resp.status_code}")

        # Step 5: finish（忽略 405）
        try:
            await client.post(
                f"{CF_API_BASE}/accounts/{account_id}/pages/projects/{project_name}/deployments/{deployment_id}/finish",
                headers=auth_headers,
            )
        except Exception:
            pass

    return {
        "deployment_id": deployment_id,
        "url": f"https://{project_name}.pages.dev",
        "pages_domain": f"{project_name}.pages.dev",
        "status": "active",
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
