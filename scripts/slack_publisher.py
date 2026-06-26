# -*- coding: utf-8 -*-
"""
Slack Integration Helper Script for Minchodan
This script allows reading channel history and posting messages or local files
to the specified Slack channel using standard HTTP client (urllib).
"""

import os
import sys
import argparse
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Reconfigure stdout for UTF-8 output formatting support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Setup basic logging config
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Try to load environment variables from local .env file safely
try:
    from dotenv import load_dotenv
    # Compute relative path to workspace root .env
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info("Successfully loaded environment configuration from .env")
    else:
        logger.warning(".env file not found, relying on system environment variables")
except ImportError:
    logger.warning("python-dotenv library is not installed. Using raw environment variables")


class SlackClient:
    """
    Lightweight Slack Web API Client wrapper using standard library urllib.
    """
    def __init__(self, token=None):
        # Defensive check: load token from environment if not explicitly provided
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        if not self.token:
            logger.warning("SLACK_BOT_TOKEN environment variable is not defined.")

    def _send_request(self, api_method: str, payload: dict = None, method: str = "POST") -> dict:
        """
        Internal helper to send API requests to Slack.
        """
        if not self.token:
            logger.error("API request failed: Slack Bot Token is missing.")
            return {"ok": False, "error": "missing_token"}

        url = f"https://slack.com/api/{api_method}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        try:
            data = None
            if payload:
                # Ensure no emojis or raw characters break json serialization
                data = json.dumps(payload).encode("utf-8")

            req = Request(url, data=data, headers=headers, method=method)
            with urlopen(req, timeout=10) as response:
                res_body = response.read().decode("utf-8")
                res_data = json.loads(res_body)
                return res_data
        except HTTPError as e:
            logger.error(f"HTTP Error {e.code} during Slack API request: {e.reason}")
            return {"ok": False, "error": f"http_{e.code}"}
        except URLError as e:
            logger.error(f"Network Connection Error: {e.reason}")
            return {"ok": False, "error": "network_error"}
        except Exception as e:
            logger.error(f"Unexpected error encountered: {str(e)}")
            return {"ok": False, "error": "internal_error"}

    def post_message(self, channel_id: str, text: str) -> dict:
        """
        Posts a text message to a specific Slack channel.
        """
        if not channel_id:
            logger.error("Target Channel ID is empty.")
            return {"ok": False, "error": "missing_channel_id"}

        payload = {
            "channel": channel_id,
            "text": text
        }
        logger.info(f"Attempting to post message to channel: {channel_id}")
        result = self._send_request("chat.postMessage", payload)
        if result.get("ok"):
            logger.info("Message successfully posted to Slack.")
        else:
            logger.error(f"Slack postMessage failed: {result.get('error')}")
        return result

    def get_history(self, channel_id: str, limit: int = 10) -> dict:
        """
        Fetches the recent history from a specific Slack channel.
        """
        if not channel_id:
            logger.error("Target Channel ID is empty.")
            return {"ok": False, "error": "missing_channel_id"}

        payload = {
            "channel": channel_id,
            "limit": limit
        }
        logger.info(f"Retrieving recent history (limit={limit}) from channel: {channel_id}")
        
        # Slack history reading API requires GET query parameters or JSON payload
        result = self._send_request("conversations.history", payload, method="POST")
        if result.get("ok"):
            logger.info("History successfully retrieved from Slack.")
        else:
            logger.error(f"Slack conversations.history failed: {result.get('error')}")
        return result


def summarize_file_content(file_path: str) -> str:
    """
    Reads a local text file and generates a short structured summary.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        raise IOError(f"Failed to read file {file_path}: {str(e)}")

    total_lines = len(lines)
    # Extract headers (Markdown titles)
    headers = [line.strip() for line in lines if line.strip().startswith("#")]
    
    # Extract first few content lines (excluding header blocks)
    preview_lines = []
    for line in lines:
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#") and not cleaned.startswith(">"):
            preview_lines.append(cleaned)
            if len(preview_lines) >= 5:
                break

    summary = (
        f"*로컬 자료 요약 리포트*\n"
        f"- 파일명: `{os.path.basename(file_path)}` (총 {total_lines}행)\n"
        f"- 문서 헤더 목록:\n"
    )
    for h in headers[:5]:
        summary += f"  > {h}\n"
    
    if len(headers) > 5:
        summary += f"  > ...외 {len(headers)-5}개 헤더\n"

    summary += f"- 본문 초입 요약:\n"
    for pl in preview_lines:
        summary += f"  {pl}\n"

    return summary


def main():
    parser = argparse.ArgumentParser(description="Minchodan Slack Integration Publisher Tool")
    parser.add_argument("--post-text", type=str, help="Raw text message to publish directly to Slack")
    parser.add_argument("--post-file", type=str, help="Path of a local file to summarize and post to Slack")
    parser.add_argument("--get-history", action="store_true", help="Fetch and display recent channel history")
    parser.add_argument("--channel", type=str, help="Override default target Slack Channel ID")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of history logs (default: 10)")

    args = parser.parse_args()

    # Define fallback defaults
    channel_id = args.channel or os.getenv("SLACK_CHANNEL_ID") or "C0BCZSB5TJS"
    
    client = SlackClient()

    # Execute flow depending on command args
    if args.post_text:
        client.post_message(channel_id, args.post_text)
    
    elif args.post_file:
        try:
            summary = summarize_file_content(args.post_file)
            client.post_message(channel_id, summary)
        except Exception as e:
            logger.error(f"Failed to post file summary: {str(e)}")
            sys.exit(1)
            
    elif args.get_history:
        res = client.get_history(channel_id, args.limit)
        if res.get("ok"):
            messages = res.get("messages", [])
            print(json.dumps(messages, indent=2, ensure_ascii=False))
        else:
            print(f"Error fetching history: {res.get('error')}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
