import contextlib
import json
import os
import sys
from datetime import datetime

if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

# [바이브 코딩 부분]
# 코드 원리:
# - 평가 스크립트는 "질의 -> Top-k 검색 -> 정답 포함 여부 판정"의 반복 구조로 동작한다.
# 함수/변수 원리:
# - EVAL_TOP_K: 검색 깊이(Top-k) 기준값
# - PASS_THRESHOLD: 명세서 통과 기준값
# - query_text: 각 샘플에서 검색을 유도하는 자연어 문자열
# 로직 구조:
# - 데이터셋 로드 -> 벡터DB 로드 -> 샘플별 판정 -> 요약/리포트 저장

# [하드 코딩 부분 - 핵심]
# 코드 원리:
# - 아래 상수는 TC-RAG-007 명세와 1:1로 대응되는 고정 기준이다.
# 함수/변수 원리:
# - EVAL_TOP_K=5, PASS_THRESHOLD=0.6은 평가 통과 판정의 기준값이다.
# 로직 구조:
# - 값 변경 시 결과 해석이 달라지므로 관련 문서와 함께 동기화해야 한다.
EVAL_TOP_K = 5
PASS_THRESHOLD = 0.6


# 프로젝트 루트 계산 (guide 3.3)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from langchain_community.vectorstores import Chroma

from server.rag.embedding_engine_factory import EmbeddingEngineFactory


