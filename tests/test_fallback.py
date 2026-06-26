# -*- coding: utf-8 -*-
import sys
if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

import os
import pytest
from dotenv import load_dotenv

# 로컬 모듈 임포트
from server.rag.shared.labels import KICKBOARD, BOLLARD, BRAILLE_DAMAGED, STAIRS
from server.rag.fallback import get_fallback_guidance
load_dotenv()


def test_fallback_guidance_known_classes():
    # 정의된 표준 클래스들에 대한 정상 수칙 반환 테스트
    res_kick = get_fallback_guidance(KICKBOARD)
    assert "킥보드" in res_kick
    
    res_boll = get_fallback_guidance(BOLLARD)
    assert "볼라드" in res_boll
    
    res_braille = get_fallback_guidance(BRAILLE_DAMAGED)
    assert "점자블록" in res_braille
    
    res_stairs = get_fallback_guidance(STAIRS)
    assert "계단" in res_stairs

def test_fallback_guidance_unknown_and_none():
    # 존재하지 않는 클래스명 주입 시 기본 조치 안내 가이드 출력 검증
    res_unknown = get_fallback_guidance("unknown_obstacle_class")
    assert "unknown_obstacle_class" in res_unknown
    assert "서행" in res_unknown
    
    # None 주입 시 디폴트 전체 경보 반환 검증
    res_none = get_fallback_guidance(None)
    assert "장애물" in res_none
    assert "멈추거나" in res_none
