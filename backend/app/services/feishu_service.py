"""
飞书 Webhook 告警服务
"""
import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def send_alert(webhook_url: str, title: str, content: str, level: str = "error"):
    """发送飞书告警"""
    color_map = {"error": "red", "warning": "orange", "info": "blue"}
    color = color_map.get(level, "red")

    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"🚨 博客矩阵平台告警"},
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**{title}**\n{content}\n\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }
            ]
        }
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code == 200:
                logger.info(f"飞书告警发送成功: {title}")
            else:
                logger.error(f"飞书告警发送失败: {resp.status_code} {resp.text}")
    except Exception as e:
        logger.error(f"飞书告警异常: {e}")


async def send_offline_alert(webhook_url: str, blog_name: str, domain: str, fail_count: int):
    """发送站点离线告警"""
    await send_alert(
        webhook_url,
        title=f"站点离线：{blog_name}",
        content=f"域名：`{domain}`\n连续失败：{fail_count} 次\n状态：**已判定离线**\n请尽快排查！",
        level="error"
    )
