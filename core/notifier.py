"""
通知模块
异常时蜂鸣告警 + Telegram Bot通知
"""
import sys
import time
import asyncio
from typing import Optional

import httpx

from core.logger import logger


class Notifier:
    """异常通知：蜂鸣 + Telegram"""

    def __init__(self, config: dict):
        cfg = config.get("telegram", {})
        self.enabled = cfg.get("enabled", False)
        self.bot_token = cfg.get("bot_token", "")
        self.chat_id = cfg.get("chat_id", "")
        self.proxy = cfg.get("proxy", "")
        self.mode = cfg.get("mode", "summary")
        logger.debug(f"通知模块初始化: Telegram={'启用' if self.enabled else '禁用'}")

    # ============================================================
    # 蜂鸣
    # ============================================================

    def beep_alert(self, count: int = 3):
        """系统蜂鸣告警"""
        logger.debug(f"蜂鸣告警 {count} 次")
        if sys.platform == "win32":
            import winsound
            for _ in range(count):
                winsound.Beep(1000, 300)  # 1000Hz, 300ms
                time.sleep(0.2)
        elif sys.platform == "darwin":
            # macOS: 用afplay播放系统音效
            import subprocess
            for _ in range(count):
                subprocess.run(
                    ["afplay", "/System/Library/Sounds/Ping.aiff"],
                    capture_output=True
                )
                time.sleep(0.2)
        else:
            # Linux: 终端响铃
            for _ in range(count):
                print("\a", end="", flush=True)
                time.sleep(0.2)

    # ============================================================
    # Telegram
    # ============================================================

    async def send_telegram(self, message: str) -> bool:
        """发送Telegram消息"""
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        client_kwargs = {}
        if self.proxy:
            client_kwargs["proxy"] = self.proxy

        try:
            async with httpx.AsyncClient(timeout=15, **client_kwargs) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("Telegram 通知已发送")
                    return True
                else:
                    logger.error(f"Telegram 发送失败: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"Telegram 连接失败: {e}")
            return False

    async def notify_anomalies(self, results: list[dict]):
        """根据检测结果发送通知"""
        anomalies = [r for r in results if r.get("status") not in ("normal", "no_qr")]

        if not anomalies:
            logger.debug("无异常，不需要通知")
            return

        logger.info(f"发现 {len(anomalies)} 个异常，发送通知")

        # 先蜂鸣
        self.beep_alert(count=3)

        # 再Telegram
        if not self.enabled:
            logger.debug("Telegram 通知已禁用")
            return

        if self.mode in ("summary", "both"):
            await self._send_summary(anomalies)

        if self.mode in ("per_anomaly", "both"):
            for r in anomalies:
                await self._send_single(r)
                await asyncio.sleep(0.5)  # 避免被限流

    async def _send_summary(self, anomalies: list[dict]):
        """发送汇总通知"""
        lines = [
            "<b>🔗 二维码扫描异常汇总</b>",
            f"异常数量: <b>{len(anomalies)}</b>",
            ""
        ]
        for r in anomalies:
            status_label = {
                "blocked": "⛔已封禁", "dialog": "⚠️弹窗",
                "blank": "🈳空白页", "short": "📝极少文字",
                "unknown": "❓未知"
            }.get(r.get("status"), r.get("status", "?"))

            link = r.get("link", "")[:60]
            lines.append(
                f"{status_label} | {r.get('wechat_id', '?')} | {link}"
            )

        await self.send_telegram("\n".join(lines))

    async def _send_single(self, r: dict):
        """发送单个异常通知"""
        status_label = {
            "blocked": "⛔已封禁", "dialog": "⚠️弹窗",
            "blank": "🈳空白页", "short": "📝极少文字",
            "unknown": "❓未知"
        }.get(r.get("status"), r.get("status", "?"))

        msg = (
            f"<b>🔗 二维码异常</b>\n"
            f"微信号: {r.get('wechat_id', '?')}\n"
            f"链接: {r.get('link', '无')[:100]}\n"
            f"状态: {status_label}\n"
            f"详情: {r.get('detail', '')[:200]}"
        )
        await self.send_telegram(msg)
