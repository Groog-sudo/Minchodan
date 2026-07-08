# -*- coding: utf-8 -*-
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from pydantic import BaseModel


# ============================================================
# STT 스키마 파일
# ============================================================
# [바이브 코딩 부분]
# - 라우터/서비스/테스트가 공통으로 사용할 응답 데이터 구조 정의.
# - SegmentOut은 세그먼트 단위 결과, SttTranscribeResult는 파일 단위 전사 결과를 표현한다.
#
# [하드 코딩 부분]
# - 운영에서 필요한 필드(신뢰도, 처리시간, 에러코드)는 담당자가 직접 확장.


class SegmentOut(BaseModel):
    start: float
    end: float
    text: str


class SttTranscribeResult(BaseModel):
    model_name: str
    text: str
    language: str | None
    duration: float | None
    segments: list[SegmentOut]
    has_input: bool
    saved_file: str
