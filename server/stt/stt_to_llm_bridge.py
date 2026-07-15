import sys
import time
from typing import ClassVar

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from server.orchestration import run_orchestrator
from server.rag.convenience_rag import (
    answer_convenience_question,
    looks_like_convenience_query,
)

from .stt_config import STT_ORCH_CLASS_NAME, STT_ORCH_RISK_HINT
from .stt_runtime import validate_stt_bridge_config
from .stt_schema import SttTranscribeResult

# [하드 코딩 부분 - 핵심] 자유 질의응답 진입 트리거 문구.
# 2026-07-10 추가: 위치 질문("가장 가까운 지하철역이 어디야?") 등 일반 발화가 장애물
# 회피 오케스트레이터(run_orchestrator)로 들어가 무관한 안내 문장을 만들던 문제
# (실기기 실측 확인)를 해결하기 위해, 명시적 wake-word로 자유 질문 모드를 분리한다.
QUESTION_TRIGGER_KEYWORDS = ["질문할게", "질문할래", "질문 있어", "질문이요", "물어볼게"]
# 목적지 대기 중에도 "질문처럼 보이는" 발화는 POI 목적지가 아니라 자유 질문으로 보낸다.
QUESTION_HINT_WORDS = (
    "뭐",
    "무엇",
    "어디",
    "언제",
    "몇",
    "왜",
    "어떻게",
    "누가",
    "얼마",
    "무슨",
)

# [하드 코딩 부분 - 핵심] 2026-07-10 추가: "길댕아" 2단계 wake-word.
# "네비게이션 켜줘"는 "네비게이션/내비게이션" 표기 변이로 인식이 불안정했다(실기기
# 실측). "길댕아"는 짧고 표기 변이가 없어 더 안정적으로 인식되며, 온보딩 안내
# ("길댕입니다")와 브랜드 일관성도 맞는다. 기존 단일 트리거(네비게이션 켜줘/질문할게)는
# 하위 호환을 위해 그대로 유지하고, 이 2단계 흐름을 추가 진입점으로 둔다.
#
# 2026-07-10 정정(실기기 실측): "길댕아"조차 "길대가"/"결댕아"/"길땡아" 등으로 오인식되는
# 사례가 반복 관측됐다. 변형을 하나씩 목록에 추가하는 방식은 한계가 있어(다음 오인식은
# 또 못 잡음), 정확 문자열 목록 대신 편집거리(Levenshtein) 기반 퍼지 매칭으로 전환한다 -
# "길댕"과 편집거리 1 이하인 2글자 구간이 발화에 있으면 wake로 인정한다.
GILDAENG_ROOT = "길댕"
GILDAENG_FUZZY_MAX_DISTANCE = 1

GILDAENG_NAV_INTENT_KEYWORDS = [
    "길찾아줘",
    "길 찾아줘",
    "길찾아 줘",
    "네비게이션 켜줘",
    "길안내 시작해줘",
    "길안내 시작",
    "네비게이션 기능 켜줘",
    "네비게이션 시작",
]
# 2026-07-10 정정(실기기 실측): "길댕아" 프롬프트 자체가 "질문 받을까요?"라고 묻는데
# "물어볼게"만 받아주면 사용자가 프롬프트 표현 그대로 "질문할게"라고 답했을 때 튕겨나가
# 재질문 루프에 빠졌다. QUESTION_TRIGGER_KEYWORDS(기존 직접 트리거)와 합쳐 받는다.
GILDAENG_QUESTION_INTENT_KEYWORDS = [
    "물어볼게",
    "물어볼래",
    "물어볼게요",
    *QUESTION_TRIGGER_KEYWORDS,
]


