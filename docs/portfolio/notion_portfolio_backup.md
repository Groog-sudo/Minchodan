# Gildang(길당) 노션 포트폴리오 백업

> **작성일**: 2026-07-27
> **버전**: v0.3.9
> **노션 원본**: https://app.notion.com/p/Gildang-3aa6e291277680d09a44c8cad1bd9885
> **노션 페이지 ID**: `3aa6e291-2776-80d0-9a44-c8cad1bd9885`
> **이미지 호스팅**: Cloudflare R2(`minchodan-event-frames/portfolio/`)

본 문서는 노션 포트폴리오 페이지의 로컬 Markdown 백업입니다. 노션 원본과 동일한 구조(15섹션)를 유지하며, 이미지는 R2 presigned URL(7일 유효) 대신 로컬 파일 경로로 표기합니다.

---

## 빌드 정보

| 항목 | 내용 |
| :--- | :--- |
| 빌드 스크립트 | `scripts/notion/build_portfolio.py` |
| 노션 API | REST v1 (`/blocks/{id}/children`) |
| 추가 블록 수 | 190개 |
| 이미지 블록 | 14개 |
| 테이블 블록 | 9개 |
| 이미지 소스 | `client/assets/`, `data/validation_samples/results/` |

---

## 섹션 구조

1. **표지** — 프로젝트명·과제명·작성자·팀 구성
2. **1. 프로젝트 개요** — 개발 목적, 이중 경로 분리 원칙, 주요 사용자, 주요 기능
3. **2. 프로젝트 전체 구조** — 기술 스택 표, 데이터 처리 흐름(ASCII)
4. **3. 본인의 담당 역할** — 직접 수행 vs 팀 작업 매트릭스, 연결 지점
5. **4-A. iOS 온디바이스 추론 파이프라인 & Xcode 빌드** — CoreMLInferenceBridge.swift 핵심 코드
6. **4-B. 3단계 반사 게이트** — class-agnostic 설계
7. **4-C. 6단계 LangGraph 계층 오케스트레이션** — L1/L2/L3 + fast_lane
8. **4-D. 협업 인프라** — 스킬 저작·CI·시연 환경·병합 정합성
9. **4-E. 운영 콘솔 프론트엔드** — LiveCameraFeed·DeviceTelemetryPanel 등
10. **4-F. 7단계 TTS·음성 안내 파이프라인** — Supertonic + 이중 채널
11. **5. 문제 해결 과정** — 7개 트러블슈팅(5-A~5-G)
12. **6. 프로젝트 평가 및 개선 방향** — 성과·KPI 실측·부족한 점·향후 계획
13. **7. 부록 — 작업 이력 요약** — 06-24~07-24 날짜별
14. **부록 A. 핵심 산출물 갤러리** — 14개 이미지
15. **부록 B. 근거 자료** — changelog·벤치마크·검증 보고서 경로

---

## 이미지 목록 (로컬 경로)

| 노션 블록 | 로컬 원본 | R2 키 |
| :--- | :--- | :--- |
| 표지 로고 | `client/assets/gildang-logo.jpeg` | `portfolio/gildang-logo.jpg` |
| 앱 아이콘 | `client/assets/icon.png` | `portfolio/app-icon.png` |
| Detection person | `data/validation_samples/results/detection/person/person_1_result.jpg` | `portfolio/sample-01-person.jpg` |
| Detection bicycle | `data/validation_samples/results/detection/bicycle/bicycle_1_result.jpg` | `portfolio/sample-02-bicycle.jpg` |
| Detection movable_signage | `data/validation_samples/results/detection/movable_signage/movable_signage_1_result.jpg` | `portfolio/sample-03-movable-signage.jpg` |
| Detection traffic_light | `data/validation_samples/results/detection/traffic_light/traffic_light_1_result.jpg` | `portfolio/sample-04-traffic-light.jpg` |
| Detection pole | `data/validation_samples/results/detection/pole/pole_1_result.jpg` | `portfolio/sample-05-pole.jpg` |
| Detection bollard | `data/validation_samples/results/detection/bollard/bollard_1_result.jpg` | `portfolio/det-bollard.jpg` |
| Detection scooter | `data/validation_samples/results/detection/scooter/scooter_1_result.jpg` | `portfolio/det-scooter.jpg` |
| Detection stroller | `data/validation_samples/results/detection/stroller/stroller_1_result.jpg` | `portfolio/det-stroller.jpg` |
| Segmentation caution | `data/validation_samples/results/segmentation/caution/caution_1_result.jpg` | `portfolio/seg-caution.jpg` |
| Segmentation roadway | `data/validation_samples/results/segmentation/roadway/roadway_2_result.jpg` | `portfolio/seg-roadway.jpg` |
| Segmentation 일반 보도 | `data/validation_samples/results/segmentation/sidewalk_normal/sidewalk_normal_1_result.jpg` | `portfolio/seg-sidewalk.jpg` |

> **이미지 검증 이력**: 2026-07-27 VLM 분석으로 박스/마스크 정확도 검증. `wheelchair`(사람에 박스, 표지판 오탐지)와 `braille_normal`(벽면 segmentation)은 3종 전부 부적합으로 판정되어 제거. wheelchair 자리는 stroller(신뢰도 0.921)로 대체. braille_normal은 한국 실사 데이터 확보 후 재학습 예정.

---

## 재빌드 방법

```bash
# 1. R2 presigned URL 갱신 (7일마다 만료)
venv/bin/python -c "
import boto3, json
from botocore.client import Config
s3 = boto3.client('s3',
    endpoint_url='https://246527ea5d04caad740133e20614ecd9.r2.cloudflarestorage.com',
    aws_access_key_id='12854b0f22fbd8b8c7dbfa3a283611d9',
    aws_secret_access_key='d666a28ae9eaa45da5670800cd76e79af76c196aa09640c85b3479153709d1b8',
    region_name='auto', config=Config(signature_version='s3v4'))
keys=[l.split('|')[-1].strip().strip('\`') for l in open('docs/portfolio/notion_portfolio_backup.md') if 'portfolio/' in l]
urls={k: s3.generate_presigned_url('get_object', Params={'Bucket':'minchodan-event-frames','Key':k}, ExpiresIn=604800) for k in set(keys)}
json.dump(urls, open('/tmp/r2_urls.json','w'), indent=2)
"

# 2. 노션 페이지 재빌드 (기존 블록 삭제 후)
venv/bin/python scripts/notion/build_portfolio.py
```

> **주의**: 노션 presigned URL은 노션이 한 번 가져가면 자체 CDN에 영구 캐싱됩니다. 단, 노션 페이지를 새로 빌드할 때는 presigned URL이 유효한 상태에서 실행해야 합니다.