def load_guidelines(json_path: str) -> list[dict]:
    """
    [바이브 코딩 부분]
    코드 원리:
    - 평가 대상 데이터셋(JSON)을 메모리로 올려 샘플 반복 평가를 준비한다.
    함수/변수 원리:
    - json_path: 입력 파일 경로
    - guidelines: 각 항목이 caption/objects/scene_type/risk_level/guidance를 담는 리스트
    로직 구조:
    - 경로 체크 -> UTF-8 로드 -> 리스트 타입 검증
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"평가 대상 JSON을 찾을 수 없습니다: {json_path}")

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("safety_guidelines.json 루트는 배열(list)이어야 합니다.")

    return data


def build_query_text(item: dict) -> str:
    """
    [하드 코딩 부분 - 핵심]
    코드 원리:
    - 검색 질의 템플릿은 평가 재현성을 위해 고정된 문구 구조를 사용한다.
    함수/변수 원리:
    - scene_type은 고정 축, caption_slice(80자)는 노이즈 제한 규칙이다.
    로직 구조:
    - scene_type 폴백 -> caption 80자 절단 -> 고정 템플릿 결합
    """
    scene_type = str(
        item.get("scene_type") or "unknown"
    ).strip()  # scene_type가 없으면 "unknown"으로 처리
    caption = str(item.get("caption") or "").strip()  # caption가 없으면 빈 문자열로 처리
    caption_slice = caption[:80]  # caption을 80자까지 자름
    return f"{scene_type} 상황에서 보행 회피 방법: {caption_slice}".strip()  # 최종 질의 텍스트 반환


def expected_labels(item: dict) -> set[str]:
    """
    [하드 코딩 부분 - 핵심]
    코드 원리:
    - 정답 라벨은 objects + scene_type 합집합으로 고정 정의한다.
    함수/변수 원리:
    - objects는 1차 라벨군, scene_type은 보강 라벨군이다.
    로직 구조:
    - 정규화(lower/strip) 후 set으로 통일해 판정 기준을 고정한다.
    """
    labels: set[str] = set()

    for obj in item.get("objects", []) or []:
        obj_text = str(obj).strip().lower()
        if obj_text:
            labels.add(obj_text)

    scene_type = str(item.get("scene_type") or "").strip().lower()
    if scene_type:
        labels.add(scene_type)

    return labels


def is_hit_top_k(results: list, expected: set[str]) -> tuple[bool, str]:
    """
    [하드 코딩 부분 - 핵심]
    코드 원리:
    - Top-k 중 1건이라도 교집합이 있으면 hit 처리하는 OR 규칙을 고정한다.
    함수/변수 원리:
    - expected: 정답 라벨 집합
    - results: similarity_search_with_score 결과 [(Document, score), ...]
    로직 구조:
    - metadata(scene_type, objects) 정규화 -> predicted 생성 -> 교집합 판정
    """
    try:
        for idx, (doc, _score) in enumerate(results, start=1):
            predicted: set[str] = set()
            metadata = getattr(doc, "metadata", {}) or {}

            scene_type = str(metadata.get("scene_type") or "").strip().lower()
            if scene_type:
                predicted.add(scene_type)

            obj_meta = metadata.get("objects")
            if isinstance(obj_meta, list):
                for v in obj_meta:
                    v_text = str(v).strip().lower()
                    if v_text:
                        predicted.add(v_text)
            elif isinstance(obj_meta, str):
                raw = obj_meta.strip()
                if raw:
                    # JSON 문자열 리스트 형태일 수 있어 1회 파싱 시도
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            for v in parsed:
                                v_text = str(v).strip().lower()
                                if v_text:
                                    predicted.add(v_text)
                        else:
                            predicted.add(raw.lower())
                    except Exception:
                        predicted.add(raw.lower())

            if predicted & expected:
                return True, f"top{idx} 매치: {sorted(predicted & expected)}"

        return False, "Top-k 내 라벨 교집합 없음"
    except Exception as exc:
        return False, f"판정 예외: {exc}"


def evaluate_hit_rate(
    json_path: str,
    chroma_dir: str,
    top_k: int = EVAL_TOP_K,
    pass_threshold: float = PASS_THRESHOLD,
) -> dict:
    """
    [바이브 코딩 부분]
    코드 원리:
    - 전체 샘플을 순회하면서 hit/miss를 누적해 hit-rate를 계산한다.
    함수/변수 원리:
    - top_k: 검색 상위 개수
    - pass_threshold: 합격 기준
    - details: 샘플별 판정 로그
    로직 구조:
    - 데이터/DB 준비 -> 샘플 반복 -> 통계 계산 -> 결과 dict 반환
    """
    guidelines = load_guidelines(json_path)

    embeddings = EmbeddingEngineFactory.get_embeddings(provider="ollama")
    vector_db = Chroma(
        persist_directory=chroma_dir,
        embedding_function=embeddings,
        collection_name="safety_guidelines",
    )

    total = len(guidelines)
    hits = 0
    details: list[dict] = []

    for idx, item in enumerate(guidelines, start=1):
        query_text = build_query_text(item)
        expected = expected_labels(item)

        results = vector_db.similarity_search_with_score(query_text, k=top_k)
        is_hit, reason = is_hit_top_k(results, expected)
        if is_hit:
            hits += 1

        details.append(
            {
                "index": idx,
                "scene_type": item.get("scene_type", ""),
                "objects": item.get("objects", []),
                "hit": is_hit,
                "reason": reason,
            }
        )

    hit_rate = (hits / total) if total else 0.0
    passed = hit_rate >= pass_threshold

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "top_k": top_k,
        "threshold": pass_threshold,
        "total": total,
        "hits": hits,
        "hit_rate": round(hit_rate, 4),
        "passed": passed,
        "details": details,
    }


def save_report(report: dict, report_path: str) -> None:
    """
    [바이브 코딩 부분]
    코드 원리:
    - 평가 결과를 파일로 남겨 재현성과 비교 가능성을 확보한다.
    함수/변수 원리:
    - report_path: JSON 리포트 출력 경로
    - report: evaluate_hit_rate()의 반환 dict
    로직 구조:
    - 상위 디렉토리 보장 -> UTF-8 JSON 저장
    """
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main() -> int:
    """
    [하드 코딩 부분 - 핵심]
    코드 원리:
    - 실행 엔트리에서 평가 입력/출력 경로와 판정 출력을 고정해 운영 절차를 일관화한다.
    함수/변수 원리:
    - json_path/chroma_dir/report_path는 현재 프로젝트 표준 경로를 가리킨다.
    로직 구조:
    - 경로 설정 -> 평가 실행 -> 요약 출력 -> 리포트 저장
    """
    json_path = os.path.join(PROJECT_ROOT, "data", "safety_guidelines.json")
    chroma_dir = os.path.join(PROJECT_ROOT, "data", "chroma_db")
    report_path = os.path.join(PROJECT_ROOT, "reports", "eval_history_report.json")

    print("==================================================")
    print(" RAG Top-5 Hit-Rate 평가 시작")
    print("==================================================")
    print(f"- 입력 JSON: {json_path}")
    print(f"- Chroma DB: {chroma_dir}")
    print(f"- Top-k: {EVAL_TOP_K}")
    print(f"- 통과 기준: {PASS_THRESHOLD}")

    try:
        report = evaluate_hit_rate(
            json_path=json_path,
            chroma_dir=chroma_dir,
            top_k=EVAL_TOP_K,
            pass_threshold=PASS_THRESHOLD,
        )

        print("--------------------------------------------------")
        print(f"샘플 수: {report['total']}")
        print(f"적중 수: {report['hits']}")
        print(f"Top-{report['top_k']} hit-rate: {report['hit_rate']:.4f}")
        print(f"판정: {'PASS' if report['passed'] else 'FAIL'}")
        print("--------------------------------------------------")

        save_report(report, report_path)
        print(f"리포트 저장 완료: {report_path}")
        return 0
    except Exception as exc:
        print(f"[실패] 평가 중 오류 발생: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
