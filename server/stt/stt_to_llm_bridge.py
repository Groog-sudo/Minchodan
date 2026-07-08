# -*- coding: utf-8 -*-
import sys
import re
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.orchestration import run_orchestrator
from .stt_config import STT_ORCH_CLASS_NAME, STT_ORCH_RISK_HINT
from .stt_runtime import validate_stt_bridge_config
from .stt_schema import SttTranscribeResult


# ============================================================
# STT -> 기존 LLM 브리지
# ============================================================
# [바이브 코딩 부분]
# - STT 텍스트를 기존 오케스트레이션 입력 형식으로 감싸는 어댑터.
# - LLM 신규 구현 없이 기존 server/orchestration 경로를 재사용.
#
# [하드 코딩 부분]
# - 어떤 위험도 기본값을 쓸지, STT 전용 프롬프트 힌트 규칙은 담당자가 직접 정의.


class SttToLlmBridge:
    @staticmethod
    def build_orch_input(stt_result: SttTranscribeResult) -> dict:
        """
        [바이브 코딩 부분]
        STT 결과를 기존 run_orchestrator(state) 입력 형태로 변환한다.
        """
        validate_stt_bridge_config()

        return {
            "event": {
                "event_id": f"stt-{stt_result.saved_file}",
                "risk_hint": STT_ORCH_RISK_HINT,
                "source": "stt",
            },
            "detected_classes": [STT_ORCH_CLASS_NAME],
            "positions": [""],
            "risk_level": STT_ORCH_RISK_HINT,
            "rag_context": stt_result.text,
            "retry_count": 0,
            "verified": False,
            "validation_errors": [],
        }

    async def invoke_existing_llm(self, stt_result: SttTranscribeResult) -> dict:
        """
        [하드 코딩 부분]
        STT 텍스트를 기존 오케스트레이션으로 전달하고 결과를 표준 응답 dict로 매핑한다.
        빈 입력은 stt-bridge-empty 폴백, 실행 예외는 stt-bridge-error 폴백으로 처리한다.
        원문 텍스트 대신 길이/모델명/파일명 메타 정보만 내부 처리에 사용한다.
        """
        validate_stt_bridge_config()

        normalized_text = (stt_result.text or "").strip()
        if not normalized_text:
            return {
                "guidance_text": "입력이 없어 정지하세요",
                "used_fallback_llm": True,
                "source": "stt-bridge-empty",
            }

        device_id = "default_device"
        from server.navigation.manager import nav_manager
        current_status = nav_manager.get_status(device_id)

        # 1. 네비게이션 기능 켜기(Wake-up) 명령어 판별
        wakeup_keywords = ["네비게이션 켜줘", "길안내 시작해줘", "길안내 시작", "네비게이션 기능 켜줘", "네비게이션 시작"]
        is_wakeup = any(kw in normalized_text for kw in wakeup_keywords)

        # 2. 네비게이션 기능 끄기(Shutdown) 명령어 판별
        shutdown_keywords = ["네비게이션 꺼줘", "길안내 종료해줘", "길안내 종료", "네비게이션 기능 꺼줘", "길안내 꺼줘"]
        is_shutdown = any(kw in normalized_text for kw in shutdown_keywords)

        if is_wakeup:
            # 상태를 목적지 대기 상태로 변경
            nav_manager.set_status(device_id, "WAITING_FOR_DESTINATION")
            return {
                "guidance_text": "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요.",
                "used_fallback_llm": True,
                "source": "navigation-setup-wakeup",
            }

        elif is_shutdown:
            # 상태를 IDLE로 변경 및 경로 제거
            nav_manager.update_route(device_id, [])
            nav_manager.set_status(device_id, "IDLE")
            return {
                "guidance_text": "네비게이션 안내를 종료합니다.",
                "used_fallback_llm": True,
                "source": "navigation-setup-shutdown",
            }

        elif current_status == "WAITING_FOR_DESTINATION":
            # 목적지 입력으로 인식하여 TMAP 경로 수립 시도
            destination = normalized_text.replace("목적지는", "").replace("으로", "").replace("로", "").replace("설정", "").strip()
            
            from server.navigation.server import helper_search_poi, helper_fetch_route
            
            # 동기 검색 및 경로 호출 수행
            try:
                session = nav_manager._get_or_create_session(device_id)
                curr_lat = session.lat if session.lat is not None else 37.5560
                curr_lon = session.lon if session.lon is not None else 126.9722
                
                start_poi = {
                    "name": "내 실시간 위치",
                    "x": str(curr_lon),
                    "y": str(curr_lat)
                }
                
                end_poi = helper_search_poi(destination)
                if end_poi:
                    route_data = helper_fetch_route(start_poi, end_poi)
                    if route_data:
                        session_waypoints = []
                        features = route_data.get("features", [])
                        point_idx = 1
                        for feature in features:
                            geom = feature.get("geometry", {})
                            if geom.get("type") == "Point":
                                coords = geom.get("coordinates", [])
                                props = feature.get("properties", {})
                                session_waypoints.append({
                                    "index": point_idx,
                                    "lat": float(coords[1]),
                                    "lon": float(coords[0]),
                                    "description": props.get("description", "").strip(),
                                    "facility_type": props.get("facilityType")
                                })
                                point_idx += 1
                        
                        nav_manager.update_route(device_id, session_waypoints)
                        nav_manager.set_status(device_id, "NAVIGATING")
                        return {
                            "guidance_text": f"{destination}까지 보행 경로 안내를 시작합니다.",
                            "used_fallback_llm": True,
                            "source": "navigation-setup-success",
                        }
            except Exception as ex:
                print(f"[STT BRIDGE] Failed to setup route via voice: {ex}")

            # 경로 수립 실패 시 멘트 리턴 (상태는 계속 유지)
            return {
                "guidance_text": "목적지를 찾지 못했습니다. 다시 말씀해 주세요.",
                "used_fallback_llm": True,
                "source": "navigation-setup-fail",
            }

        # 원문 텍스트는 기록하지 않고 메타 정보만 보존한다.
        _text_len = len(normalized_text)
        _model_name = stt_result.model_name
        _saved_file = stt_result.saved_file

        try:
            orch_input = self.build_orch_input(stt_result)
            orch_result = await run_orchestrator(orch_input)
            return {
                "guidance_text": orch_result.get("guidance_text", ""),
                "used_fallback_llm": orch_result.get("used_fallback_llm", False),
                "source": "stt-bridge",
            }
        except Exception:
            _ = (_text_len, _model_name, _saved_file)
            return {
                "guidance_text": "안전을 위해 잠시 멈추고 주변을 확인하세요",
                "used_fallback_llm": True,
                "source": "stt-bridge-error",
            }

    async def invoke_existing_llm_template(self, stt_result: SttTranscribeResult) -> dict:
        """
        [바이브 코딩 부분]
        최소 템플릿 실행 경로.
        실제 운영에서는 invoke_existing_llm()을 직접 작성해서 사용한다.
        """
        if not stt_result.has_input:
            return {
                "guidance_text": "입력이 없어 정지하세요",
                "used_fallback_llm": True,
                "source": "stt-template",
            }

        orch_input = self.build_orch_input(stt_result)
        orch_result = await run_orchestrator(orch_input)
        return {
            "guidance_text": orch_result.get("guidance_text", ""),
            "used_fallback_llm": orch_result.get("used_fallback_llm", False),
            "source": "stt-template",
        }
