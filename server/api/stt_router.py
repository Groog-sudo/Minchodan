import asyncio
import contextlib
import logging
import os
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from server.stt import DEFAULT_REQUEST_MODEL, SttService, SttToLlmBridge
from server.stt.stt_schema import SttTranscribeResult

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/stt", tags=["STT"])


# ============================================================
# STT HTTP Router
# ============================================================
# [바이브 코딩 부분]
# - 업로드 파일을 임시 파일로 저장하고, STT 서비스/브리지 호출 흐름을 연결한다.
# - FastAPI 라우팅, response_model, 기본 예외 변환(HTTPException) 구조를 유지한다.
#
# [하드 코딩 부분]
# - 어떤 예외를 어떤 HTTP 상태코드로 매핑할지(400/422/500)는 운영 정책으로 직접 확정한다.
# - 파일 삭제 시점, 로그 민감정보 정책(원문 비노출), 허용 파일 형식/용량 제한 정책을 직접 확정한다.
#
# [2026-07-09 참고] 실제 단말 앱은 이 REST 엔드포인트가 아니라 server/api/ws_router.py의
# stt_audio WS 메시지(client/src/hooks/useSttRecorder.ts)를 사용한다. 이 라우터는 curl/
# Postman 등 외부 도구로 STT 서비스만 독립적으로 호출·디버깅할 때 쓰는 용도로 유지한다.
# 두 경로 모두 동일한 SttService/SttToLlmBridge를 재사용하므로 로직 중복은 없다.


class SttGuideResponse(BaseModel):
    """
    [바이브 코딩 부분]
    /transcribe-and-guide 응답 스키마.
    STT 원본 결과와 오케스트레이션 안내문을 함께 반환한다.

    [하드 코딩 부분]
    운영에서 필요한 필드(요청 ID, 처리시간, 오류코드, 모델 버전)는 팀 정책에 맞춰 확장한다.
    """

    stt: SttTranscribeResult
    guidance_text: str
    used_fallback_llm: bool
    source: str


async def _save_upload_to_temp(upload_file: UploadFile) -> Path:
    """
    [바이브 코딩 부분]
    업로드 오디오를 임시 파일로 저장하고 Path를 반환한다.

    [하드 코딩 부분] 직접 확정 영역
    작성 조건:
    1) 저장 suffix는 업로드 확장자를 우선 사용하되, 비어 있으면 .wav로 폴백한다.
    2) 파일 데이터가 비어 있으면 즉시 400으로 중단한다.
    3) 임시 파일은 delete=False로 생성하고, 라우터 finally에서 삭제 책임을 강제한다.
    4) 추후 운영 반영 시 파일 크기 상한(예: 10MB), 허용 확장자(wav/mp3/m4a) 검증을 추가한다.
    5) 보안 정책상 원본 파일명/원문 텍스트는 로그에 직접 남기지 않는다.
    """

    # 업로드 원본 확장자를 최대한 보존해 디코더 호환성을 높인다.
    # 확장자가 비어 있으면 Whisper 친화적인 .wav로 폴백한다.
    suffix = Path(upload_file.filename or "input.wav").suffix or ".wav"

    # FastAPI UploadFile은 비동기 스트림이므로 await read()로 안전하게 버퍼링한다.
    # (대용량 처리 최적화는 추후 청크 저장 방식으로 확장 가능)
    data = await upload_file.read()

    if not data:
        raise HTTPException(status_code=400, detail="오디오 파일이 비어 있습니다.")

    # delete=False를 사용해 STT 엔진이 파일을 여는 시점까지 파일 경로를 보장한다.
    # 삭제 책임은 라우터 finally 블록으로 명시적으로 이동한다.
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(data)
        temp_path = Path(temp_file.name)

    return temp_path


