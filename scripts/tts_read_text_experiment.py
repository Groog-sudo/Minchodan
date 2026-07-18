# -*- coding: utf-8 -*-
"""임의 한국어 문장(문자/안내문)을 프로젝트 TTS로 읽어 WAV로 저장하는 실험 스크립트.

사용 예:
  python scripts/tts_read_text_experiment.py --text "앞쪽에 킥보드가 있습니다"
  python scripts/tts_read_text_experiment.py --text "새 문자가 도착했습니다. 엄마에게서. 오늘 저녁 몇 시에 오실 건가요?" --play
  python scripts/tts_read_text_experiment.py --to-device
  python scripts/tts_read_text_experiment.py --to-device --device-id dev-001 --text "문자가 왔습니다"

엔진은 루트 .env의 TTS_ENGINE을 따릅니다 (edge / supertonic / piper).
--to-device 는 실행 중인 FastAPI의 /api/v1/debug/speak-to-device 로 푸시합니다.
앱이 WebSocket 연결된 상태에서 사용하세요.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import os
import sys
import wave
from contextlib import suppress
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="한국어 텍스트를 TTS로 합성해 WAV로 저장하는 실험 도구",
    )
    parser.add_argument(
        "--text",
        default="새 문자가 도착했습니다. 엄마에게서. 오늘 저녁 몇 시에 오실 건가요?",
        help="읽어 줄 한국어 문장 (문자/안내문 실험용)",
    )
    parser.add_argument(
        "--voice",
        default="ko",
        help="TTS voice 힌트 (엔진별 해석, 기본 ko)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="말하기 속도 (기본 1.0)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(PROJECT_ROOT, "outputs", "tts_experiment"),
        help="WAV 저장 폴더",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="합성 후 기본 앱으로 WAV 재생 시도 (Windows)",
    )
    parser.add_argument(
        "--to-device",
        action="store_true",
        help="로컬 WAV 저장 대신 연결된 모바일 앱으로 TTS 푸시",
    )
    parser.add_argument(
        "--device-id",
        default=None,
        help="--to-device 대상 device_id (생략 시 서버가 연결된 첫 단말 선택)",
    )
    parser.add_argument(
        "--api-base",
        default=os.getenv("TTS_EXPERIMENT_API_BASE", "http://127.0.0.1:8000"),
        help="FastAPI base URL (기본 http://127.0.0.1:8000)",
    )
    return parser.parse_args()


def wav_duration_sec(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate <= 0:
            return 0.0
        return frames / float(rate)


async def synthesize(text: str, voice: str, speed: float) -> bytes | None:
    from server.tts.tts_service import get_tts_service

    service = get_tts_service()
    engine = os.getenv("TTS_ENGINE", "supertonic")
    print(f"[TTS] engine={engine} voice={voice} speed={speed}")
    print(f"[TTS] text={text}")
    return await service.generate(text=text, voice=voice, speed=speed)


def play_wav(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(str(path))  # noqa: S606
        print(f"[TTS] 재생 요청: {path}")
        return
    print(f"[TTS] --play는 Windows에서만 자동 재생합니다. 파일: {path}")


async def push_to_device(
    api_base: str,
    text: str,
    voice: str,
    speed: float,
    device_id: str | None,
) -> int:
    import urllib.error
    import urllib.request

    url = f"{api_base.rstrip('/')}/api/v1/debug/speak-to-device"
    payload = {
        "text": text,
        "voice": voice,
        "speed": speed,
    }
    if device_id:
        payload["device_id"] = device_id

    body = __import__("json").dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"[TTS] 모바일 푸시 요청: {url}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
            print(f"[TTS] 응답 HTTP {resp.status}: {raw}")
            return 0
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"[TTS] 푸시 실패 HTTP {exc.code}: {detail}")
        if exc.code == 409:
            print("[TTS] 앱이 ws://<서버>:8000/ws/detect 에 연결되어 있는지 확인하세요.")
        return 3
    except urllib.error.URLError as exc:
        print(f"[TTS] 서버 연결 실패: {exc.reason}")
        print("[TTS] FastAPI(uvicorn)가 떠 있는지 확인하세요.")
        return 4


async def main_async() -> int:
    args = parse_args()
    text = (args.text or "").strip()
    if not text:
        print("[TTS] 빈 텍스트는 합성하지 않습니다.")
        return 1

    if args.to_device:
        return await push_to_device(
            api_base=args.api_base,
            text=text,
            voice=args.voice,
            speed=args.speed,
            device_id=args.device_id,
        )

    wav = await synthesize(text, args.voice, args.speed)
    if not wav:
        print("[TTS] 합성 실패 (엔진 미설치/네트워크/모델 확인)")
        return 2

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"tts_read_{stamp}.wav"
    out_path.write_bytes(wav)

    duration = wav_duration_sec(wav)
    print(f"[TTS] 저장 완료: {out_path}")
    print(f"[TTS] bytes={len(wav)} duration={duration:.2f}s")

    if args.play:
        play_wav(out_path)
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
