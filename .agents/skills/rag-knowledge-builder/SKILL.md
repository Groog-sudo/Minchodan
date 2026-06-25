---
name: rag-knowledge-builder
description: |
  로컬 대처 수칙 리스트를 오픈소스 VLM(Llava)과 로컬 임베딩(nomic-embed-text)을 활용하여
  ChromaDB에 오프라인 배치 구축하고 검증하는 RAG 지식 빌더 스킬.
  메타데이터를 3단계 분리 클래스와 일치시켜 검색 정합을 확보한다.
---

# RAG Knowledge Builder (4단계: 위험 대처 수칙 DB 구축)

> **작성일**: 2026-06-24
> **버전**: v0.2.0
> **설계 기준**: `docs/minchodan_design_note.md` 4단계
> **코딩 패턴 준수**: [`docs/course_codebase_guide.md`](../../../docs/course_codebase_guide.md) 섹션 13, 3.3, 17.2

## 개요

오프라인 환경에서 비용 발생 없이 로컬 RAG 시스템을 구동하기 위해, 위험 상황 이미지 데이터셋을 로컬 VLM(Llava)으로 캡셔닝하고, 로컬 임베딩 모델(nomic-embed-text)로 벡터화하여 ChromaDB 영구 저장소에 인덱싱 및 검증한다.

## 전체 아키텍처 위치

```
[원천 영상/사진 데이터]  [프레임 추출/pHash 중복 제거]  [로컬 VLM Llava 캡셔닝]
                                                                
[ChromaDB 로컬 DB 저장]  [로컬 임베딩 nomic-embed-text]  [대처 수칙 메타데이터 결합]
          
[5단계: 실시간 RAG 검색 엔진에서 활용]
```

이 스킬은 **오프라인 배치 프로세스**로 실행되며, 최종 산출물은 실시간 RAG 엔진(5단계)에서 사용하는 `data/chroma_db` 폴더이다.

## 사전 조건

| 항목 | 요구사항 |
|------|----------|
| Python | 3.13 |
| Ollama | 로컬에 설치 및 실행 중 (`ollama run llava`, `ollama run nomic-embed-text`) |
| 패키지 | `chromadb>=0.5`, `langchain-community`, `langchain-ollama`, `imagehash`, `pillow`, `numpy` |
| 원천 데이터 | `data/raw/` 내에 위험 상황을 담은 비디오 또는 사진 100건 이상 |

## 디렉토리 구조 (Minchodan 기준)

```
server/rag/build/
├── frame_extractor.py         # 1fps 프레임 추출
├── dedup_phash.py             # pHash 중복 제거
├── llava_captioner.py         # Ollama(Llava) 한글 캡셔닝
└── db_builder.py              # Chroma.from_documents(persist_directory)

data/
├── raw/                       # 원천 비디오/이미지 저장소
├── frames/                    # 1fps 추출 프레임
├── deduped/                   # pHash 중복 제거 후 프레임
├── captions/                  # Llava 캡셔닝 결과 JSON
└── chroma_db/                 # ChromaDB persist 디렉토리 (산출물)
```

## 핵심 구현 절차

### 단계 4-1. 프레임 샘플링 및 중복 제거

```python
# -*- coding: utf-8 -*-
# server/rag/build/frame_extractor.py
from pathlib import Path
import sys
import cv2

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

def extract_frames(video_path: str, output_dir: str, fps: float = 1.0):
    """영상  1fps 프레임 추출"""
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_count % int(cap.get(cv2.CAP_PROP_FPS) / fps) == 0:
            cv2.imwrite(f"{output_dir}/frame_{frame_count:06d}.jpg", frame)
        frame_count += 1
    cap.release()
```

```python
# -*- coding: utf-8 -*-
# server/rag/build/dedup_phash.py
from pathlib import Path
import sys

from PIL import Image
import imagehash

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

def dedup_frames(input_dir: str, output_dir: str, threshold: int = 5):
    """pHash 중복 제거 (유사도 threshold 이하는 제거)"""
    hashes = {}
    for img_path in sorted(Path(input_dir).glob("*.jpg")):
        img = Image.open(img_path)
        phash = imagehash.phash(img)
        is_dup = False
        for existing_hash in hashes.values():
            if phash - existing_hash < threshold:
                is_dup = True
                break
        if not is_dup:
            hashes[img_path.name] = phash
            img.save(f"{output_dir}/{img_path.name}")
```

