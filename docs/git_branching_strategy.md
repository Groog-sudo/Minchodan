# Minchodan Git 브랜칭 전략

> **작성일**: 2026-06-24
> **버전**: v0.1.0

---

## 1. 개요

Minchodan 프로젝트는 3계층 브랜치 구조를 사용합니다. 모든 팀원은 자신의 개인 브랜치에서 작업하고, `dev` 브랜치를 거쳐 `master`에 반영합니다.

```text
master          (운영 기준선, 직접 커밋 금지)
  └── dev       (통합 개발 브랜치)
        ├── dg  (대근)
        ├── jh  (진형)
        ├── jy  (준영)
        ├── kb  (관범)
        └── th  (태현)
```

---

## 2. 브랜치 역할

| 브랜치 | 용도 | 보호 수준 | 병합 방식 |
| --- | --- | --- | --- |
| `master` | 운영 기준선. 배포 가능한 상태만 유지 | 보호됨 (직접 push 금지) | `dev`에서 병합 |
| `dev` | 통합 개발. 모든 기능이 모이는 곳 | 보호됨 (직접 push 금지) | 개인 브랜치 변경 사항 병합 |
| `dg`, `jh`, `jy`, `kb`, `th` | 개인 작업 브랜치 | 자유 push | 자유 커밋 |

---

## 3. 팀원 브랜치 매핑

| 이니셜 | 팀원명 | 담당 영역 (할당 가능) |
| --- | --- | --- |
| `dg` | 대근 | (할당 가능) |
| `jh` | 진형 | (할당 가능) |
| `jy` | 준영 | (할당 가능) |
| `kb` | 관범 | (할당 가능) |
| `th` | 태현 | (할당 가능) |

> 개인 문서 폴더는 사용하지 않으며, 모든 설계 문서는 `docs/` 폴더에서 공유로 관리합니다.

단계별 분업 인원수 제안은 `docs/minchodan_design_note.md` 각 단계의 **분업** 필드를 참조합니다.

| 단계 | 분업 제안 (design_note 기준) |
| --- | --- |
| 1 | RN 경험자 1~2명 (WS 연결 로직 집중·안정화) |
| 2 | 모바일 캡처/전송 1명 전담 |
| 3 | CV/PyTorch 경험자 1~2명 (Colab 검증  서버 이식) |
| 4 | 2명 주도 (문서 수집·전처리 1명, LangChain·DB 구축 1명) |
| 5 | 랭체인 1~2명 (검색 정확도·속도 집중 테스트) |
| 6 | 랭체인 숙련 1~2명 (프롬프트 튜닝 집중) |
| 7 | 모바일 1명 (수신·재생, 전체 지연 측정) |

---

## 4. 작업 흐름

### 4.1 일반 작업 흐름

```text
1. 개인 브랜치에서 작업 시작
2. 로컬에서 커밋 및 테스트
3. 개인 브랜치 변경 사항을 dev에 반영
4. 코드 리뷰 후 dev에 병합
5. dev 안정성 확인 후 master에 반영
6. master에 병합 (릴리스)
```

### 4.2 처음 브랜치 생성 (최초 1회)

```bash
# dev 브랜치 생성 (master 기준)
git checkout master
git pull origin master
git checkout -b dev
git push -u origin dev

# 개인 브랜치 생성 (dev 기준)
git checkout dev
git checkout -b dg    # 본인 이니셜로 변경
git push -u origin dg
```

### 4.3 일상 작업 루프

```bash
# 최신 dev 동기화
git checkout dev
git pull origin dev

# 개인 브랜치에서 작업
git checkout dg
git merge dev        # dev 최신 반영
# ... 코드 작성 ...
git add .
git commit -m "3단계: YOLO26 추론 래퍼 추가"
git push origin dg

# dev에 병합 (PR 기반)
gh pr create --base dev --head dg --title "3단계 YOLO26 추론 래퍼"
```

---

## 5. 커밋 메시지 규칙

| 접두어 | 용도 |
| --- | --- |
| `1단계:` | WebSocket 통신 관련 |
| `2단계:` | 카메라 캡처·전송 관련 |
| `3단계:` | 탐지·분할·게이트 관련 |
| `4단계:` | RAG DB 구축 관련 |
| `5단계:` | RAG 검색 관련 |
| `6단계:` | LangGraph 오케스트레이션 관련 |
| `7단계:` | TTS·음성 출력 관련 |
| `docs:` | 문서 작성·수정 |
| `infra:` | Docker/스크립트/환경 |
| `test:` | 테스트 추가·수정 |

예시: `3단계: Reflex Gate 고위험 클래스 임계값 조정`

---

## 6. PR 규칙

- 모든 `dev` 병합은 PR(Pull Request) 기반으로 진행합니다.
- PR 제목은 작업 단계와 핵심 내용을 포함합니다.
- PR 설명에 변경 파일과 검증 결과를 기재합니다.
- `master` 병합은 `dev` 안정성 확인 후 별도 PR로 진행합니다.

---

## 7. 주의 사항

- `master`와 `dev`에 직접 push하지 않습니다.
- 이모지는 커밋 메시지·코드·문서 어디에도 사용하지 않습니다.
- 작업 완료 후 [`README.md`](../README.md)의 **최근 변경 사항**을 업데이트합니다.
- Windows 로컬 Git은 `core.autocrlf=false`, `core.eol=lf`를 권장합니다.
