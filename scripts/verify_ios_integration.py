"""
iOS 단말과 GPU 서버 간 오케스트레이션 및 TTS E2E 통신 프로토콜을 검증하는 시뮬레이터.
실제 iOS 클라이언트의 프레임 전송 규격을 모사하여 FastAPI 서버에 전달하고,
오케스트레이션 결과 가이드 및 TTS 음성 합성 bytes 회신까지의 전체 흐름을 검증합니다.
"""

import asyncio
import json
import os
import subprocess  # nosec B404
import sys
import time

import cv2
import numpy as np

# UTF-8 출력 재설정 (guide 3.1)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# sys.path에 프로젝트 루트 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# websockets 패키지 체크
try:
    import websockets
except ImportError:
    print("[실패] websockets 패키지가 가상환경에 설치되어 있지 않습니다.")
    sys.exit(1)


def make_dummy_jpeg() -> bytes:
    """640x640 크기의 가상 더미 프레임 JPEG 바이트 생성"""
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
    assert ok, "더미 JPEG 인코딩 실패"
    return buf.tobytes()


async def run_client_simulation():
    server_url = "ws://127.0.0.1:8000/ws/detect?device_id=dev-001"
    device_token = "token-abc-001"  # noqa: S105 # nosec B105

    print("\n==================================================")
    print(" 1. iOS 단말 ↔ GPU 서버 E2E 연동성 시뮬레이션 시작")
    print("==================================================")

    print(f"-> 서버 접속 주소: {server_url}")

    try:
        async with websockets.connect(server_url) as ws:
            # 1. Welcome 수신
            welcome_msg = await ws.recv()
            welcome_data = json.loads(welcome_msg)
            print(f"[성공] Welcome 수신: {welcome_data}")
            assert welcome_data["type"] == "welcome"

            # 2. Hello (인증) 전송
            hello_payload = {"type": "hello", "device_id": "dev-001", "token": device_token}
            await ws.send(json.dumps(hello_payload))
            print(f"-> Hello 인증 요청 송신: token={device_token}")

            # 3. Auth OK 수신
            auth_msg = await ws.recv()
            auth_data = json.loads(auth_msg)
            print(f"[성공] Auth OK 수신: {auth_data}")
            assert auth_data["type"] == "auth_ok"

            # 4. Detection 메타데이터 송신 (바이너리 모드)
            event_id = "verify-e2e-evt-999"
            meta_payload = {
                "type": "detection",
                "payload": {
                    "event_id": event_id,
                    "device_id": "dev-001",
                    "frame_id": 100,
                    "stream": "cognitive",
                    "transport": "binary",
                },
            }
            await ws.send(json.dumps(meta_payload))
            print(f"-> Detection 메타데이터 송신 (event_id={event_id})")

            # 5. JPEG 바이너리 프레임 즉각 송신 (iOS 실기기 프로토콜)
            jpeg_bytes = make_dummy_jpeg()
            await ws.send(jpeg_bytes)
            print(f"-> JPEG 더미 바이너리 프레임 송신 ({len(jpeg_bytes)} bytes)")

            # 6. Ack 수신 대기
            ack_msg = await ws.recv()
            ack_data = json.loads(ack_msg)
            print(f"[성공] Ack 수신: {ack_data}")
            assert ack_data["type"] == "ack"
            assert ack_data["event_id"] == event_id

            # 7. 오케스트레이션 가이드 및 TTS 음성 합성 회신 대기 (최대 10초)
            print("-> 서버 백그라운드 오케스트레이션 및 TTS 합성 대기 중 (최대 10초)...")
            start_time = time.time()

            while True:
                if time.time() - start_time > 10.0:
                    print(
                        "[실패] 10초 이내에 오케스트레이션 가이드 응답을 받지 못했습니다. (타임아웃)"
                    )
                    break

                try:
                    response_msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    response_data = json.loads(response_msg)

                    if response_data.get("type") == "guide":
                        print("\n==================================================")
                        print(" [최종 검증 성공] iOS 연동 E2E 가이드 메시지 수신 완료!")
                        print("==================================================")
                        print(f" - 이벤트 ID: {response_data.get('event_id')}")
                        print(f" - 위험 수준: {response_data.get('risk_level')}")
                        print(
                            f" - 생성된 가이드 문장 (LangGraph): {response_data.get('guidance_text')}"
                        )
                        audio_len = len(response_data.get("audio_mp3_b64", ""))
                        print(f" - TTS 오디오 데이터 수신: {audio_len} bytes (base64)")
                        print("==================================================")
                        break
                    elif response_data.get("type") == "heartbeat":
                        # 서버의 하트비트 요청에 대해 즉각 ack 응답하여 타임아웃 방어
                        ack_payload = {
                            "type": "heartbeat_ack",
                            "ts": response_data.get("ts", int(time.time() * 1000)),
                        }
                        await ws.send(json.dumps(ack_payload))
                        print("-> Heartbeat 수신 및 ack 회신 완료")
                    else:
                        print(f"-> 수신된 기타 메시지(무시): {response_data.get('type')}")
                except TimeoutError:
                    print("[실패] 대기 시간 초과")
                    break

    except Exception as e:
        print(f"[실패] 소켓 통신 예외 발생: {e}")


def main():
    # 검증 모드 환경변수 설정
    env = os.environ.copy()
    env["TEST_VERIFY_MODE"] = "true"
    env["YOLO26N_OBJECT_DET"] = "nonexistent.pt"  # MockDetector 강제 활성화

    # FastAPI Uvicorn 서버를 subprocess로 기동
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]

    print("==================================================")
    print(" 0. 검증 모드로 FastAPI uvicorn 서버 기동 시도")
    print("==================================================")

    server_process = subprocess.Popen(  # nosec B603
        uvicorn_cmd, cwd=project_root, env=env, stdout=sys.stdout, stderr=sys.stderr
    )

    # 서버 바인딩 로그 대기
    print("-> uvicorn 서버가 8000 포트에 바인딩될 때까지 로그 대기 중...")
    time.sleep(3.0)

    try:
        # 비동기 클라이언트 시뮬레이션 기동
        asyncio.run(run_client_simulation())
    finally:
        # uvicorn 서버 강제 정리
        print("\n==================================================")
        print(" 2. 검증 완료 - FastAPI 백그라운드 서버 정리 중...")
        print("==================================================")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("-> 백그라운드 서버 프로세스 정상 종료 완료.")


if __name__ == "__main__":
    main()