### 단계 4-2. 로컬 VLM (Llava) 캡셔닝

```python
# -*- coding: utf-8 -*-
# server/rag/build/llava_captioner.py
import base64
import json
import sys

import requests

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

OLLAMA_URL = "http://localhost:11434/api/generate"
LLAVA_MODEL = "llava"

PROMPT = "이 이미지의 위험 상황을 한국어 1~2문장으로 설명하고 회피 방법을 제시하라."

def caption_image(image_path: str) -> str:
    """이미지를 base64 인코딩하여 로컬 Ollama Llava에 전달"""
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    response = requests.post(OLLAMA_URL, json={
        "model": LLAVA_MODEL,
        "prompt": PROMPT,
        "images": [img_b64],
        "stream": False,
    })
    return response.json().get("response", "")
```

### 단계 4-3. 로컬 임베딩 및 ChromaDB 인덱싱

```python
# -*- coding: utf-8 -*-
# server/rag/build/db_builder.py
import os
import sys

from dotenv import load_dotenv
from langchain.schema import Document
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

if hasattr(sys.stdout, "reconfigure"):
    getattr(sys.stdout, "reconfigure")(encoding="utf-8")

# 환경 변수 및 절대 경로 설정 (가이드 3.3, 3.4 준수)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
env_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path=env_path)

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434",
)

def build_chroma_db(captions: list, persist_dir: str = "data/chroma_db"):
    """캡션 + 메타데이터  ChromaDB 영구 저장"""
    documents = []
    for cap in captions:
        doc = Document(
            page_content=cap["caption"],
            metadata={
                "scene_type": cap["scene_type"],
                "risk_level": cap["risk_level"],
                "objects": cap["objects"],           # 3단계 분리 클래스와 일치
                "guidance_template": cap["guidance"],
            }
        )
        documents.append(doc)

    db = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="safety_guidelines",
    )
    return db
```

## v1.1 핵심: 메타데이터 분리 클래스 일치

메타데이터 `objects`·`scene_type`을 3단계 **분리 클래스**(예: `braille_damaged`)와 일치시켜 검색 정합을 확보한다.

| 메타데이터 필드 | 값 예시 | 3단계 클래스와의 관계 |
| --- | --- | --- |
| `objects` | `["kickboard", "bollard"]` | Yolo 26N - Object Detection 클래스와 일치 |
| `scene_type` | `braille_damaged` | Yolo 26N - Segmentation 클래스와 일치 |
| `risk_level` | `high` / `mid` / `low` | Reflex/Surface Gate 위험도와 일치 |
| `guidance_template` | `"전방 점자블록 파손, 우측으로 우회하세요"` | RAG 검색 결과 텍스트 |

## 데이터 인터페이스

| 방향 | 페이로드 |
| --- | --- |
| In | `List[Document]`(page_content=수칙, metadata={scene_type, risk_level, objects, guidance_template}) |
| Out | 로컬 persist 디렉토리 (`data/chroma_db/`) |

## 의존성·예외

- 단독 선행 작업. 산출 DB는 5단계가 경로 연동.
- 임베딩 API 네트워크/인증 오류; 디스크 쓰기 권한·경로(`PermissionError`) 사전 체크.

## 추상화 (상용 전환 대비)

`Embeddings` 추상 클래스로 랩핑하여 `gemini-embedding-001` 등 상용 임베딩으로 전환 가능.

## 테스트 체크리스트

| 항목 | 기대 결과 | 합격 기준 |
|------|-----------|-----------|
| 1fps 프레임 추출 | 영상  프레임 정상 추출 | 파일 생성 확인 |
| pHash 중복 제거 | 유사 프레임 제거 | deduped 파일 수 < frames |
| Llava 한글 캡셔닝 | 캡션 JSON 생성 | 한국어 포함 |
| 임베딩 768d | nomic-embed-text 벡터 차원 | 768 |
| ChromaDB persist | 디렉토리 정상 생성 | `data/chroma_db/` 존재 |
| **collection 건수** | **>= 100** (MVP 10~15) | `collection.count()` |
| **Top-5 hit-rate** | **>= 0.6** | `eval_hitrate.py` |
| 메타데이터 정합 | `objects`/`scene_type`이 분리 클래스와 일치 | 수동 검증 |

## 참고 자료

- 상세 구현 알고리즘: [references/implementation_detail.md](./references/implementation_detail.md)
- 평가 스크립트: `scripts/eval_hitrate.py`
