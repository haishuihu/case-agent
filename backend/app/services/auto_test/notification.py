from __future__ import annotations

import json
import logging

import httpx

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务

    支持企业微信、钉钉、飞书 Webhook 以及邮件通知。
    解析 TestPlan 的 notification_config 字段来确定通知渠道和接收人。
    """

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=10)
        return self._http_client

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def notify(
        self,
        notification_config: dict,
        title: str,
        content: str,
    ) -> list[dict]:
        """发送通知到配置的渠道"""
        results = []
        channels = notification_config.get("channels", [])

        for channel in channels:
            channel_type = channel.get("type", "")
            try:
                if channel_type == "wecom":
                    result = await self._send_wecom(channel, title, content)
                elif channel_type == "dingtalk":
                    result = await self._send_dingtalk(channel, title, content)
                elif channel_type == "feishu":
                    result = await self._send_feishu(channel, title, content)
                elif channel_type == "email":
                    result = await self._send_email(channel, title, content)
                else:
                    result = {"channel": channel_type, "status": "skipped", "reason": f"Unsupported channel: {channel_type}"}

                results.append(result)
            except Exception as e:
                logger.exception(f"Notification failed for channel {channel_type}")
                results.append({"channel": channel_type, "status": "error", "error": str(e)})

        return results

    async def _send_wecom(self, channel: dict, title: str, content: str) -> dict:
        webhook_url = channel.get("webhook_url", "")
        if not webhook_url:
            return {"channel": "wecom", "status": "skipped", "reason": "No webhook_url"}

        msg = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"## {title}\n{content}"
            }
        }
        client = await self._get_client()
        resp = await client.post(webhook_url, json=msg)
        return {"channel": "wecom", "status": "ok" if resp.status_code == 200 else "error", "status_code": resp.status_code}

    async def _send_dingtalk(self, channel: dict, title: str, content: str) -> dict:
        webhook_url = channel.get("webhook_url", "")
        if not webhook_url:
            return {"channel": "dingtalk", "status": "skipped", "reason": "No webhook_url"}

        msg = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n{content}"
            }
        }
        client = await self._get_client()
        resp = await client.post(webhook_url, json=msg)
        return {"channel": "dingtalk", "status": "ok" if resp.status_code == 200 else "error", "status_code": resp.status_code}

    async def _send_feishu(self, channel: dict, title: str, content: str) -> dict:
        webhook_url = channel.get("webhook_url", "")
        if not webhook_url:
            return {"channel": "feishu", "status": "skipped", "reason": "No webhook_url"}

        msg = {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": title}},
                "elements": [{"tag": "markdown", "content": content}]
            }
        }
        client = await self._get_client()
        resp = await client.post(webhook_url, json=msg)
        return {"channel": "feishu", "status": "ok" if resp.status_code == 200 else "error", "status_code": resp.status_code}

    async def _send_email(self, channel: dict, title: str, content: str) -> dict:
        # Placeholder: use an email service or SMTP
        return {"channel": "email", "status": "skipped", "reason": "Email service not configured"}


# Module-level singleton
notification_service = NotificationService()
