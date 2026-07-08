# Minchodan 네비게이션 모듈 통합(Integration) 가이드

이 문서는 개발 완료된 독립 네비게이션 모듈(`navigation`)을 기존 `Minchodan` 프로젝트에 안전하게 통합하고 실행하기 위한 단계별 절차를 안내합니다.  
**기존 Minchodan 프로젝트의 어떠한 코드도 수정하지 않고** 안전하게 합칠 수 있도록 설계되었습니다.

---

## 1단계: 모듈 폴더 이동 (합치기)

가장 먼저 임시 검증 디렉토리에 있는 `navigation` 폴더를 `Minchodan` 프로젝트 내부로 이동시킵니다.

1. `d:\2025_langchain_ydg\TeamProject\navigation` 폴더를 통째로 복사합니다.
2. `Minchodan` 프로젝트의 `server` 디렉토리 하위로 붙여넣습니다.
   * **최종 복사 경로**: `d:\2025_langchain_ydg\TeamProject\Minchodan\server\navigation\`

> [!NOTE]
> `Minchodan` 프로젝트 구조의 일관성을 위해 파이썬 백엔드 소스들이 모여있는 `server` 폴더 아래에 위치시키는 것이 가장 이상적입니다. 기존 코드 수정은 일절 필요 없습니다.

---

## 2단계: 환경 변수 (API Key) 설정

네비게이션에서 사용하는 TMAP 보행자 경로 API 연동을 위해 발급받은 TMAP API Key를 등록합니다. 

`Minchodan` 루트 디렉토리에 있는 `.env` 파일(`d:\2025_langchain_ydg\TeamProject\Minchodan\.env`)을 열고 아래 항목을 추가합니다.

```env
# --- TMAP Navigation API Key ---
TMAP_APP_KEY=실제_발급받은_티맵_앱_키
```

> [!TIP]
> 만약 전체 프로젝트의 `.env` 파일을 공용으로 쓰지 않고 네비게이션만 개별 키를 적용하고 싶다면, `Minchodan/server/navigation/.env` 파일을 새로 생성하여 그 안에 `TMAP_APP_KEY=키값` 형태로 기입하셔도 모듈 내부의 멀티 레벨 로더가 정상적으로 감지하여 읽어옵니다.

---

## 3단계: 가상 환경 의존성(Dependency) 설치

모듈 내에서 로컬 음성 발화 기능 및 백엔드 라우팅을 정상적으로 수행하기 위한 패키지들을 설치합니다.  
Minchodan 프로젝트의 가상 환경(`venv`)이 활성화된 상태에서 아래 패키지들을 추가로 설치합니다.

### 1. `pyttsx3` 설치 (선택사항 - 로컬 TTS 발화용)
로컬 터미널에서 TTS를 직접 말하게 하려면 `pyttsx3` 모듈이 필요합니다.
```bash
# 가상 환경 활성화 후 터미널에서 실행
d:\2025_langchain_ydg\TeamProject\Minchodan\venv\Scripts\pip install pyttsx3
```

### 2. 기본 의존성 확인
기존 Minchodan에 설치되어 있는 `fastapi`, `uvicorn`, `requests`, `python-dotenv` 등은 이미 충족되어 있으므로 별도의 추가 설치가 필요 없습니다.

---

## 4단계: 개별 구동 및 검증

통합 완료 후, 네비게이션 모듈이 단독으로 정상 실행되는지 확인합니다.

### 1. 웹소켓 및 지도 시뮬레이터 서버 구동
```bash
# CWD를 복사한 navigation 디렉터리로 변경
cd d:\2025_langchain_ydg\TeamProject\Minchodan\server\navigation

# Minchodan 가상환경 파이썬으로 서버 기동
..\..\venv\Scripts\python.exe server.py
```
* **구동 확인**: 브라우저를 켜고 `http://localhost:8001/`에 접속하여 Leaflet 지도 화면이 뜨고 목적지 검색/가상 보행 시뮬레이션 및 안내가 정상 청취되는지 검증합니다.

### 2. CLI 전용 시뮬레이터 구동 (터미널)
```bash
# CWD: d:\2025_langchain_ydg\TeamProject\Minchodan\server\navigation
..\..\venv\Scripts\python.exe pedestrian_navigation.py
```
* **구동 확인**: 출발지(예: 서울역) 및 목적지(예: 숭례문)를 입력해 단계별 가상 노드 이동과 음성 로그가 콘솔에 정상 출력되는지 검증합니다.