def _levenshtein(a: str, b: str) -> int:
    """외부 의존성 없이 쓰는 표준 편집거리(Levenshtein distance) 구현."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[-1]


def _is_gildaeng_wake(text: str) -> bool:
    """발화 안에 "길댕"과 편집거리 1 이하인 2글자 구간이 있으면 wake로 인정한다.

    2026-07-14 정정: "길찾아줘"의 부분문자열 "길찾"이 "길댕"과 편집거리 1이라
    wake 오인되던 버그(목적지 대기 직후 IDLE로 되돌아가는 루프)를 막기 위해,
    네비/질문 인텐트 키워드가 포함된 발화는 wake로 보지 않는다.
    """
    if not text:
        return False
    # 인텐트 키워드는 wake보다 우선 (부분문자열 퍼지 매칭 오인 방지)
    if any(kw in text for kw in GILDAENG_NAV_INTENT_KEYWORDS):
        return False
    if any(kw in text for kw in GILDAENG_QUESTION_INTENT_KEYWORDS):
        return False
    root_len = len(GILDAENG_ROOT)
    for i in range(len(text) - root_len + 1):
        window = text[i : i + root_len]
        if _levenshtein(window, GILDAENG_ROOT) <= GILDAENG_FUZZY_MAX_DISTANCE:
            return True
    return False


# 2026-07-11 추가: 자기-에코(앱 자신의 TTS 안내문이 마이크로 다시 들어가 전사되는 현상)
# 방지용 short-term 메모리. device_id별로 최근 전송한 안내문과 시각을 보관한다.
ECHO_MEMORY_TTL_SEC = 10.0
ECHO_SIMILARITY_THRESHOLD = 0.6


def _is_self_echo(transcript: str, recent_guidance: str) -> bool:
    """전사 결과가 앱이 방금 재생한 안내문과 유사한지 판정한다.

    TTS 안내문이 스피커로 재생되는 도중 사용자가 녹음 버튼을 누르면 마이크가 그
    안내문을 그대로 주워들어 Whisper가 전사한다 - 이 전사가 웨이크업/인텐트 키워드를
    포함하면 메아리 루프(안내문 -> 녹음 -> 전사 -> 웨이크업 재발동 -> 동일 안내문)가
    발생한다(실기기 13:24:07 로그로 확인).

    판정 기준: 안내문의 핵심 키워드 구간이 전사 결과에 포함되어 있으면 에코로 인정한다.
    전사는 Whisper의 오인식이 섞일 수 있으므로, 편집거리가 짧은 부분 문자열 매칭을
    사용한다 (전사가 안내문보다 짧거나 중간에 끊길 수 있으므로 안내문의 부분이 전사에
    있는지 확인한다).
    """
    if not recent_guidance or not transcript:
        return False
    # 안내문이 전사에 거의 그대로 포함되어 있으면 확정 에코
    if recent_guidance in transcript:
        return True
    # 전사가 안내문의 접두사/접미사인 경우 (끊겨 녹음)
    if transcript in recent_guidance and len(transcript) >= 4:
        return True
    # 안내문의 핵심 구간(처음 10자)이 전사에 편집거리 2 이내로 포함되어 있으면 에코
    key_fragment = recent_guidance[:10]
    if len(key_fragment) >= 3:
        for i in range(len(transcript) - len(key_fragment) + 1):
            window = transcript[i : i + len(key_fragment)]
            if _levenshtein(window, key_fragment) <= 2:
                return True
    return False


# [하드 코딩 부분 - 핵심] 근접 POI 질의 판별용 키워드.
# "가까운/근처/주변" + 장소 유형이 함께 있으면 T맵 실거리 검색으로 답한다(LLM 환각 방지).
NEARBY_TRIGGER_WORDS = ["가까운", "가까이", "근처", "주변", "가장"]
POI_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "지하철역": ["지하철역", "전철역", "지하철", "전철"],
    "버스정류장": ["버스정류장", "버스 정류장", "정류장"],
    "편의점": ["편의점"],
    "화장실": ["화장실"],
    "약국": ["약국"],
    "병원": ["병원"],
    "카페": ["카페"],
    "은행": ["은행"],
    "주차장": ["주차장"],
}


def _looks_like_question(text: str) -> bool:
    """목적지 POI가 아니라 일반 질문으로 보이는지 휴리스틱 판별."""
    if not text:
        return False
    if "?" in text or "？" in text:  # noqa: RUF001
        return True
    return any(w in text for w in QUESTION_HINT_WORDS)


QUESTION_SYSTEM_PROMPT = """당신은 시각장애인 보행자를 돕는 음성 비서입니다.
사용자의 질문에 짧고 명확한 한국어 존댓말로 답변하세요.

