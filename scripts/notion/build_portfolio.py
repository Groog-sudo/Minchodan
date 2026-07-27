#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minchodan(Gildang) Notion Portfolio Builder
- 대상 노션 페이지에 블록을 순차 추가하여 포트폴리오를 작성한다.
- 디자인룰: 이모지 금지, 한국어 존댓말, 표(Table) 우선, 핵심 굵게.
- 노션 REST API 한 번 호출당 최대 100블록 / 1MB 제한 -> 섹션별 분할 호출.
"""

import json
import os
import sys
import urllib.error
import urllib.request

TOKEN = os.environ.get("NOTION_TOKEN", "")
PAGE_ID = "3aa6e291-2776-80d0-9a44-c8cad1bd9885"
BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

with open("/tmp/r2_urls.json") as f:  # nosec B108 # noqa: S108
    R2 = json.load(f)


def img(key):
    return R2[key]


# ---------- 헬퍼: 블록 빌더 ----------
def rt(text, bold=False, italic=False, code=False, color="default"):
    """rich_text segment 하나 생성."""
    return {
        "type": "text",
        "text": {"content": text},
        "annotations": {
            "bold": bold,
            "italic": italic,
            "strikethrough": False,
            "underline": False,
            "code": code,
            "color": color,
        },
    }


def para(*segments):
    return {"type": "paragraph", "paragraph": {"rich_text": list(segments)}}


def h1(text):
    return {"type": "heading_1", "heading_1": {"rich_text": [rt(text, bold=True)]}}


def h2(text):
    return {"type": "heading_2", "heading_2": {"rich_text": [rt(text, bold=True)]}}


def h3(text):
    return {"type": "heading_3", "heading_3": {"rich_text": [rt(text, bold=True)]}}


def bullet(*segments):
    return {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": list(segments)}}


def numbered(*segments):
    return {"type": "numbered_list_item", "numbered_list_item": {"rich_text": list(segments)}}


def quote(text):
    return {"type": "quote", "quote": {"rich_text": [rt(text)]}}


def callout(text, color="blue_background"):
    return {
        "type": "callout",
        "callout": {
            "rich_text": [rt(text)],
            "color": color,
        },
    }


def divider():
    return {"type": "divider", "divider": {}}


def code(text, lang="python"):
    return {
        "type": "code",
        "code": {"rich_text": [rt(text)], "language": lang},
    }


def image_block(url, caption):
    return {
        "type": "image",
        "image": {
            "type": "external",
            "external": {"url": url},
            "caption": [rt(caption)],
        },
    }


def table(rows, has_header=True, col_width=150):
    """rows: List[List[str]] 첫 행이 헤더."""
    n_cols = len(rows[0]) if rows else 1
    tbl = {
        "table_width": n_cols,
        "has_column_header": has_header,
        "has_row_header": False,
        "children": [],
    }
    for r in rows:
        cells = []
        for c in r:
            cells.append([rt(c)])
        tbl["children"].append({"type": "table_row", "table_row": {"cells": cells}})
    return {"type": "table", "table": tbl}


def toggle(title, *children):
    return {
        "type": "toggle",
        "toggle": {
            "rich_text": [rt(title, bold=True)],
            "children": list(children),
        },
    }


# ---------- API 호출 ----------
def append_blocks(blocks, parent_id=PAGE_ID):
    """블록 리스트를 페이지에 추가. 100개 초과 시 자동 분할."""
    url = f"{BASE}/blocks/{parent_id}/children"
    chunks = [blocks[i : i + 100] for i in range(0, len(blocks), 100)]
    total = 0
    for ch in chunks:
        body = json.dumps({"children": ch}).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=HEADERS, method="PATCH")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
                data = json.loads(resp.read())
                total += len(data.get("results", []))
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code} error appending {len(ch)} blocks:", err[:800], file=sys.stderr)
            raise
    return total


def run():
    blocks = []

    # ===== 표지 =====
    blocks.append(image_block(img("portfolio/gildang-logo.jpg"), "Gildang(길당) 서비스 로고"))
    blocks.append(h1("Gildang(길당)"))
    blocks.append(
        para(
            rt("시각장애인 보행 보조 스마트 가이드독 AI 플랫폼", bold=True),
            rt("  |  ", color="gray"),
            rt("최종 프로젝트 보고서", color="gray"),
        )
    )
    blocks.append(
        callout(
            "본 포트폴리오는 (비NCS) 랭체인 기반 AI영상객체 플랫폼 구축 프로젝트 최종 산출물로, "
            "실제 구현 코드·실기기 검증 로그·팀 공용 changelog를 근거로 작성되었습니다.",
            "blue_background",
        )
    )
    blocks.append(
        table(
            [
                ["항목", "내용"],
                ["과제명", "(비NCS) 랭체인 기반 AI영상객체 플랫폼 구축 프로젝트"],
                ["프로젝트명", "Gildang(길당) — 시각장애인 보행 보조 스마트 가이드독 AI 플랫폼"],
                ["작성자", "김관범(kb)"],
                ["작성일", "2026-07-27"],
                ["버전", "v0.3.9"],
                ["팀 규모", "5인(MVP) — kb·dg·jh·jy·th"],
            ]
        )
    )
    blocks.append(divider())

    # ===== 1. 프로젝트 개요 =====
    blocks.append(h1("1. 프로젝트 개요"))
    blocks.append(h2("개발 목적"))
    blocks.append(
        para(
            rt(
                "시각장애인이 스마트폰 카메라만으로 보행 중 주변 장애물과 노면 상태를 실시간 인식하고, "
            ),
            rt("음성과 햅틱(진동)", bold=True),
            rt("으로 즉시 안내받도록 하는 것이 목적입니다."),
        )
    )
    blocks.append(
        callout(
            "핵심 설계 원칙: 이중 경로의 물리적 분리. "
            "안전 경보가 무거운 AI 추론 때문에 지연되면 안 된다는 안전 요구를 코드 구조 자체로 강제했습니다.",
            "red_background",
        )
    )
    blocks.append(h3("이중 경로 분리 원칙"))
    blocks.append(
        table(
            [
                ["구분", "반사 경로(Reflex)", "인지 경로(Cognitive)"],
                ["대상 위험", "정면 근접 고위험", "중·저위험"],
                ["경유 모듈", "LLM/RAG/실시간 TTS 미경유", "RAG 검색 + LangGraph LLM"],
                ["음성 출력", "사전 합성 고정 클립 선점 재생", "실시간 TTS 상세 가이드"],
                ["목표 지연", "300ms 이내", "1~2Hz"],
            ]
        )
    )
    blocks.append(h3("주요 사용자"))
    blocks.append(
        table(
            [
                ["대상", "상호작용 방식"],
                ["시각장애인 종단 사용자", "음성·햅틱만으로 상호작용(화면 미사용)"],
                [
                    "운영자/보호자",
                    "React 운영 콘솔로 실시간 탐지 피드·위험 이벤트·세션 상태 모니터링",
                ],
            ]
        )
    )
    blocks.append(h3("주요 기능"))
    funcs = [
        "카메라 이중 캡처(반사 8~10fps / 인지 1~2fps)와 WebSocket 실시간 전송",
        "YOLO26n 객체 탐지(29클래스) + 세그멘테이션(노면 4클래스) + ByteTrack 추적",
        "iOS 온디바이스 추론(CoreML/ANE) 반사 레이어 + 서버 추론 하이브리드",
        "이중 게이트(반사 게이트/노면 게이트)를 통한 위험 판정 및 즉시 경보",
        "RAG(ChromaDB) 대처 수칙 검색 + LangGraph 계층 LLM 종합 가이드 생성",
        "이중 채널 음성 출력 + 거리 반비례 햅틱·비프",
        "부가: STT 음성 명령, TMAP 기반 GPS 보행 길안내",
    ]
    for f in funcs:
        blocks.append(numbered(rt(f)))
    blocks.append(divider())

    # ===== 2. 프로젝트 전체 구조 =====
    blocks.append(h1("2. 프로젝트 전체 구조"))
    blocks.append(h2("기술 스택"))
    blocks.append(
        table(
            [
                ["계층", "기술 스택"],
                [
                    "클라이언트(단말)",
                    "React Native, react-native-vision-camera(Frame Processor), iOS Swift 브릿지 + CoreML/ANE, Android TFLite, expo-audio/speech/haptics",
                ],
                [
                    "iOS 빌드/디버깅",
                    "Xcode(xcodebuild), xcrun simctl, XcodeBuildMCP, CocoaPods, .mlpackage→.mlmodelc 컴파일",
                ],
                ["서버(GPU 추론)", "Python 3.13, FastAPI, uvicorn, asyncio, WebSocket /ws/detect"],
                [
                    "AI 모델",
                    "Ultralytics YOLO26n(Object Detection·Segmentation), ByteTrack, LangGraph, Ollama(gemma4:e4b/nomic-embed·bge-m3), Gemini(VLM 캡셔닝), Supertonic TTS, faster-whisper STT",
                ],
                [
                    "데이터베이스",
                    "MariaDB(사용자·단말·감사 로그), Redis(Streams 이벤트 버스·컨텍스트 TTL), ChromaDB(RAG 벡터 저장소)",
                ],
                ["운영 콘솔", "React + Vite, SSE/WebSocket 구독"],
                [
                    "인프라",
                    "Docker(Redis+MariaDB+FastAPI), Ollama 호스트 프로세스, RTX 5090(CUDA 13.0)/macOS MPS, Tailscale·ngrok",
                ],
            ]
        )
    )
    blocks.append(h2("데이터 처리 흐름"))
    blocks.append(
        para(
            rt(
                "스마트폰은 thin client(카메라 캡처 + 온디바이스 반사 추론 + 음성/햅틱 재생)이고, 무거운 인지 추론은 GPU 서버에서 수행합니다. 서버는 ",
            ),
            rt("Router → Service → Repository", bold=True),
            rt(" 3계층으로 분리되어 있습니다."),
        )
    )
    blocks.append(
        code(
            "[iOS 단말 카메라]\n"
            "   |  (입력) 640x640 프레임을 반사/인지 이중 스트림으로 캡처\n"
            "   |\n"
            "   +-▶ [iOS 온디바이스 반사] CoreML/ANE로 YOLO26n 추론\n"
            "   |     -> 반사 게이트 -> 사전합성 클립·햅틱  (네트워크 왕복 0)\n"
            "   |\n"
            "   +-▶ WebSocket /ws/detect (welcome -> 단말 인증 -> auth_ok)\n"
            "   |     (바이너리 raw JPEG + 메타 JSON)\n"
            "   |     |\n"
            "   |     +-▶ [반사 경로(서버)] YOLO26n Detection\n"
            "   |     |     -> Reflex Gate / Surface Gate -> ReflexAlert  [<300ms]\n"
            "   |     |\n"
            "   |     +-▶ [인지 경로] Redis Streams\n"
            "   |           -> LangGraph L1/L2/L3 + RAG(ChromaDB)\n"
            "   |           -> 실시간 TTS 상세 가이드\n"
            "   v\n"
            "[단말] 음성(선점 재생)·햅틱·비프 출력",
            lang="bash",
        )
    )
    blocks.append(h3("아키텍처 시각 자료"))
    blocks.append(
        image_block(
            img("portfolio/sample-02-bicycle.jpg"),
            "Detection 결과 — bicycle(자전거) 클래스. 29클래스 보행 위험 사물 탐지 예시",
        )
    )
    blocks.append(divider())

    print(f"[1/6] 표지+개요+구조: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"      appended {n}")
    blocks = []

    # ===== 3. 본인 담당 역할 =====
    blocks.append(h1("3. 본인의 담당 역할"))
    blocks.append(
        para(
            rt(
                "이번 프로젝트에서 ",
            ),
            rt("iOS 클라이언트 개발과 빌드", bold=True),
            rt(
                "가 본인의 핵심 담당이었습니다. React Native/Swift 네이티브 브릿지 구현, CoreML 모델 로딩·raw tensor 파싱, Apple Neural Engine(ANE) 완전 가속 기동, Xcode 빌드·실기기 배포·디버깅 전 과정을 직접 수행했습니다. 서버 측에서는 "
            ),
            rt("3단계(AI 장애물 실시간 인식)", bold=True),
            rt("과 "),
            rt("6단계(LangGraph 계층 LLM 가이드 생성)", bold=True),
            rt("을 주담당했습니다."),
        )
    )
    blocks.append(h2("직접 수행 vs 팀 작업"))
    blocks.append(
        table(
            [
                ["영역", "담당자(kb) 직접 수행", "팀원/공통"],
                [
                    "iOS 온디바이스 추론(핵심)",
                    "CoreMLInferenceBridge.swift 전면 구현(MLModel 로드·raw tensor 파싱·det/seg 동시 추론·ANE 완전 가속·CFAbsoluteTime 벤치마크)",
                    "—",
                ],
                [
                    "iOS 빌드/실기기(핵심)",
                    "Xcode 빌드·.mlpackage 리소스 배치(pbxproj 수정)·실기기 배포·디버깅, xcode-build-management 스킬 신설",
                    "—",
                ],
                [
                    "운영 콘솔 프론트(핵심)",
                    "LiveCameraFeed·DeviceTelemetryPanel·ConsoleAudioMirror·거리구역 오버레이·회원 등록 화면 등 React 컴포넌트 신규 구현",
                    "임진형(jh) 콘솔 위젯 일부",
                ],
                [
                    "1·2단계 WS·캡처(핵심)",
                    "서버 WS /ws/detect·세션/하트비트, 이중 스트림 asyncio.Queue 분기, 클라 WS 훅·이중 캡처·동적 반사 FPS·바이너리 전송·지수 백오프 재연결",
                    "—",
                ],
                [
                    "3단계 탐지",
                    "server/detection/ 전체(탐지·분할·ByteTrack·게이트·거리정책 SSOT·보도 이탈 판정·실내 오탐 완화)",
                    "YOLO 데이터셋 라벨링·학습 일부 협업",
                ],
                [
                    "6단계 LLM",
                    "server/orchestration/(LangGraph L1/L2/L3·fast_lane·LLMClientFactory 핫스왑)",
                    "—",
                ],
                [
                    "7단계 TTS(핵심)",
                    "Supertonic TTS 엔진 도입·합성 직렬화 락·바이너리 WS 전송·반사 클립 송신·음성 우선순위 4단·캐시 프리워밍",
                    "—",
                ],
                [
                    "MCP 연동(6종)",
                    "GPU 모니터·Slack·Audio Validator·Cache Monitor·Accessibility Simulator·LangSmith Tracer 아웃오브밴드 비동기 구현",
                    "—",
                ],
                [
                    "백엔드 영속화·클라우드",
                    "이벤트 프레임 저장·오탐 판정 컬럼·탐지 로그 DB 영속화, 클라우드 MariaDB(gildang_db)·Cloudflare R2 미디어 백엔드",
                    "문준영(jy) DB/미디어 API 가이드",
                ],
                [
                    "성능·과부하 대응",
                    "P0/P1 백프레셔·추론 절감·guide drop, YOLO 추론 전용 스레드풀 분리, Redis 트리밍·이벤트 프레임 주기 정리",
                    "—",
                ],
                [
                    "에이전트 스킬 저작(핵심)",
                    "xcode-build-management·integration-test-orchestrator·rpi-network-profile-switcher·auto-publish-work·react-doctor",
                    "—",
                ],
                [
                    "브랜치 병합·정합성(핵심)",
                    "팀원 브랜치 dev 통합, 디스포저블 테스트 브랜치 사전 병합·린트/mypy 베이스라인 대조·반사 경로 위반 스캔",
                    "각 팀원 개별 브랜치 작업",
                ],
                [
                    "아키텍처·설계 문서(기준선)",
                    "README·architecture.md·api_specification·test_specification·pipeline_stage_design·stage2/3/6 설계서·다중 에이전트 진입점",
                    "설계 노트(minchodan_design_note) 팀 공동",
                ],
            ]
        )
    )
    blocks.append(h2("연결 지점(본인 작업 ↔ 팀원 작업)"))
    connect = [
        (
            "iOS 단말 ↔ 서버",
            "본인이 구현한 iOS 클라이언트가 WebSocket /ws/detect로 서버와 연결. 온디바이스(반사)와 서버(인지) 추론을 하이브리드로 배선.",
        ),
        (
            "3단계 → 6단계",
            "3단계 server/bus/producer.py가 Redis Streams에 발행하는 payload(event_id·track_id·class_name·confidence·bbox·direction·risk)를 6단계 입력 계약으로 매핑.",
        ),
        (
            "5단계(RAG) → 6단계",
            "팀원이 구축한 RAG 검색 결과(rag_context)를 L2 생성 노드 입력으로 소비.",
        ),
        (
            "위험도 SSOT 계약",
            "서버 게이트 임계값과 iOS 단말 CLASS_MIN_CONFIDENCE를 tests/test_risk_ssot.py로 강제 동기화.",
        ),
    ]
    for title, desc in connect:
        blocks.append(bullet(rt(title + ": ", bold=True), rt(desc)))
    blocks.append(divider())

    print(f"[2/6] 담당역할: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"      appended {n}")
    blocks = []

    # ===== 4. 세부 구현 내용 =====
    blocks.append(h1("4. 세부 구현 내용"))
    blocks.append(
        para(
            rt(
                "담당 핵심(iOS 온디바이스 추론·빌드, 3단계 반사 게이트, 6단계 LangGraph, 7단계 TTS)을 "
            ),
            rt("입력 → 처리 → 출력", bold=True),
            rt(" 순으로 설명합니다."),
        )
    )

    # 4-A iOS
    blocks.append(h2("4-A. iOS 온디바이스 추론 파이프라인 & Xcode 빌드"))
    blocks.append(
        para(
            rt("사용 기술: ", bold=True),
            rt(
                "Swift, CoreML(MLModel/MLMultiArray/MLDictionaryFeatureProvider), Apple Neural Engine(ANE), Core Video(CVPixelBuffer), Vision(VNClassifyImageRequest), React Native Native Module, Xcode/xcodebuild, expo-image-manipulator."
            ),
        )
    )
    blocks.append(
        para(
            rt(
                "전체 구현은 ",
            ),
            rt("client/ios/CoreMLInferenceBridge.swift", code=True),
            rt(" (약 654줄, 실제 Xcode 빌드 타겟 파일)에 있습니다."),
        )
    )

    blocks.append(h3("(1) 모델 로드 — ANE 우선, 실패 시 CPU 폴백"))
    blocks.append(
        para(
            rt("Apple Neural Engine을 우선 사용하되, 로드 실패 시 CPU 전용으로 폴백해 "),
            rt("파이프라인 영속성", bold=True),
            rt("을 확보합니다."),
        )
    )
    blocks.append(
        code(
            "private func loadModel(url: URL) throws -> MLModel {\n"
            "  let aneConfig = MLModelConfiguration()\n"
            "  aneConfig.computeUnits = .cpuAndNeuralEngine        // ANE 가속 우선\n"
            "  do {\n"
            "    let model = try MLModel(contentsOf: url, configuration: aneConfig)\n"
            "    return model\n"
            "  } catch {\n"
            "    let cpuConfig = MLModelConfiguration()\n"
            "    cpuConfig.computeUnits = .cpuOnly                  // 실패 시 CPU 폴백\n"
            "    return try MLModel(contentsOf: url, configuration: cpuConfig)\n"
            "  }\n"
            "}",
            lang="swift",
        )
    )
    blocks.append(
        para(
            rt(
                "loadModels에서 object_detection.mlmodelc는 필수, segmentation.mlmodelc는 선택 로드로 두어 seg 미번들 시에도 det-only로 기동합니다."
            )
        )
    )

    blocks.append(h3("(2) 프레임 진입 — EXIF 방향 정규화 후 백그라운드 추론"))
    blocks.append(
        para(
            rt(
                "UIImage.cgImage는 EXIF imageOrientation을 반영하지 않아, 세로로 촬영된 사진이 회전되지 않은 채 모델에 들어가면 엉뚱한 클래스로 오탐지됩니다. 반드시 "
            ),
            rt(".up으로 정규화한 cgImage", bold=True),
            rt("를 사용합니다."),
        )
    )
    blocks.append(
        code(
            "guard let imageData = Data(base64Encoded: base64Image),\n"
            "      let image = UIImage(data: imageData),\n"
            "      let cgImage = image.normalizedCGImage() else {   // EXIF 방향 정규화\n"
            '  reject("INVALID_IMAGE", nil, nil); return\n'
            "}\n"
            "DispatchQueue.global(qos: .userInteractive).async {   // 메인 UI 블로킹 방지\n"
            "  let startTime = CFAbsoluteTimeGetCurrent()\n"
            "  let detPrediction = try self.predictRaw(model: detModel, cgImage: cgImage)\n"
            "  let detResults = self.runDetection(prediction: detPrediction,\n"
            '                                    modelType: "object_detection")\n'
            "  let detLatency = (CFAbsoluteTimeGetCurrent() - startTime) * 1000.0\n"
            "}",
            lang="swift",
        )
    )

    blocks.append(h3("(3) raw tensor 수동 파싱 (핵심)"))
    blocks.append(
        para(
            rt(
                "Vision(VNCoreMLRequest)이 강제하는 라벨 매핑이 커스텀 29/4클래스 모델과 맞지 않아, "
            ),
            rt("MLMultiArray를 포인터로 직접 읽", bold=True),
            rt("습니다. ANE 비호환 연산(TopK/Gather)을 export 단계에서 제거한 "),
            rt("NMS-free 밀집(dense) 텐서", bold=True),
            rt("를 클래스별 최댓값·임계값·정렬만으로 디코딩합니다."),
        )
    )
    blocks.append(
        code(
            "// parseYoloOutput() — channels-first 밀집 [1, 4+nc(+32), N]\n"
            "let ptr = UnsafeMutablePointer<Float32>(\n"
            "    multiArray.dataPointer.assumingMemoryBound(to: Float32.self))\n"
            "let strides = multiArray.strides.map { $0.intValue }\n"
            "for i in 0..<numBoxes {\n"
            "  var bestClassId = -1; var bestScore: Float32 = -1\n"
            "  for c in 0..<numClasses {                       // 클래스별 최댓값\n"
            "    let score = ptr[(4 + c) * strides[1] + i * strides[2]]\n"
            "    if score > bestScore { bestScore = score; bestClassId = c }\n"
            "  }\n"
            "  if Double(bestScore) < confThreshold || bestClassId < 0 { continue }\n"
            "  let cx = Double(ptr[0 * strides[1] + i * strides[2]]) * 640.0   // xywh -> 픽셀\n"
            "  let w  = Double(ptr[2 * strides[1] + i * strides[2]]) * 640.0\n"
            '  results.append(["className": activeClassNames[bestClassId] ?? "unknown",\n'
            '                  "confidence": Double(bestScore),\n'
            '                  "bbox": ["x": cx - w/2.0, "y": cy - h/2.0,\n'
            '                            "w": w, "h": h]])\n'
            "}",
            lang="swift",
        )
    )

    blocks.append(h3("(4) 지연 계측 + 응답 반환"))
    blocks.append(
        para(
            rt(
                "CFAbsoluteTimeGetCurrent()로 det/seg/scene을 개별 계측(정상 ANE 10~20ms, 가속 실패 100ms+)합니다."
            )
        )
    )
    blocks.append(
        code(
            'let benchmarkDict = ["det_ms": detLatency, "seg_ms": segLatency,\n'
            '                     "scene_ms": sceneLatency, "total_ms": totalLatency]\n'
            'resolve(["det": detResults, "seg": segResults,\n'
            '         "benchmark": benchmarkDict, "scene": sceneResult,\n'
            '         "surfaceDeparture": isDepartingSidewalk] as NSDictionary)',
            lang="swift",
        )
    )

    blocks.append(h3("(5) Xcode 빌드 정합 (실기기 배포)"))
    blocks.append(
        para(
            rt(
                "segmentation.mlpackage가 Xcode 드롭 시 소스 빌드 단계(PBXSourcesBuildPhase)로 오분류된 것을 "
            ),
            rt("project.pbxproj를 직접 수정", bold=True),
            rt(
                "해 리소스 단계(PBXResourcesBuildPhase)로 재배치 → 빌드 시 .mlmodelc로 자동 컴파일·번들 탑재. 실기기 리빌드로 det=CoreML ANE / seg=CoreML ANE 완전 가속 기동 로그를 확인했습니다."
            ),
        )
    )

    blocks.append(h3("출력 결과"))
    blocks.append(
        bullet(
            rt(
                "신뢰도 역순 정렬된 detection·segmentation 결과 + 씬 분류(scene) + 벤치마크(total_ms)를 React Native(useOnDeviceDetection)로 반환 → 반사 게이트/BBox 오버레이/거리 반비례 햅틱·비프 구동."
            )
        )
    )
    blocks.append(
        bullet(
            rt("무선 전송 프레임: ", bold=True),
            rt("3.4MB → 약 12KB(1/45)로 압축해 소켓 끊김 제거."),
        )
    )
    blocks.append(
        bullet(
            rt("부가 산출물: ", bold=True),
            rt("iOS 빌드/디버깅 자동화를 위한 xcode-build-management 에이전트 스킬 신설."),
        )
    )

    print(f"[3/6-A] iOS 파이프라인: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"         appended {n}")
    blocks = []

    # 4-B 반사 게이트
    blocks.append(h2("4-B. 3단계 — 반사 게이트 (즉시 경보 판정)"))
    blocks.append(
        para(
            rt("입력: ", bold=True),
            rt(
                "Detection 객체(bbox, confidence, track_id, hit_count, route, effective_distance_zone)."
            ),
        )
    )
    blocks.append(
        para(
            rt("처리(", bold=True),
            rt("class-agnostic 설계", bold=True),
            rt("): ", bold=True),
            rt("클래스명으로 분기하지 않고 "),
            rt('"진행 방향 정면 Near 구역에 물체가 존재하는가"', bold=True),
            rt(
                '로만 즉시 경보. 오탐 억제 다단 필터 — ① hit_count>=3(단, 재획득 객체는 즉시) ② confidence>=0.35 ③ 12시 회랑 판정 ④ route=="reflex".'
            ),
        )
    )
    blocks.append(
        code(
            "# server/detection/gates/reflex_gate.py (발췌)\n"
            "if not detection.reacquired and detection.hit_count < MIN_HIT_COUNT:\n"
            "    return None\n"
            "if detection.confidence < AGNOSTIC_MIN_CONFIDENCE:\n"
            "    return None\n"
            'speech_ok = is_speech_front(detection.bbox, frame_width, "near")\n'
            "if not speech_ok:\n"
            "    return None\n"
            'if detection.route != "reflex":   # Near(reflex)만 통과\n'
            "    return None",
            lang="python",
        )
    )
    blocks.append(
        para(
            rt("출력: ", bold=True),
            rt(
                "ReflexAlert(clip, haptic, panning, 거리 반비례 beep) → 단말 사전합성 클립 선점 재생."
            ),
        )
    )
    blocks.append(
        image_block(
            img("portfolio/det-bollard.jpg"),
            "Detection 결과 — 볼라드(bollard) 클래스 탐지. 보행 안전 핵심 사물.",
        )
    )

    # 4-C LangGraph
    blocks.append(h2("4-C. 6단계 — LangGraph 계층 오케스트레이션"))
    blocks.append(
        para(
            rt("입력: ", bold=True),
            rt("Redis Streams의 3단계 탐지 이벤트 + RAG 검색 결과(rag_context)."),
        )
    )
    blocks.append(
        para(
            rt("처리: ", bold=True),
            rt("OrchState를 상태로 L1(분류)→(조건분기)→L2/fast_lane→L3(검증)→END 그래프 실행. "),
            rt("fast_lane", bold=True),
            rt(
                "은 단일 객체+구조화 필드가 있으면 LLM을 건너뛰어 지연 절감. L3 검증 실패 시 최대 1회 재시도, 초과 시 Fallback 고정 문장."
            ),
        )
    )
    blocks.append(
        code(
            "# server/orchestration/graph.py (발췌) — L3 이후 조건부 라우팅\n"
            'if state.get("verified"):\n'
            '    return "end"\n'
            "if retry_count > 1:\n"
            '    return "fallback"        # 재시도 한도 초과 -> 고정 문장\n'
            'return "l2_generate"          # 재성공 시도',
            lang="python",
        )
    )
    blocks.append(
        para(
            rt("AI 연동: ", bold=True),
            rt(
                "GPU 부하 임계 초과 시 LLMClientFactory가 Ollama→OpenAI 핫스왑(메인 스레드 0ms 블로킹)."
            ),
        )
    )
    blocks.append(para(rt("출력: ", bold=True), rt("방향 포함 20자 내외 안내 문장 → 실시간 TTS.")))
    blocks.append(
        para(
            rt("검증: ", bold=True),
            rt("pytest test_langgraph.py 6건, test_detection.py 등 3단계 93건 통과."),
        )
    )

    # 4-D 협업 인프라
    blocks.append(h2("4-D. 협업 인프라 — 스킬·CI·시연 환경·병합 정합성"))
    blocks.append(
        para(
            rt(
                "결과물 코드뿐 아니라, 팀원들이 서로 다른 AI 코딩 에이전트를 써도 동일하게 활용할 수 있는 "
            ),
            rt("협업 인프라", bold=True),
            rt("를 직접 구축했습니다."),
        )
    )

    blocks.append(h3("(1) 팀 공용 에이전트 스킬 저작"))
    blocks.append(
        bullet(
            rt("xcode-build-management: ", bold=True),
            rt("iOS 빌드·시뮬레이터·실기기 로그·Swift 리팩토링 워크플로."),
        )
    )
    blocks.append(
        bullet(
            rt("integration-test-orchestrator: ", bold=True),
            rt("실기기-Docker(FastAPI/Redis/MariaDB)-DB 통합 테스트 기동·로그 오케스트레이션."),
        )
    )
    blocks.append(
        bullet(
            rt("rpi-network-profile-switcher: ", bold=True),
            rt("시연용 네트워크 프로필 무빌드 전환."),
        )
    )
    blocks.append(
        bullet(
            rt("auto-publish-work / react-doctor: ", bold=True),
            rt("문서 정합·린트·changelog 자동 마감 / RN 정적 분석."),
        )
    )
    blocks.append(
        para(
            rt("검증: ", bold=True),
            rt("python scripts/validate_agent_rules.py 6/6 통과(진입점·스킬 미러 diff -rq 일치)."),
        )
    )

    blocks.append(h3("(2) 모듈 빌드·Git 커밋·CI 테스트 자동화"))
    blocks.append(
        para(
            rt(
                "커밋·푸시·PR 시 자동 실행되는 품질 파이프라인(Ruff+Bandit+mypy+jscpd+pip-audit)을 문서화·구현했습니다."
            )
        )
    )
    blocks.append(
        table(
            [
                ["실행 시점", "검증 도구", "목적"],
                ["pre-commit", "Ruff + Bandit", "빠른 린트·보안 1·2차"],
                ["pre-push", "mypy + jscpd + pip-audit", "타입 점검·중복·의존성 CVE"],
                ["GitHub Actions", "전체 + pytest", "PR 게이트"],
            ]
        )
    )
    blocks.append(
        para(
            rt("반사 경로(server/detection/gates/)의 LLM/RAG/TTS 임포트 금지도 "),
            rt("스캔으로 강제", bold=True),
            rt("합니다."),
        )
    )

    blocks.append(h3("(3) 시연 환경 전환 스크립트"))
    blocks.append(
        para(
            rt(
                "scripts/switch_rpi_network.sh — 시연 네트워크 토폴로지(아이폰↔서버=Tailscale, 서버↔LLM(Mac mini)·DB(Raspberry Pi)=LAN)를 "
            ),
            rt("무빌드로 전환", bold=True),
            rt(". DB TCP, 미디어 /health, Ollama /api/tags 도달성 사전검사 포함."),
        )
    )

    blocks.append(h3("(4) 브랜치 병합 전 정합성 검토"))
    blocks.append(
        numbered(
            rt("디스포저블 테스트 브랜치(merge-test-*)에서 순차 시험 병합해 git 충돌을 먼저 확인.")
        )
    )
    blocks.append(numbered(rt("병합 트리에서 ruff / bandit / tsc --noEmit 전체 통과 확인.")))
    blocks.append(
        numbered(
            rt(
                "mypy /client tsc 잔여 오류는 별도 워크트리로 origin/dev 베이스라인 대조 → 신규 오류 0건 확인."
            )
        )
    )
    blocks.append(numbered(rt("반사 경로 임포트 위반 스캔 → 문서-코드 교차 검증.")))
    blocks.append(numbered(rt("충돌·회귀 없이 dev 통합 및 어긋난 문서 정정.")))

    print(f"[3/6-B] 게이트+오케스트레이션+협업인프라: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"         appended {n}")
    blocks = []

    # 4-E 콘솔, 4-F TTS
    blocks.append(h2("4-E. 운영 콘솔 프론트엔드 — 실시간 렌더링 & HUD 디자인"))
    blocks.append(
        para(
            rt(
                "운영자가 단말 상태를 실시간 모니터링하는 React(+Vite) 콘솔의 프론트엔드를 직접 구현했습니다."
            )
        )
    )
    blocks.append(
        para(
            rt("입력(렌더링 데이터): ", bold=True),
            rt(
                "콘솔 WS /ws/console/live-feed와 SSE로 수신하는 ① 카메라 실시간 프레임(바이너리 Blob) ② server_detection(bbox + effective_distance_zone) ③ console_guide_audio·reflex_alert(TTS WAV/반사 클립 미러) ④ SSE monitor 이벤트."
            ),
        )
    )
    blocks.append(para(rt("주요 컴포넌트: ", bold=True)))
    blocks.append(
        bullet(
            rt("LiveCameraFeed.tsx: ", bold=True),
            rt(
                "실시간 카메라 화면 위 BBox 오버레이 + effective_distance_zone(near/medium/far) 색상(빨강/주황/파랑) 매핑. T맵 GPS HUD 미니맵 iframe 포함."
            ),
        )
    )
    blocks.append(
        bullet(
            rt("DeviceTelemetryPanel.tsx: ", bold=True),
            rt(
                "단말 접속·AI 모델 런타임·위험물 매트릭스·STT/TTS 로그를 군용 콘솔 스타일 HUD로 디자인."
            ),
        )
    )
    blocks.append(
        bullet(
            rt("ConsoleAudioMirror.tsx: ", bold=True),
            rt("인지 TTS·반사 비프를 <audio>로 미러 재생, 햅틱을 강도별 색상/크기 펄스로 시각화."),
        )
    )
    blocks.append(
        bullet(
            rt("DashboardPage.tsx: ", bold=True), rt("위젯 키 기반 대시보드로 각 패널 배치·정렬.")
        )
    )
    blocks.append(
        para(
            rt("검증: ", bold=True),
            rt("console npx tsc --noEmit 0 오류, 서버 연동 pytest 352 passed."),
        )
    )

    blocks.append(h2("4-F. 7단계 — TTS·음성 안내 파이프라인"))
    blocks.append(
        para(rt("이중 채널 음성 출력(반사=사전합성 / 인지=실시간 TTS)을 직접 구현했습니다."))
    )
    blocks.append(
        para(
            rt("처리: ", bold=True),
            rt("인지 문장은 Supertonic TTS로 실시간 합성, 반사는 사전합성 고정 클립 송신. 합성은 "),
            rt("asyncio.Lock으로 직렬화", bold=True),
            rt(
                "(동시 합성 시 버퍼 경합으로 동일 오디오가 나오던 버그 차단). 자주 쓰는 문장은 문장 단위 캐시 프리워밍."
            ),
        )
    )
    blocks.append(
        para(
            rt("출력·전송: ", bold=True),
            rt(
                'audio_mp3_b64(base64 JSON) 폐기 → JSON 메타(transport:"binary") + raw WAV 바이너리 2단계 WS 전송으로 페이로드 축소. 단말은 arraybuffer로 수신해 expo-fileSystem 직접 기록 후 재생.'
            ),
        )
    )
    blocks.append(
        para(
            rt("검증: ", bold=True),
            rt("컨테이너 내 모델 로드 0.5초/합성 0.86초, 동시 합성 시 서로 다른 바이트 길이 확인."),
        )
    )
    blocks.append(divider())

    print(f"[3/6-C] 콘솔+TTS: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"         appended {n}")
    blocks = []

    # ===== 5. 문제 해결 과정 =====
    blocks.append(h1("5. 문제 해결 과정"))

    problems = [
        (
            "5-A. iOS CoreML GPU 경로 크래시 (MLIR pass manager failed)",
            "문제: computeUnits=.cpuAndGPU(Metal) 경로에서 앱 크래시.\n원인: end2end NMS 연산(Topk/GatherNd 등)의 Metal 컴파일 실패로 추정.\n해결: 안정성 우선으로 CPU/ANE 경로로 조정하고, 이후 세그멘테이션까지 ANE 완전 가속으로 재기동해 성능·안정성 양립.",
        ),
        (
            "5-B. iOS 무선 전송 소켓 끊김 (대역폭 병목)",
            "문제: 10fps 전송 시 무선망에서 WebSocket 소켓이 끊김.\n원인: 원본 프레임(약 3.4MB/장)이 무선 대역폭 초과.\n해결: expo-image-manipulator로 640x640 크롭 + JPEG 50% 압축 → 약 12KB(1/45)로 격감. 실기기에서 소켓 끊김 100% 소멸 검증.",
        ),
        (
            "5-C. iOS 좌표/방향 정합 (EXIF·종횡비)",
            "문제: 세로 촬영 시 오탐, BBox가 실물보다 뚱뚱하게 어긋남.\n원인: UIImage.cgImage가 EXIF orientation 미반영, 프리뷰(19.5:9)와 추론 해상도(640 정사각) 불일치.\n해결: normalizedCGImage()로 방향 정규화 + 카메라 컨테이너를 1:1 정사각으로 격리해 좌표 투영 왜곡 제거.",
        ),
        (
            "5-D. 실내 오탐 (도메인 시프트, OOD)",
            "원인: YOLO26n이 실외 데이터만 학습 → 실내에서 car/sidewalk_normal 고신뢰도 오탐.\n해결: 클래스별 confidence 상향 + hit_count>=3 + 실외 노면 co-occurrence + 물리적 타당성 필터 + 씬 분류기 게이트(iOS VNClassifyImageRequest). 실기기 로그 632건 분석으로 동반 identifier 기반 규칙 확정. 씬 분류 지연 평균 11.27ms.",
        ),
        (
            "5-E. Android/Metro 교차 플랫폼 검증",
            "Android TFLite 프레임 병목(풀해상도 JPEG 왕복 1.4~1.5초) → crop + inSampleSize 다운샘플로 해결. Tailscale VPN 인터페이스 오인식으로 인한 Metro 에셋 로딩 지연 → REACT_NATIVE_PACKAGER_HOSTNAME 강제로 해결.",
        ),
        (
            "5-F. 실기기 안내 음성 절단 (근본 원인 2건)",
            "문제: 실기기에서만 안내 음성이 문장 중간에 끊김.\n원인: ① Piper G2P가 흔한 음절(측/직/걸 등) 누락 ② 반사 캡처의 takePhoto()가 매 촬영마다 AVAudioSessionInterruption 유발(3분간 80회).\n해결: ① Supertonic 엔진 전면 교체 ② 반사 캡처를 AVCapturePhotoOutput 대신 VisionCamera Frame Processor(연속 스트림)로 전환. sudo log collect로 전환 후 인터럽션 0회 확인.",
        ),
        (
            "5-G. 장시간 구동 시 체감 지연·CPU 경합",
            "문제: 장시간 테스트에서 안내 지연이 점점 커지고 다중 객체 프레임에서 반응이 느려짐.\n원인: Redis 스트림·이벤트 프레임 데이터 누적, YOLO 추론이 메인 이벤트 루프 스레드와 CPU 경합.\n해결: Redis 스트림 트리밍·이벤트 프레임 주기 정리, YOLO 추론 전용 스레드풀 분리, 과부하 시 백프레셔·추론 절감·guide drop 적용.",
        ),
    ]
    for title, body in problems:
        blocks.append(h3(title))
        for line in body.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith(("문제:", "원인:", "해결:")):
                tag = line.split(":", 1)[0]
                rest = line.split(":", 1)[1].strip()
                blocks.append(bullet(rt(tag + ": ", bold=True), rt(rest)))
            else:
                blocks.append(bullet(rt(line)))
    blocks.append(divider())

    print(f"[4/6] 문제해결: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"      appended {n}")
    blocks = []

    # ===== 6. 평가 및 개선 방향 =====
    blocks.append(h1("6. 프로젝트 평가 및 개선 방향"))
    blocks.append(h2("성과"))
    achievements = [
        "iOS 실기기에서 detection·segmentation을 ANE 완전 가속으로 구동(10~20ms대)하는 온디바이스 반사 레이어를 완성해, thin client가 단순 전송기가 아닌 즉각 경보 반응기로 동작.",
        "이중 경로 물리 분리를 코드 구조·테스트(SSOT 계약)로 강제.",
        "7단계 KPI 상당수 충족(WS RTT<100ms, Detection<80ms, RAG<50ms).",
        "Xcode 빌드/실기기 배포·디버깅을 스킬로 표준화해 반복 작업 자동화.",
        "실기기(iOS)-Docker(FastAPI/Redis/MariaDB)-DB 전 구간 종단(E2E) 통합 테스트를 실기기로 반복 수행해 반사·인지·STT·네비게이션 전 경로 실측 검증(외부망 ngrok/Tailscale 야외 필드 테스트 포함).",
    ]
    for a in achievements:
        blocks.append(bullet(rt(a)))

    blocks.append(h2("실측 성능 지표 (KPI)"))
    blocks.append(
        table(
            [
                ["항목", "설계 목표", "실측", "출처"],
                ["iOS ANE det 추론", "<80ms", "10~14ms", "docs/ops/ondevice_coreml_benchmark.md"],
                ["iOS ANE seg 추론", "—", "5~12ms", "동일"],
                [
                    "iOS ANE 총합(det+seg+scene)",
                    "—",
                    "19~35ms (이전 cpuOnly 42.97ms 대비 2.5배 단축)",
                    "동일",
                ],
                ["프레임 디코딩", "<50ms", "0.8ms (달성)", "latency_impact_analysis.md"],
                ["RAG 검색", "<50ms", "56~78ms (근접)", "outdoor_guidance_refinement_roadmap.md"],
                ["패스트 레인(캐시 히트)", "<300ms", "<300ms (달성)", "동일"],
                ["YOLO scooter confidence", "≈0.87", "0.939", "model_class_validation_report.md"],
                ["segmentation caution", "—", "0.908", "동일"],
                ["WS RTT", "<100ms", "달성", "tests"],
                ["씬 분류 지연", "—", "평균 11.27ms", "실기기 로그"],
            ]
        )
    )
    blocks.append(
        callout(
            "ANE 검증 엄밀성: Xcode Instruments Core ML 템플릿 15초 트레이스로 "
            "ANE 하드웨어 활동(ane-hw-intervals-internal) 247건을 칩 카운터 기록으로 직접 확인했습니다.",
            "green_background",
        )
    )

    blocks.append(h2("현재 구현의 부족한 점"))
    limits = [
        "stop 클래스 등 일부 클래스 미탐지(학습 데이터 부족) → 재학습 보강 필요.",
        "씬 분류기 게이트의 실외 표본 소수 → 다양한 환경 보강 필요.",
        "Android 온디바이스 성능 검증은 iOS 대비 미완(반사 fps 회귀 검증 진행 중).",
        "E2E 검증이 수동 실기기 실측에 의존 — 실기기 없이 CI에서 재현 가능한 자동 E2E 회귀 스위트가 부재.",
    ]
    for item in limits:
        blocks.append(bullet(rt(item)))

    blocks.append(h2("향후 추가·개선하고 싶은 기능"))
    futures = [
        "셀룰러/실환경용 단말 on-device 반사 레이어(네트워크 왕복 0) 정식화 — post-MVP 하이브리드 로드맵.",
        "LiDAR/Depth 기반 실거리 추정으로 거리 판정 정밀화.",
        "실내·야간 등 다양한 도메인 재학습으로 도메인 시프트 근본 완화.",
        "실기기 없이 돌릴 수 있는 E2E 자동 회귀 테스트 스위트 구축(KPI 게이트화).",
    ]
    for f in futures:
        blocks.append(numbered(rt(f)))
    blocks.append(divider())

    print(f"[5/6] 평가/개선: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"      appended {n}")
    blocks = []

    # ===== 7. 부록 =====
    blocks.append(h1("7. 부록 — 작업 이력 요약"))
    blocks.append(
        para(rt("docs/changelogs/kb.md의 약 285개 작업 로그를 날짜 단위로 압축한 요약입니다."))
    )

    history = [
        (
            "06-24",
            "전체·문서",
            "프로젝트 문서 기준선·디렉토리 골격(README·AGENTS·architecture·API/테스트/브랜치/파이프라인 명세, .env.example, requirements)",
        ),
        ("06-25", "3단계", "탐지·분할·게이트 백엔드 + Redis bus 구현, 테스트 21건"),
        (
            "06-26",
            "3·6단계",
            "보행이론 보고서·YOLO26n 통합테스트, 6단계 LangGraph 설계서+오케스트레이터 구현, 슬랙 연동",
        ),
        (
            "06-27",
            "6·1·공통",
            "GPU Monitor MCP 핫스왑, 통합 MCPManager+SSE 관제 API, 환경변수·배포 명세, 코드 품질 파이프라인",
        ),
        (
            "06-28",
            "2·6·공통",
            "2단계 캡처 백엔드 설계·구현(이중 스트림·asyncio.Queue), 문서 정합성 감사, gemma4-e4b 교체·지연 분석",
        ),
        (
            "06-30",
            "1·2단계",
            "온디바이스 모바일 앱 계획·설계서(iOS/Android 분리), Phase A~D 구현(서버 WS 라우터+클라 WS/이중 캡처)",
        ),
        (
            "07-01",
            "2·3·공통",
            "온디바이스 TFLite 추론 구조·햅틱/비프(78 테스트), 문서 링크 정합, 30개 문서 교차검증",
        ),
        (
            "07-04",
            "온디바이스·통신",
            "CoreML 완전 가속(det+seg ANE)·엔진 격리 설계, 파이프라인 안정화·expo-audio 마이그레이션, ngrok LTE 야외 테스트",
        ),
        (
            "07-05",
            "iOS·문서",
            "xcode-build-management 스킬, CoreML 벤치마크·이미지 압축(3.4MB→12KB)·햅틱/비프·1:1 캘리브레이션, YOLO 데이터셋 29종",
        ),
        (
            "07-07",
            "3·6·품질",
            "LangGraph 구조 정상화, 실내 오탐 완화 4연작(confidence·hit_count·co-occurrence·씬 분류기 게이트), 동적 반사 FPS, 바이너리 전송",
        ),
        (
            "07-09",
            "6·7·전체",
            "TTS 절단 근본원인(Piper→Supertonic·Frame Processor 전환), 4단계 미구현 보완, Dockerfile pygoruut 캐싱, dev 병합",
        ),
        (
            "07-11",
            "3·6·7·클라",
            "CoreML FP16·ANE, STT 신호음·AEC·오디오 블리드·hotwords, T맵 지도 패널, 재연결 백오프, event_id 구조화·위험도 SSOT, LiDAR 프로토타입",
        ),
        (
            "07-12",
            "서버·콘솔",
            "이벤트 프레임 보존·콘솔 렌더링, 오탐 판정 DB 컬럼, 레이턴시 계측 표시, 회원 등록 화면, 라이브 카메라 피드·텔레메트리 패널",
        ),
        (
            "07-13",
            "서버·콘솔·클라",
            "보도 이탈 판정(마스크·히스테리시스·점자블록), ngrok→Tailscale, TTS 캐시 프리워밍, N시 방향 안내, MCP 5종 구현",
        ),
        (
            "07-14",
            "콘솔·3·공통",
            "콘솔 디자인·타임라인 패널, Gildang 브랜딩, YOLO26n 260714 온디바이스, 씬 히스테리시스·Android ML Kit 씬 게이트",
        ),
        (
            "07-16",
            "3·6·콘솔·Git",
            "outdoor Option A 반사 억제, 인지 guide 구조화·패스트레인, 디버그 로그·RiskEventLog, dial_action Siri, kb→dev 병합",
        ),
        (
            "07-17",
            "3·6·5·통합",
            "필드테스트 M1~M7(큐 최신성·억제 재무장·소형객체 ApproachLost·발화가치·반사 후속 행동·계단 보정·세그5클래스), MID_RISK SSOT, LiDAR 검증 로깅",
        ),
        (
            "07-18",
            "병합·거리정책·스킬",
            "팀원 4브랜치 dev 통합, integration-test-orchestrator 스킬, 거리 정책 SSOT 1단계(Near 전용·episode 상태기계), 필드테스트 T1/T2/T3",
        ),
        (
            "07-19",
            "통합·콘솔·단말",
            "거리정책 2단계(LiDAR 자문)·검증 캡처, 콘솔 오디오 미러·거리구역 도식·Docker compose 통합, 음성 우선순위 4단·대기열",
        ),
        (
            "07-20",
            "3·7·인프라",
            "필드 피드백 다수 수정(노면 비중·Near 무반응·12시 회랑 분리), STT 목적지 인식 P0 6건, 대기열 위험도순 전환, Redis 트리밍·YOLO 스레드풀 분리",
        ),
        (
            "07-21",
            "다단계·CI·시연",
            "head_level 완화, P0/P1 과부하 백프레셔, Near 행동 클립·완주 우선·Medium 1회, 2계층 거리 오버레이, kb→dev mypy·jscpd CI, 시연 환경",
        ),
        (
            "07-24",
            "Android·6·ops",
            "Android det TFLite nms=False·android-gpu 배선, Ollama LAN keepalive·gpu_monitor, 클라우드 MariaDB(gildang_db)·R2 미디어 백엔드",
        ),
    ]
    blocks.append(
        table([["날짜", "단계/영역", "주요 작업 요약"]] + [[d, s, w] for d, s, w in history])
    )
    blocks.append(
        para(
            rt(
                "위 표는 반복 튜닝·버그픽스·문서 동기화·병합 등 동일 주제의 다수 항목을 날짜별로 묶어 압축한 것입니다. 개별 항목 전체는 "
            ),
            rt("docs/changelogs/kb.md", code=True),
            rt("에서 확인할 수 있습니다."),
        )
    )
    blocks.append(divider())

    # ===== 추가: 핵심 산출물 갤러리 =====
    blocks.append(h1("부록 A. 핵심 산출물 갤러리"))
    blocks.append(h3("브랜딩"))
    blocks.append(image_block(img("portfolio/app-icon.png"), "Gildang 앱 아이콘"))
    blocks.append(h3("Detection 결과 — 보행 안전 핵심 5종"))
    blocks.append(
        image_block(
            img("portfolio/sample-01-person.jpg"),
            "Detection 결과 — person(보행자) 클래스. 바운딩 박스 + 클래스명 + 신뢰도 표시",
        )
    )
    blocks.append(
        image_block(
            img("portfolio/sample-03-movable-signage.jpg"),
            "Detection 결과 — movable_signage(이동식 표지판) 클래스",
        )
    )
    blocks.append(
        image_block(
            img("portfolio/sample-04-traffic-light.jpg"),
            "Detection 결과 — traffic_light(신호등) 클래스",
        )
    )
    blocks.append(
        image_block(img("portfolio/sample-05-pole.jpg"), "Detection 결과 — pole(기둥/전주) 클래스")
    )
    blocks.append(h3("Detection 결과 (Bounding Box)"))
    blocks.append(
        image_block(img("portfolio/det-scooter.jpg"), "Detection — scooter(개인형 이동장치) 클래스")
    )
    blocks.append(
        image_block(
            img("portfolio/det-stroller.jpg"),
            "Detection — stroller(유모차) 클래스. 신뢰도 0.921로 안정적 탐지",
        )
    )
    blocks.append(
        image_block(
            img("portfolio/det-bollard.jpg"),
            "Detection — bollard(볼라드) 클래스. 보행 안전 핵심 사물",
        )
    )
    blocks.append(h3("Segmentation 결과 (노면 분할)"))
    blocks.append(
        image_block(
            img("portfolio/seg-caution.jpg"), "Segmentation — caution(주의 구역) 노면 클래스"
        )
    )
    blocks.append(
        image_block(
            img("portfolio/seg-roadway.jpg"),
            "Segmentation — roadway(차도) 노면 클래스. 보도 이탈 감지 대상 (신뢰도 0.68)",
        )
    )
    blocks.append(
        image_block(
            img("portfolio/seg-sidewalk.jpg"),
            "Segmentation — sidewalk_normal(일반 보도) 노면 클래스",
        )
    )
    blocks.append(
        callout(
            "노면 분할은 보도(sidewalk_normal)·주의구역(caution)·차도(roadway) 3종 결과를 식별합니다. "
            "점자블록(braille_normal) 클래스는 한국 실사 데이터 확보 후 재학습 예정으로 현재 결과에서 제외했습니다.",
            "gray_background",
        )
    )
    blocks.append(divider())

    blocks.append(h1("부록 B. 근거 자료"))
    blocks.append(
        table(
            [
                ["자료", "위치"],
                ["팀 공용 changelog", "docs/changelogs/kb.md"],
                ["iOS CoreML 벤치마크", "docs/ops/ondevice_coreml_benchmark.md"],
                ["클래스별 모델 검증 보고서", "docs/ops/model_class_validation_report.md"],
                ["지연 영향 분석", "docs/research/latency_impact_analysis.md"],
                ["야외 안내 정제 로드맵", "docs/research/outdoor_guidance_refinement_roadmap.md"],
                ["보행이론 인사이트", "docs/design/behavior_and_risk_insight.md"],
                ["시스템 아키텍처", "docs/design/architecture.md"],
                ["iOS CoreML 구현", "client/ios/CoreMLInferenceBridge.swift"],
                ["반사 게이트", "server/detection/gates/reflex_gate.py"],
                ["LangGraph 오케스트레이션", "server/orchestration/graph.py"],
                ["TTS 서비스", "server/tts/tts_service.py"],
            ]
        )
    )
    blocks.append(divider())
    blocks.append(
        para(
            rt(
                "본 문서는 팀 공용 changelog(docs/changelogs/kb.md)의 실제 작업 로그와 저장소 코드를 근거로, 본인이 직접 수행·이해한 내용을 중심으로 작성했습니다.",
                italic=True,
                color="gray",
            ),
        )
    )

    print(f"[6/6] 부록+갤러리: {len(blocks)} blocks")
    n = append_blocks(blocks)
    print(f"      appended {n}")

    print("\n=== DONE ===")


if __name__ == "__main__":
    run()
