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
# - STT 텍스트를 기존 오케스트레이션 입력 형식으로 감싸는 어댑터다.
# - LLM 신규 구현 없이 기존 server/orchestration 경로를 재사용한다.
# - 일반 대화 입력은 오케스트레이션으로 전달하고, 네비게이션 제어 입력은 로컬 분기로 처리한다.
#
# [하드 코딩 부분]
# - 상태 문자열(IDLE/WAITING_FOR_DESTINATION/NAVIGATING), source 값, 키워드 리스트는 핵심 계약값이다.
# - 하드코딩 작성법:
#   1) 문자열은 오탈자 방지를 위해 한 곳에 모아 관리한다.
#   2) 변경 시 테스트(source/status 단언)와 함께 수정한다.
#   3) 사용자 안내 문구는 서비스 톤앤매너와 일치하게 유지한다.


class SttToLlmBridge:
    @staticmethod
    def build_orch_input(stt_result: SttTranscribeResult) -> dict:
        """
        [바이브 코딩 부분]
        STT 결과를 기존 run_orchestrator(state) 입력 형태로 변환한다.
        - event: 오케스트레이션 추적용 메타
        - rag_context: STT 원문을 RAG 질의 문맥으로 전달
        - validation_*: 후속 단계에서 검증 결과를 누적할 기본 슬롯
        """
        validate_stt_bridge_config()

        # [하드 코딩 부분 - 핵심]
        # source="stt"와 detected_classes=[STT_ORCH_CLASS_NAME]는
        # 파이프라인 라우팅 규칙의 기준값이므로 임의 변경하지 않는다.
        return {
            "event" : {
                "event_id" : f"stt-{stt_result.saved_file}",
                "risk_hint" : STT_ORCH_RISK_HINT,
                "source" : "stt",
            },
            "detected_classes" : [STT_ORCH_CLASS_NAME],
            "positions" : [""],
            "risk_level" : STT_ORCH_RISK_HINT,
            "rag_context" : stt_result.text,
            "retry_count" : 0,
            "verified" : False,
            "validation_errors" : [],
        }

    async def invoke_existing_llm(self, stt_result: SttTranscribeResult) -> dict:
        """
        [바이브 코딩 부분]
        처리 순서:
        1) 입력 정규화/빈 입력 폴백
        2) 네비게이션 제어 명령 분기
        3) 목적지 설정 분기
        4) 일반 입력 오케스트레이션 호출

        [하드 코딩 부분 - 핵심]
        - 빈 입력 source: stt-bridge-empty
        - 예외 폴백 source: stt-bridge-error
        - 네비게이션 제어 source: navigation-setup-*

        하드코딩 작성법:
        - source 값은 모니터링/테스트 키로 쓰이므로 문자열을 바꾸면 테스트와 로그 파서를 같이 수정한다.
        - 사용자 안내 문구는 짧고 즉시 행동 가능한 문장으로 고정한다.
        """
        validate_stt_bridge_config()

        # [바이브 코딩 부분] 공백/None 입력을 동일 규칙으로 처리하기 위한 정규화 단계
        normalized_text = (stt_result.text or "").strip()

        # [하드 코딩 부분 - 핵심] 입력 없음은 안전 우선 안내로 즉시 종료한다.
        if not normalized_text:
            return {
                "guidance_text": "입력이 없어 정지하세요",
                "used_fallback_llm": True,
                "source": "stt-bridge-empty",
            }

        # [하드 코딩 부분 - 핵심]
        # 현재 구현은 단일 디바이스 기준(default_device)으로 상태를 조회한다.
        # 다중 디바이스 확장 시 STT 세션 식별자를 device_id로 치환해야 한다.
        device_id = "default_device"
        from server.navigation.manager import nav_manager
        current_status = nav_manager.get_status(device_id)

        # [하드 코딩 부분 - 핵심]
        # 네비게이션 기능 켜기(Wake-up) 명령어 판별
        # 작성법: 동의어는 짧은 구문 위주로 추가하고, 의미가 겹치는 표현은 중복 등록하지 않는다.
        wakeup_keywords = ["네비게이션 켜줘", "길안내 시작해줘", "길안내 시작", "네비게이션 기능 켜줘", "네비게이션 시작"]
        is_wakeup = any(kw in normalized_text for kw in wakeup_keywords)

        # [하드 코딩 부분 - 핵심]
        # 네비게이션 기능 끄기(Shutdown) 명령어 판별
        # 작성법: 종료/중단 의도를 가진 문장만 포함해 오탐을 줄인다.
        shutdown_keywords = ["네비게이션 꺼줘", "길안내 종료해줘", "길안내 종료", "네비게이션 기능 꺼줘", "길안내 꺼줘"]
        is_shutdown = any(kw in normalized_text for kw in shutdown_keywords)

        if is_wakeup:
            # [바이브 코딩 부분] Wake-up 이후 목적지 발화를 받기 위한 상태 전이
            nav_manager.set_status(device_id, "WAITING_FOR_DESTINATION")
            return {
                "guidance_text": "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요.",
                "used_fallback_llm": True,
                "source": "navigation-setup-wakeup",
            }

        elif is_shutdown:
            # [바이브 코딩 부분] 종료 요청 시 경로 캐시와 상태를 초기화
            nav_manager.update_route(device_id, [])
            nav_manager.set_status(device_id, "IDLE")
            return {
                "guidance_text": "네비게이션 안내를 종료합니다.",
                "used_fallback_llm": True,
                "source": "navigation-setup-shutdown",
            }

        elif current_status == "WAITING_FOR_DESTINATION":
            # [하드 코딩 부분 - 핵심]
            # 목적지 파싱 규칙: 조사/설정 어미를 제거해 POI 검색용 핵심 문자열을 만든다.
            # 작성법: replace 체인은 짧게 유지하고, 복잡해지면 정규식/파서 함수로 분리한다.
            destination = normalized_text.replace("목적지는", "").replace("으로", "").replace("로", "").replace("설정", "").strip()
            
            from server.navigation.server import helper_search_poi, helper_fetch_route
            
            # [바이브 코딩 부분] POI 조회와 경로 계산을 순차 수행해 세션 경로를 구성
            try:
                session = nav_manager._get_or_create_session(device_id)

                # [하드 코딩 부분 - 핵심]
                # GPS 미수신 시 서울역 인근 좌표를 기본 시작점으로 사용한다.
                # 작성법: 폴백 좌표는 운영 기준점 하나로 고정하고 문서화한다.
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

                        # [바이브 코딩 부분] Point 지오메트리만 추출해 TTS 안내용 웨이포인트로 변환
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
                        
                        # [하드 코딩 부분 - 핵심]
                        # 상태 전이 순서: route 갱신 -> NAVIGATING 전환
                        # 작성법: 상태를 먼저 바꾸면 route 비어있는 구간이 생길 수 있으므로 현재 순서를 유지한다.
                        nav_manager.update_route(device_id, session_waypoints)
                        nav_manager.set_status(device_id, "NAVIGATING")
                        return {
                            "guidance_text": f"{destination}까지 보행 경로 안내를 시작합니다.",
                            "used_fallback_llm": True,
                            "source": "navigation-setup-success",
                        }
            except Exception as ex:
                # [바이브 코딩 부분] 경로 수립 예외는 음성 재입력을 유도해 세션 지속성을 지킨다.
                print(f"[STT BRIDGE] Failed to setup route via voice: {ex}")

            # [하드 코딩 부분 - 핵심] 실패 시 WAITING 상태를 유지해 재입력을 받을 수 있게 한다.
            return {
                "guidance_text": "목적지를 찾지 못했습니다. 다시 말씀해 주세요.",
                "used_fallback_llm": True,
                "source": "navigation-setup-fail",
            }

        # [바이브 코딩 부분] 개인정보 최소화를 위해 원문 대신 최소 메타만 보존
        _text_len = len(normalized_text)
        _model_name = stt_result.model_name
        _saved_file = stt_result.saved_file

        try:
            # [바이브 코딩 부분] 일반 발화는 기존 오케스트레이션 경로로 위임
            orch_input = self.build_orch_input(stt_result)
            orch_result = await run_orchestrator(orch_input)
            return {
                "guidance_text": orch_result.get("guidance_text", ""),
                "used_fallback_llm": orch_result.get("used_fallback_llm", False),
                "source": "stt-bridge",
            }
        except Exception:
            # [하드 코딩 부분 - 핵심]
            # 오케스트레이션 장애 시 안전 멈춤 멘트를 고정 반환한다.
            # 작성법: 예외 메시지를 사용자에게 직접 노출하지 말고, 내부 추적용 메타만 유지한다.
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

        [하드 코딩 부분 - 핵심]
        템플릿 source는 stt-template으로 고정해 실운영(source=stt-bridge)와 구분한다.
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