[규칙]
1. 2문장 이내로 간결하게 답합니다.
2. 실시간 위치나 실제 장소 정보를 모르면 추측해서 답하지 말고 "정확히 알 수 없습니다"라고 답합니다.
3. 보행 중 안전을 해치지 않는 답변을 우선합니다.
"""


def _extract_poi_category(text: str) -> str | None:
    for canonical, variants in POI_CATEGORY_KEYWORDS.items():
        if any(v in text for v in variants):
            return canonical
    return None


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
    # 2026-07-11: device_id별 최근 전송 안내문 캐시 (자기-에코 감지용).
    # {device_id: (guidance_text, timestamp_monotonic)}
    _recent_guidance: ClassVar[dict[str, tuple[str, float]]] = {}

    @classmethod
    def _record_guidance(cls, device_id: str, guidance_text: str) -> None:
        """클라이언트에 전송할 안내문을 에코 감지용 메모리에 기록한다."""
        if guidance_text:
            cls._recent_guidance[device_id] = (guidance_text, time.monotonic())

    @classmethod
    def _check_self_echo(cls, device_id: str, transcript: str) -> bool:
        """전사 결과가 최근 안내문의 에코인지 확인한다. TTL 경과 시 자동 정리."""
        entry = cls._recent_guidance.get(device_id)
        if not entry:
            return False
        guidance_text, ts = entry
        if time.monotonic() - ts > ECHO_MEMORY_TTL_SEC:
            del cls._recent_guidance[device_id]
            return False
        return _is_self_echo(transcript, guidance_text)

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

    async def invoke_existing_llm(self, stt_result: SttTranscribeResult, device_id: str) -> dict:
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

        # [바이브 코딩 부분] 2026-07-10 추가: Whisper가 "네비게이션"을 표준 표기인
        # "내비게이션"으로 인식하는 경우가 실기기에서 관측됨(같은 발화가 매번 다르게
        # 전사됨) - 키워드 리스트마다 두 표기를 중복 등록하는 대신 여기서 한 번만
        # 표준화해 이후 모든 키워드 매칭이 "네비게이션" 표기만 신경 쓰면 되게 한다.
        normalized_text = normalized_text.replace("내비게이션", "네비게이션")

        # [하드 코딩 부분 - 핵심] 입력 없음은 안전 우선 안내로 즉시 종료한다.
        if not normalized_text:
            return {
                "guidance_text": "음성이 인식되지 않았어요. 다시 말씀해 주세요.",
                "used_fallback_llm": True,
                "source": "stt-bridge-empty",
            }

        # 2026-07-11 추가: 자기-에코 감지. TTS 안내문이 재생되는 도중 사용자가 녹음
        # 버튼을 누르면 스피커 소리가 마이크로 다시 들어가 전사된다(음향 블리드). 이
        # 전사가 웨이크업/인텐트 키워드를 포함하면 메아리 루프가 발생한다(실기기
        # 13:24:07 로그 확인: "길찾아줘 또는 물어볼게 중 하나로 다시 말씀해주세요"
        # 안내문이 통째로 전사됨). 최근 전송한 안내문과 유사하면 에코로 판정해
        # 클라이언트에 응답을 보내지 않는다(ws_router에서 source별 스킵).
        if self._check_self_echo(device_id, normalized_text):
            print(
                f"[STT BRIDGE] 자기-에코 감지(안내문 재녹음), 무시: "
                f"device_id={device_id}, text_len={len(normalized_text)}"
            )
            return {
                "guidance_text": "",
                "used_fallback_llm": True,
                "source": "stt-echo-detected",
            }

        # 2026-07-10 정정(실기기 실측): device_id를 "default_device"로 하드코딩했더니
        # 목적지 설정(WAITING_FOR_DESTINATION/NAVIGATING)은 이 가짜 ID의 세션에 저장되는
        # 반면, GPS 갱신(ws_router.py의 realtime_gps/detection 핸들러)과 실제 turn-by-turn
        # 안내 조회(DetectionConsumer._send_cognitive_guide -> get_combined_guidance)는
        # 진짜 device_id("dev-001")의 세션을 본다 - 서로 다른 세션이라 목적지는 설정돼도
        # 길안내 음성이 절대 나올 수 없었다. 호출측(ws_router.py)이 넘겨주는 실제
        # device_id를 그대로 쓴다.
        from server.navigation.manager import nav_manager

        current_status = nav_manager.get_status(device_id)

        # [하드 코딩 부분 - 핵심]
        # 자유 질의응답 모드 최우선 처리: "질문할게" 등으로 진입한 다음 발화는 그
        # 내용과 무관하게(네비게이션 키워드가 우연히 섞여 있어도) 질문 자체로 취급한다.
        # 2026-07-10 정정(실기기 실측): 무음/빈 인식 응답 뒤에도 대기 상태가 유지되는데,
        # 사용자가 트리거 문구("질문할게")를 다시 말하면 그게 재트리거가 아니라 "질문
        # 내용 그 자체"로 처리돼 LLM이 엉뚱하게 답하는 문제가 있었다. 재입력이 트리거
        # 문구 자체면 질문으로 소비하지 않고 대기 상태를 유지한 채 재안내한다.
        if nav_manager.is_awaiting_question(device_id):
            if any(kw in normalized_text for kw in QUESTION_TRIGGER_KEYWORDS):
                return {
                    "guidance_text": "네, 질문해 주세요.",
                    "used_fallback_llm": True,
                    "source": "question-mode-retrigger",
                }
            nav_manager.set_awaiting_question(device_id, False)
            return await self._answer_free_question(device_id, normalized_text)

        # [하드 코딩 부분 - 핵심]
        # "길댕아" 2단계 wake-word 대기 처리. 옵션 A(엄격 매칭) 채택: "길찾아줘"/
        # "물어볼게" 둘 중 정확히 하나만 인정하고, 그 외 발화는 추측하지 않고 재질문한다
        # (애매한 발화를 억지로 해석하다 생긴 과거 오류 재발 방지 - 질문 모드 재트리거
        # 수정과 동일한 원칙).
        if nav_manager.is_awaiting_intent(device_id):
            is_nav_intent = any(kw in normalized_text for kw in GILDAENG_NAV_INTENT_KEYWORDS)
            is_question_intent = any(
                kw in normalized_text for kw in GILDAENG_QUESTION_INTENT_KEYWORDS
            )
            # 2026-07-11 정정(실기기 실측): wake 재호출 체크가 nav/question intent보다
            # 먼저였던 것을 뒤로 이동했다. 사용자가 "길댕아 길찾아줘"라고 말하면
            # _is_gildaeng_wake가 True가 되어 intent 매칭 전에 리턴해버려, 목적지
            # 대기 상태로 진입하지 못하고 같은 안내만 반복하는 문제(5회 반복 로그
            # 확인)가 있었다. 실제 인텐트 키워드가 포함되어 있으면 그것을 우선 처리한다.
            if is_nav_intent:
                nav_manager.set_awaiting_intent(device_id, False)
                nav_manager.set_status(device_id, "WAITING_FOR_DESTINATION")
                return {
                    "guidance_text": "네비게이션 기능을 시작합니다. 목적지를 말씀해 주세요.",
                    "used_fallback_llm": True,
                    "source": "navigation-setup-wakeup",
                }
            elif is_question_intent:
                nav_manager.set_awaiting_intent(device_id, False)
                nav_manager.set_awaiting_question(device_id, True)
                return {
                    "guidance_text": "네, 질문해 주세요.",
                    "used_fallback_llm": True,
                    "source": "question-mode-wakeup",
                }
            # 2026-07-10 정정(실기기 실측): 이미 대기 중인데 "길댕아"를 또 말하면
            # (재확인 습관) "길찾아줘/물어볼게로 다시 말씀해주세요" 오류 메시지가 나가
            # 혼란스러웠다. 재호출 wake는 같은 안내를 반복하며 대기를 유지한다
            # (질문 모드 재트리거 수정과 동일 원칙).
            elif _is_gildaeng_wake(normalized_text):
                return {
                    "guidance_text": "네, 길 찾아드릴까요, 질문 받을까요?",
                    "used_fallback_llm": True,
                    "source": "intent-mode-wakeup",
                }
            else:
                # 옵션 A: 추측하지 않고 대기 상태를 유지한 채 정확한 재입력을 유도한다.
                return {
                    "guidance_text": "길 찾아줘 또는 물어볼게 중 하나로 다시 말씀해 주세요.",
                    "used_fallback_llm": True,
                    "source": "intent-mode-retry",
                }

        # [하드 코딩 부분 - 핵심]
        # 네비게이션 기능 켜기(Wake-up) 명령어 판별
        # 작성법: 동의어는 짧은 구문 위주로 추가하고, 의미가 겹치는 표현은 중복 등록하지 않는다.
        # 2026-07-14: "길찾아줘"는 wake 퍼지와 충돌하던 탓에 여기에도 넣어, 인텐트 대기
        # 없이 단독 발화되어도 목적지 대기로 들어가게 한다.
        wakeup_keywords = [
            "네비게이션 켜줘",
            "길안내 시작해줘",
            "길안내 시작",
            "네비게이션 기능 켜줘",
            "네비게이션 시작",
            *GILDAENG_NAV_INTENT_KEYWORDS,
        ]
        is_wakeup = any(kw in normalized_text for kw in wakeup_keywords)

        # [하드 코딩 부분 - 핵심]
        # 네비게이션 기능 끄기(Shutdown) 명령어 판별
        # 작성법: 종료/중단 의도를 가진 문장만 포함해 오탐을 줄인다.
        shutdown_keywords = [
            "네비게이션 꺼줘",
            "길안내 종료해줘",
            "길안내 종료",
            "네비게이션 기능 꺼줘",
            "길안내 꺼줘",
        ]
        is_shutdown = any(kw in normalized_text for kw in shutdown_keywords)

        # [하드 코딩 부분 - 핵심] 자유 질의응답 진입 트리거 판별
        is_question_trigger = any(kw in normalized_text for kw in QUESTION_TRIGGER_KEYWORDS)

        # [하드 코딩 부분 - 핵심] "길댕아" 2단계 wake-word 진입 트리거 판별(퍼지 매칭)
        is_gildaeng_wake = _is_gildaeng_wake(normalized_text)

        if is_gildaeng_wake:
            # 2026-07-14 정정: 목적지 대기 중 "길찾아줘" 퍼지 오인/재웨크로
            # WAITING을 깨고 인텐트 선택으로 되돌리던 동작을 막는다. 대기 유지 + 재안지만.
            if current_status == "WAITING_FOR_DESTINATION":
                return {
                    "guidance_text": "목적지를 말씀해 주세요.",
                    "used_fallback_llm": True,
                    "source": "navigation-destination-reprompt",
                }
            nav_manager.set_awaiting_intent(device_id, True)
            return {
                "guidance_text": "네, 길 찾아드릴까요, 질문 받을까요?",
                "used_fallback_llm": True,
                "source": "intent-mode-wakeup",
            }

        elif is_wakeup:
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
                # 지도 패널의 경로 폴리라인 제거용(빈 배열 = 경로 해제).
                "nav_waypoints": [],
            }

        elif is_question_trigger:
            # [바이브 코딩 부분] 다음 발화를 자유 질문으로 받기 위한 상태 전이.
            # nav status(IDLE/WAITING_FOR_DESTINATION/NAVIGATING)와 독립적이라
            # 길안내 중에도 질문 모드에 진입할 수 있다.
            nav_manager.set_awaiting_question(device_id, True)
            return {
                "guidance_text": "네, 질문해 주세요.",
                "used_fallback_llm": True,
                "source": "question-mode-wakeup",
            }

        elif current_status == "WAITING_FOR_DESTINATION":
            # 2026-07-13: 목적지 대기 중에도 "지금 몇 시야" 같은 질문을 목적지로
            # 삼켜 네비만 돌리던 문제를 막는다. 질문처럼 보이면 대기를 풀고 자유 답변.
            if _looks_like_question(normalized_text):
                nav_manager.set_status(device_id, "IDLE")
                return await self._answer_free_question(device_id, normalized_text)

            # [하드 코딩 부분 - 핵심]
            # 목적지 파싱 규칙: 조사/설정 어미를 제거해 POI 검색용 핵심 문자열을 만든다.
            # 작성법: replace 체인은 짧게 유지하고, 복잡해지면 정규식/파서 함수로 분리한다.
            destination = (
                normalized_text.replace("목적지는", "")
                .replace("으로", "")
                .replace("로", "")
                .replace("설정", "")
                .strip()
            )

            from server.navigation.server import helper_fetch_route, helper_search_poi

            # [바이브 코딩 부분] POI 조회와 경로 계산을 순차 수행해 세션 경로를 구성
            try:
                session = nav_manager._get_or_create_session(device_id)

                # [하드 코딩 부분 - 핵심]
                # GPS 미수신 시 서울역 인근 좌표를 기본 시작점으로 사용한다.
                # 작성법: 폴백 좌표는 운영 기준점 하나로 고정하고 문서화한다.
                curr_lat = session.lat if session.lat is not None else 37.5560
                curr_lon = session.lon if session.lon is not None else 126.9722

                start_poi = {"name": "내 실시간 위치", "x": str(curr_lon), "y": str(curr_lat)}

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
                                session_waypoints.append(
                                    {
                                        "index": point_idx,
                                        "lat": float(coords[1]),
                                        "lon": float(coords[0]),
                                        "description": props.get("description", "").strip(),
                                        "facility_type": props.get("facilityType"),
                                    }
                                )
                                point_idx += 1

                        # [하드 코딩 부분 - 핵심]
                        # 상태 전이 순서: route 갱신 -> NAVIGATING 전환
                        # 작성법: 상태를 먼저 바꾸면 route 비어있는 구간이 생길 수 있으므로 현재 순서를 유지한다.
                        nav_manager.update_route(device_id, session_waypoints)
                        nav_manager.set_status(device_id, "NAVIGATING")
                        # 2026-07-11 추가: 안내 시작 직후 첫 행동 지시가 없어 사용자가
                        # 어디로 출발할지 알 수 없었다(거리 트리거는 50m/15m 근접 시에만
                        # 발화). 경로의 첫 유의미 웨이포인트 설명을 시작 멘트에 붙인다.
                        first_direction = ""
                        for wp in session_waypoints:
                            desc = (wp.get("description") or "").strip()
                            if desc and "출발" not in desc:
                                first_direction = f" 먼저, {desc}"
                                break
                        return {
                            "guidance_text": (
                                f"{destination}까지 보행 경로 안내를 시작합니다.{first_direction}"
                            ),
                            "used_fallback_llm": True,
                            "source": "navigation-setup-success",
                            # 2026-07-11 지도 표시용: 클라이언트 하단 지도 패널이 경로
                            # 폴리라인을 그릴 수 있도록 좌표만 추려 전달한다(ws_router가
                            # nav_route 메시지로 변환). 좌표 외 상세 정보는 보내지 않는다.
                            "nav_waypoints": [
                                {"lat": wp["lat"], "lon": wp["lon"]} for wp in session_waypoints
                            ],
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

        # 2026-07-13: 탐지 OFF(또는 질문형 발화)면 장애물 오케스트레이터로 보내지 않는다.
        # 탐지 끄고 질문했는데 "우측으로 피하세요"류(물체탐지)만 나오던 실측 대응.
        # 탐지 ON + 비질문형만 기존 stt→orch 경로를 유지한다.
        if (not nav_manager.is_detection_enabled(device_id)) or _looks_like_question(
            normalized_text
        ):
            return await self._answer_free_question(device_id, normalized_text)

        try:
            # [바이브 코딩 부분] 탐지 ON + 일반 발화는 기존 오케스트레이션 경로로 위임
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

    def _try_answer_from_poi(self, device_id: str, question: str) -> str | None:
        """근접 POI 질의(예: "가까운 지하철역이 어디야")를 T맵 실거리 검색으로 답한다.

        LLM에게 위치 사실을 맡기면 환각 위험이 크므로, 트리거 키워드가 매칭될 때만
        실제 API 조회 결과로 답을 구성하고, 매칭되지 않으면 None을 반환해 호출측이
        일반 LLM 대화로 폴백하게 한다.
        """
        if not any(w in question for w in NEARBY_TRIGGER_WORDS):
            return None
        category = _extract_poi_category(question)
        if not category:
            return None

        from server.navigation.manager import nav_manager
        from server.navigation.server import helper_search_nearest_poi

        session = nav_manager._get_or_create_session(device_id)
        # GPS 미수신 시 서울역 인근 좌표를 기본값으로 사용(목적지 설정 분기와 동일 정책).
        lat = session.lat if session.lat is not None else 37.5560
        lon = session.lon if session.lon is not None else 126.9722

        try:
            result = helper_search_nearest_poi(category, lat, lon)
        except Exception as e:
            print(f"[STT BRIDGE] POI 검색 실패: {e}")
            return None

        if not result:
            return f"근처에서 {category}을(를) 찾지 못했습니다."

        distance_m = result["distance_m"]
        distance_str = (
            f"{distance_m / 1000:.1f}킬로미터" if distance_m >= 1000 else f"{int(distance_m)}미터"
        )
        return (
            f"가장 가까운 {category}은(는) {result['name']}이며, 약 {distance_str} 떨어져 있습니다."
        )

    async def _answer_free_question(self, device_id: str, question: str) -> dict:
        """자유 질의응답 모드에서 받은 발화에 답한다.

        순서: 1) 근접 POI 질의면 실거리 검색으로 사실 기반 답변(환각 방지)
              2) 생활지원/기관 검색 질의면 RAG + Gemini로 답변
              3) 아니면 장애물 회피 오케스트레이터를 우회해 순수 LLM 대화로 답변
        """
        if not question:
            return {
                "guidance_text": "질문을 듣지 못했습니다. 다시 말씀해 주세요.",
                "used_fallback_llm": True,
                "source": "question-empty",
            }

        poi_answer = self._try_answer_from_poi(device_id, question)
        if poi_answer:
            return {
                "guidance_text": poi_answer,
                "used_fallback_llm": True,
                "source": "question-poi",
            }

        if looks_like_convenience_query(question):
            try:
                rag_result = await answer_convenience_question(question)
                answer_text = (rag_result.get("answer") or "").strip()
                if answer_text:
                    return {
                        "guidance_text": answer_text,
                        "used_fallback_llm": bool(rag_result.get("used_fallback_llm", False)),
                        "source": "question-convenience-rag",
                        "rag_query": rag_result.get("query", question),
                        "rag_results": rag_result.get("results", []),
                        "rag_latency_ms": rag_result.get("latency_ms", 0.0),
                    }
            except Exception as e:
                print(f"[STT BRIDGE] Convenience RAG failed: {e}")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            from server.orchestration.llm_client_factory import LLMClientFactory

            messages = [
                SystemMessage(content=QUESTION_SYSTEM_PROMPT),
                HumanMessage(content=question),
            ]
            client = LLMClientFactory.get_client()
            response = await client.ainvoke(messages)
            answer = response.content.strip()
            if not answer:
                raise ValueError("빈 응답")
            return {
                "guidance_text": answer,
                "used_fallback_llm": False,
                "source": "question-llm",
            }
        except Exception as e:
            print(f"[STT BRIDGE] Free question LLM failed: {e}")
            return {
                "guidance_text": "질문에 답하지 못했습니다. 다시 시도해 주세요.",
                "used_fallback_llm": True,
                "source": "question-error",
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
                "guidance_text": "음성이 인식되지 않았어요. 다시 말씀해 주세요.",
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