@router.post("/transcribe", response_model=SttTranscribeResult)
async def transcribe_audio(
    audio: UploadFile = File(..., description="음성 파일 (wav/mp3 등)"),
    model_name: str | None = Form(default=DEFAULT_REQUEST_MODEL),
) -> SttTranscribeResult:
    """
    [바이브 코딩 부분]
    단일 오디오 파일을 STT로 전사해 표준 결과를 반환한다.
    호출 흐름: 업로드 저장 -> SttService.transcribe_file -> 결과 반환.

    [하드 코딩 부분] 직접 확정 영역
    작성 조건:
    1) 모델명 정책은 stt_config의 DEFAULT_REQUEST_MODEL 및 MODEL_NAME_MAP과 반드시 일치시킨다.
    2) 예외 매핑 규칙을 고정한다.
       - KeyError: 400 (요청 모델명 정책 위반)
       - ValueError: 422 (설정/입력 정책 위반)
       - 기타 예외: 500 (서버 내부 오류)
    3) finally에서 임시 파일 삭제를 보장해 디스크 누수를 방지한다.
    4) 운영 로그는 실패 원인 식별이 가능해야 하지만 개인정보/원문 텍스트는 제외한다.
    5) 동시 요청 증가 시 임시 디렉터리 I/O 병목을 고려해 저장 위치/정리 정책을 별도 문서화한다.
    """

    temp_path: Path | None = None

    try:
        # 1) 업로드를 로컬 임시 파일로 고정
        temp_path = await _save_upload_to_temp(audio)

        # 2) STT 서비스는 Path 기반 입력만 받으므로 라우터에서는 변환 없이 위임
        #    (라우터는 I/O 경계, 서비스는 도메인 로직이라는 계층 분리 원칙)
        # 2026-07-09 정정: transcribe_file()은 동기 블로킹 함수(faster-whisper 추론)라
        # await 없이 직접 호출하면 처리가 끝날 때까지 프로세스의 단일 이벤트 루프 전체가
        # 멈춰, 이 요청과 무관한 다른 모든 연결(반사 경보 WS 포함)까지 함께 정지되는 것을
        # 실측으로 확인했다. asyncio.to_thread로 스레드에 위임해 이벤트 루프를 보존한다.
        return await asyncio.to_thread(
            SttService.transcribe_file, saved_path=temp_path, model_name=model_name
        )
    except KeyError as exc:
        # 모델명 매핑 정책 위반은 클라이언트 입력 오류로 처리(400)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        # 설정값/정책 조합 오류는 의미상 검증 실패(422)로 반환
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        # 이미 상태코드가 정해진 예외는 그대로 전달해 의미를 보존
        raise
    except Exception as exc:
        # 미분류 예외는 내부오류로 축약하되, 서버 로그에는 원인을 남긴다.
        logger.error("STT transcribe 처리 실패: %s", exc)
        raise HTTPException(status_code=500, detail="STT 처리 중 오류가 발생했습니다.") from exc
    finally:
        # 성공/실패와 무관한 정리 단계: 임시 파일 삭제로 디스크 누수 차단
        if temp_path and temp_path.exists():
            with contextlib.suppress(Exception):
                os.unlink(temp_path)


@router.post("/transcribe-and-guide", response_model=SttGuideResponse)
async def transcribe_and_guide(
    audio: UploadFile = File(..., description="음성 파일 (wav/mp3 등)"),
    model_name: str | None = Form(default=DEFAULT_REQUEST_MODEL),
    device_id: str = Form(default="rest-stt"),
) -> SttGuideResponse:
    """
    [바이브 코딩 부분]
    오디오 전사 후 기존 오케스트레이션 브리지로 안내문까지 생성해 반환한다.
    호출 흐름: 업로드 저장 -> STT 전사 -> SttToLlmBridge.invoke_existing_llm -> 응답 조립.

    [하드 코딩 부분] 직접 확정 영역
    작성 조건:
    1) 브리지 호출은 반드시 기존 오케스트레이션 경로만 재사용하고, 라우터에서 LLM 직접 호출을 금지한다.
    2) 빈 입력/실패 폴백(source, used_fallback_llm) 계약은 stt_to_llm_bridge와 동일하게 유지한다.
    3) 응답 조립 시 키 누락 대비 기본값을 명시해 계약 안정성을 확보한다.
    4) 예외 매핑은 /transcribe와 동일한 정책을 유지해 클라이언트 처리 일관성을 보장한다.
    5) 임시 파일 삭제는 성공/실패와 무관하게 항상 수행한다.
    """

    temp_path: Path | None = None

    try:
        # 1) 업로드 저장
        temp_path = await _save_upload_to_temp(audio)

        # 2) STT 전사 수행 (2026-07-09: 이벤트 루프 블로킹 방지를 위해 스레드 위임, 위 참조)
        stt_result = await asyncio.to_thread(
            SttService.transcribe_file, saved_path=temp_path, model_name=model_name
        )

        # 3) 기존 오케스트레이션 브리지 재사용
        #    (라우터에서 LLM 직접 호출 대신, 도메인 어댑터를 통해 일관된 정책 유지)
        bridge = SttToLlmBridge()
        bridge_result = await bridge.invoke_existing_llm(stt_result, device_id)

        # 4) 브리지 응답 dict를 명시적 응답 스키마로 고정
        #    get 기본값은 키 누락 시에도 API 계약을 안정적으로 유지하기 위한 가드레일
        return SttGuideResponse(
            stt=stt_result,
            guidance_text=bridge_result.get("guidance_text", ""),
            used_fallback_llm=bridge_result.get("used_fallback_llm", True),
            source=bridge_result.get("source", "stt-bridge"),
        )
    except KeyError as exc:
        # 모델명 정책 위반
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        # 설정/검증 오류
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except HTTPException:
        # 기존 HTTP 예외 유지
        raise
    except Exception as exc:
        # 브리지/오케스트레이션 계층 오류는 500으로 통일
        logger.error("STT transcribe-and-guide 처리 실패: %s", exc)
        raise HTTPException(
            status_code=500, detail="STT 가이드 처리 중 오류가 발생했습니다."
        ) from exc
    finally:
        # 요청 단위 임시 자원 정리
        if temp_path and temp_path.exists():
            with contextlib.suppress(Exception):
                os.unlink(temp_path)
