import pytest
from fastapi.testclient import TestClient
import json
import time

from server.main import app
from server.api.auth import REGISTERED_DEVICES

client = TestClient(app)

def test_websocket_handshake_and_ping():
    """웹소켓 인증 및 ping-pong 정상 동작 확인"""
    # 임시로 유효한 디바이스 추가
    test_device = "dev-test-001"
    test_token = "token-test-001"
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
    test_token = "token-test-002"
    REGISTERED_DEVICES[test_device] = test_token

    with client.websocket_connect(f"/ws/detect?device_id={test_device}") as websocket:
        websocket.receive_json() # welcome
        
        websocket.send_json({"type": "hello", "token": test_token})
        websocket.receive_json() # auth_ok

        # detection 메시지 전송
        test_payload = {
            "type": "detection",
            "payload": {
                "event_id": "evt-123",
                "timestamp": "2026-07-01T00:00:00",
                "stream": "cognitive",
                "thumbnail_jpeg_b64": "dummy"
            }
        }
        websocket.send_json(test_payload)
        
        ack_msg = websocket.receive_json()
        assert ack_msg["type"] == "ack"
        assert ack_msg["event_id"] == "evt-123"
