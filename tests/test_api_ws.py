import time

import cv2
import numpy as np
from fastapi.testclient import TestClient

from server.api.auth import REGISTERED_DEVICES
from server.main import app

client = TestClient(app)


def _make_jpeg_bytes(width: int = 640, height: int = 480) -> bytes:
    frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    assert ok, "JPEG 인코딩 실패"
    return buf.tobytes()


def test_websocket_handshake_and_ping():
    """웹소켓 인증 및 ping-pong 정상 동작 확인"""
    # 임시로 유효한 디바이스 추가
    test_device = "dev-test-001"
    test_token = "token-test-001"  # noqa: S105
    REGISTERED_DEVICES[test_device] = test_token

    with client.websocket_connect(f"/ws/detect?device_id={test_device}") as websocket:
        # 1. welcome 수신
        welcome_msg = websocket.receive_json()
        assert welcome_msg["type"] == "welcome"
        assert welcome_msg["session_id"] == test_device

        # 2. hello (인증) 전송
        websocket.send_json({"type": "hello", "token": test_token})
        auth_ok = websocket.receive_json()
        assert auth_ok["type"] == "auth_ok"
        assert auth_ok["device_id"] == test_device

        # 3. ping-pong 테스트
        websocket.send_json({"type": "ping", "ts": time.time()})
        pong_msg = websocket.receive_json()
        assert pong_msg["type"] == "pong"
        assert "ts" in pong_msg


def test_websocket_detection_ack():
    """detection 이벤트 수신 시 ack 반환 여부 확인"""
    test_device = "dev-test-002"
    test_token = "token-test-002"  # noqa: S105
    REGISTERED_DEVICES[test_device] = test_token

    with client.websocket_connect(f"/ws/detect?device_id={test_device}") as websocket:
        websocket.receive_json()  # welcome

        websocket.send_json({"type": "hello", "token": test_token})
        websocket.receive_json()  # auth_ok

        # detection 메시지 전송
        test_payload = {
            "type": "detection",
            "payload": {
                "event_id": "evt-123",
                "timestamp": "2026-07-01T00:00:00",
                "stream": "cognitive",
                "thumbnail_jpeg_b64": "dummy",
            },
        }
        websocket.send_json(test_payload)

        ack_msg = websocket.receive_json()
        assert ack_msg["type"] == "ack"
        assert ack_msg["event_id"] == "evt-123"


def test_websocket_detection_binary_transport():
    """바이너리 전송 프로토콜: JSON 메타(transport=binary) + 바이너리 프레임 순차 전송 시
    ack가 정상 응답되는지 실제 /ws/detect 엔드포인트를 통해 검증 (base64 미경유)."""
    test_device = "dev-test-003"
    test_token = "token-test-003"  # noqa: S105
    REGISTERED_DEVICES[test_device] = test_token

    with client.websocket_connect(f"/ws/detect?device_id={test_device}") as websocket:
        websocket.receive_json()  # welcome

        websocket.send_json({"type": "hello", "token": test_token})
        websocket.receive_json()  # auth_ok

        websocket.send_json(
            {
                "type": "detection",
                "payload": {
                    "event_id": "evt-binary-1",
                    "frame_id": 1,
                    "stream": "reflex",
                    "transport": "binary",
                },
            }
        )
        websocket.send_bytes(_make_jpeg_bytes())

        ack_msg = websocket.receive_json()
        assert ack_msg["type"] == "ack"
        assert ack_msg["event_id"] == "evt-binary-1"
        # 2026-07-24(a4ef642) 이후 바이너리 경로는 ACK를 먼저 보내고 JPEG 디코드를
        # 백그라운드(_decode_and_route_bg)에서 수행한다. 따라서 ACK의 decode_ms는
        # 디코드 소요가 아니라 "아직 측정 전"을 뜻하는 0.0이 정상이다. 계약은
        # 필드 존재와 음수가 아님까지만 검증한다.
        assert isinstance(ack_msg["decode_ms"], (int, float))
        assert ack_msg["decode_ms"] >= 0


def test_websocket_binary_frame_without_pending_meta_is_ignored():
    """메타(transport=binary) 없이 바이너리 프레임만 도착하면 무시하고 다음 메시지를 정상 처리."""
    test_device = "dev-test-004"
    test_token = "token-test-004"  # noqa: S105
    REGISTERED_DEVICES[test_device] = test_token

    with client.websocket_connect(f"/ws/detect?device_id={test_device}") as websocket:
        websocket.receive_json()  # welcome
        websocket.send_json({"type": "hello", "token": test_token})
        websocket.receive_json()  # auth_ok

        # 메타 없이 고아 바이너리 프레임 전송 (무시되어야 함)
        websocket.send_bytes(_make_jpeg_bytes())

        # 이어서 정상 ping을 보내면 여전히 응답이 와야 함 (루프가 멈추지 않음)
        websocket.send_json({"type": "ping", "ts": time.time()})
        pong_msg = websocket.receive_json()
        assert pong_msg["type"] == "pong"


def test_unauthenticated_duplicate_does_not_evict_valid_session():
    """같은 device_id의 미인증 연결이 기존 정상 세션을 끊지 못해야 한다."""
    test_device = "dev-test-session-protection"
    test_token = "token-test-session-protection"  # noqa: S105
    REGISTERED_DEVICES[test_device] = test_token

    with client.websocket_connect(f"/ws/detect?device_id={test_device}") as valid_ws:
        valid_ws.receive_json()
        valid_ws.send_json({"type": "hello", "token": test_token})
        assert valid_ws.receive_json()["type"] == "auth_ok"

        with client.websocket_connect(f"/ws/detect?device_id={test_device}") as attacker_ws:
            attacker_ws.receive_json()
            attacker_ws.send_json({"type": "hello", "token": "invalid-token"})
            assert attacker_ws.receive_json()["code"] == "auth_failed"

        valid_ws.send_json({"type": "ping"})
        assert valid_ws.receive_json()["type"] == "pong"
