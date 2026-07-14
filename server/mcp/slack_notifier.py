"""
Slack Notification MCP 연동 모듈.
서버 크리티컬 예외 상황 및 LangGraph L3 가드레일 최종 실패 시
비동기로 슬랙 채널에 즉시 에러 경보를 발행합니다.
"""

import asyncio
import contextlib
import json
import logging
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# Load env safely (guide 3.4)
try:
    from dotenv import load_dotenv

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except ImportError:
    pass


class SlackNotifierMCP:
    """
    슬랙 채널로 경보를 전송하는 MCP 모듈 (싱글톤 지원).
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # 1. Incoming Webhook URL 로드
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        # 2. Web API Bot Token & Channel ID 폴백 로드
        self.bot_token = os.getenv("SLACK_BOT_TOKEN")
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")

    def send_notification_sync(self, text: str) -> bool:
        """
        동기적으로 슬랙 알림을 전송합니다. (urllib.request 활용)
        """
        # 웹훅 URL이 설정되어 있는 경우 (우선 순위 1)
        if self.webhook_url:
            headers = {"Content-Type": "application/json; charset=utf-8"}
            payload = {"text": text}
            try:
                data = json.dumps(payload).encode("utf-8")
                req = Request(self.webhook_url, data=data, headers=headers, method="POST")  # noqa: S310
                with urlopen(req, timeout=5) as response:  # nosec B310 # noqa: S310
                    res_body = response.read().decode("utf-8")
                    if res_body == "ok" or response.status == 200:
                        logger.info("[SLACK NOTIFIER] 웹훅 메시지 전송 성공")
                        return True
                    else:
                        logger.error(f"[SLACK NOTIFIER] 웹훅 메시지 전송 실패: {res_body}")
            except HTTPError as e:
                logger.error(f"[SLACK NOTIFIER] HTTP 에러 {e.code} 발생: {e.reason}")
            except URLError as e:
                logger.error(f"[SLACK NOTIFIER] 네트워크 연결 에러 발생: {e.reason}")
            except Exception as e:
                logger.error(f"[SLACK NOTIFIER] 예기치 못한 에러 발생: {e!s}")

        # Web API 토큰이 설정되어 있는 경우 (폴백 순위 2)
        elif self.bot_token and self.channel_id:
            url = "https://slack.com/api/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json; charset=utf-8",
            }
            payload = {"channel": self.channel_id, "text": text}
            try:
                data = json.dumps(payload).encode("utf-8")
                req = Request(url, data=data, headers=headers, method="POST")  # noqa: S310
                with urlopen(req, timeout=5) as response:  # nosec B310 # noqa: S310
                    res_body = response.read().decode("utf-8")
                    res_data = json.loads(res_body)
                    if res_data.get("ok"):
                        logger.info("[SLACK NOTIFIER] Web API 메시지 전송 성공")
                        return True
                    else:
                        logger.error(f"[SLACK NOTIFIER] Web API 전송 실패: {res_data.get('error')}")
            except Exception as e:
                logger.error(f"[SLACK NOTIFIER] Web API 예외 발생: {e!s}")

        else:
            # 외부 자격 증명이 없는 경우 로그만 출력 (Mock 동작)
            logger.warning(
                "[SLACK NOTIFIER] SLACK_WEBHOOK_URL 또는 SLACK_BOT_TOKEN이 없어 콘솔 로그로 대체합니다."
            )
            logger.info(f"[SLACK MOCK NOTIFICATION] {text}")
            return True

        return False

    async def send_notification(self, text: str) -> bool:
        """
        비동기로 슬랙 알림을 전송합니다 (이벤트 루프 차단 우회).
        """
        return await asyncio.to_thread(self.send_notification_sync, text)


# 싱글톤 인스턴스 제공
slack_notifier = SlackNotifierMCP()
