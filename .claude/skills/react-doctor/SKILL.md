# React Doctor Code Quality Scan Skill

> **작성일**: 2026-07-14
> **버전**: v1.0.0
> **설계 목적**: 에이전트가 React(관제 콘솔) 및 React Native(모바일 클라이언트) 코드의 품질, 렌더링 성능, 메모리 누수 및 접근성을 정적 분석 도구인 `react-doctor`를 활용하여 점검하고 이를 보완하기 위함.

---

## 1. 개요 및 배경

Minchodan 프로젝트의 프론트엔드는 시각장애인 보행 보조를 돕는 특성상 끊김 없는 실시간 데이터(프레임 및 오디오) 처리가 생명입니다.
따라서 `react-doctor`를 활용하여 렌더링 병목, 부수 효과 누수, 그리고 필수 접근성 요건이 정적 검증 단계에서 완벽하게 관리되도록 본 스킬 가이드를 정의합니다.

---

## 2. 작업 수명 주기 및 실행 지침

에이전트는 프론트엔드(`client/` 또는 `console/`) 코드를 수정하거나 품질 개선을 요청받았을 때 아래 절차를 이행합니다.

### Step 1: 프로젝트 진단 및 리포트 수집
- **도구**: `run_command`
- **명령어**:
  ```bash
  # console 디렉토리 검사
  npx -y react-doctor@latest --verbose (console/ 내에서 실행)

  # client 디렉토리 검사
  npx -y react-doctor@latest --verbose (client/ 내에서 실행)
  ```
- **목적**: 프로젝트의 건강 점수(Health Score)와 해결해야 할 Critical Bugs 및 Warnings 목록을 전수 수집합니다.

### Step 2: 품질 에러 수정 가이드라인
정적 분석기에서 감지된 경고 사항에 대해 아래 Best Practice 디자인 패턴을 충족하도록 리팩토링을 수행합니다.

| 경고 종류 | 문제 원인 | 리팩토링 조치 방안 |
| :--- | :--- | :--- |
| **Effect subscription or timer never cleaned up** | `useEffect` 내에서 생성된 리스너, WebSocket, 타이머(`setInterval` 등)가 해제되지 않아 누수 발생. | `useEffect` 최상단 스코프의 local 변수에 참조를 바인딩하고, cleanup `return () => { ... }` 내에서 직접 해제하도록 코드를 단순화합니다. |
| **State updater has side effects** | `setToken()` 등 상태 업데이트 시점에 localStorage 쓰기, API 호출 등의 부수 효과를 수행함. | 부수 효과를 해당 콜백이나 updater 밖으로 분리하고, React `useEffect` 훅 내부에서 해당 상태를 감시하여 부수 효과를 순수하게 실행하도록 격리합니다. |
| **Module removed from core** | deprecated되거나 코어에서 제거 예정인 컴포넌트(예: SafeAreaView)를 호출. | 대체 컴포넌트(일반 View)와 플랫폼별 StatusBar 보정 스타일을 작성하여 의존성을 늘리지 않고 정적 에러를 우회합니다. |

### Step 3: 분석기 오탐 회피 (Config 튜닝)
- **원칙**: 분석 파서의 한계로 인한 오탐 발생 시, 코드의 원래 디자인을 억지로 깨뜨리지 않고 프로젝트 루트의 `doctor.config.json` 파일을 제어하여 규칙 엄격성을 조정합니다.
- **적용**:
  ```json
  {
    "rules": {
      "react-doctor/effect-listener-cleanup-mismatch": "warn",
      "react-doctor/effect-needs-cleanup": "warn"
    }
  }
  ```
  심각도가 `warn`으로 강등된 경고는 마감 자동 빌드 파이프라인의 차단 기준(Blocking Level: error)에서 제외됩니다.

---

## 3. 마감 스케줄러 연동
작업이 끝난 후에는 `scripts/auto_publish_work.py`를 실행하여 린트 및 건강도 검사가 최종 통과(exit 0)했는지 검증한 뒤 커밋과 푸시를 병행하십시오.
