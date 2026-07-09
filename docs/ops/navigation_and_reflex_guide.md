# [가이드] TTS · 반사경로 · Navigation 종합 연동 및 개발 가이드

> **작성일**: 2026-07-08
> **버전**: v2.2.0
> **수신**: 역할 C 개발 담당 팀원 및 백엔드 파이프라인 개발팀

본 문서는 시각장애인 보행 보조 플랫폼의 **TTS(Piper CLI) 배포 계획**, **지연속도 최소화를 위한 비프음/햅틱 기반 반사 경로 설계**, 그리고 **다중 OS 환경에서의 길안내 엔진 크래시 방지 설계**를 다루는 종합 개발 가이드입니다.

---

## 1. 역할 C 기존 작업 명세 및 범위

본 역할 담당자는 다음 4가지 핵심 인프라 및 연동 작업 항목을 제어합니다.

* **① Piper CLI 바이너리 설치 및 배포 문서화**: 인지 경로 실시간 TTS 합성을 위한 로컬 엔진 구축.
* **② 반사 사전합성 클립 생성 스크립트 작성**: 긴급 대응을 위한 사전합성 오디오 구축 (※ 수정 사항 반영으로 비프음/햅틱 규격 문서화 및 데이터 구축으로 대체).
* **③ [reflex_clip_sender.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/tts/reflex_clip_sender.py) 정리**: 기존 사전합성 음성 발송 모듈의 미사용 코드 거동 및 채널 최적화.
* **④ server/navigation/ 모듈 정리**: [tts_engine.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/navigation/tts_engine.py)의 `winsound` macOS/Linux 크래시 방지 교체 및 린트 정리, 통합 테스트 신규 작성.

---

## 2. 변경 관리 (수정 사항 및 Rationale)

### 2.1. 수정 내용
* **기존 사양**: 반사 경로(Reflex Path) 조우 시, 사전에 합성된 음성 파일(`reflex_clips/*.mp3`)을 로드하여 클라이언트로 전송 및 재생.
* **수정 사양**: 반사 경로 조우 시, 음성 파일 전송을 완전히 배제하고 오직 **비프음 유형(주파수, 횟수) 및 햅틱 진동 유형(세기, 패턴)의 JSON 수치 제어 데이터**만 웹소켓으로 단말에 전송.

### 2.2. 수정 이유 (Rationale)
* **초저지연 경보 구현**: 음성 파일(MP3 등)은 네트워크 전송 크기가 크고, 단말기가 이를 수신한 후 오디오 디코더를 거쳐 사운드 장치로 출력하기까지 수십~수백 밀리초(ms)의 연산 지연이 발생합니다.
* **즉각적 물리 반응 유도**: 위험 감지 즉시 0ms에 가깝게 하드웨어적으로 반응하기 위해, 데이터 사이즈가 극소화된 제어 신호 패킷만 보내 즉시 단말기 내장 햅틱 모터와 비프 스피커를 울리도록 연동 아키텍처를 최적화했습니다.

---

## 3. 코드 수정 가이드라인 및 이유 (개발 참고용)

### 3.1. [reflex_clip_sender.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/tts/reflex_clip_sender.py) 수정 가이드
* **수정 가이드**:
  1. `REFLEX_CLIP_MAP` 및 `_resolve_reflex_clip` 등 MP3 음성 파일 매핑 로직을 제거합니다.
  2. `data/reflex_guidelines.json`을 읽어 `alert_id`에 할당된 비프음 패턴(`beep_pattern`)과 햅틱 패턴(`haptic_pattern`)을 조회하는 헬퍼 함수를 구축합니다.
  3. `send_reflex_clip` 내부 페이로드 조립 시, `"clip": ""`로 비워 전송 속도를 단축하고 아래와 같이 패턴 데이터를 주입해 웹소켓으로 고우선 송출합니다.
```python
payload = {
    "type": "reflex_alert",
    "event_id": event_id,
    "device_id": device_id,
    "alert_id": alert_id,
    "direction": direction,
    "clip": "", # 음성 배제
    "beep_pattern": resolved_beep_pattern,   # 주파수, 시간, 반복수
    "haptic_pattern": resolved_haptic_pattern, # 강도, 유형
    "ts": int(time.time() * 1000)
}
```
* **수정 이유**: 네트워크 대역폭 점유를 없애고 단말기가 파싱 즉시 비프/진동 API로 직행하도록 제어 명령만 전달하기 위함입니다.

### 3.2. [tts_engine.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/navigation/tts_engine.py) 수정 가이드
* **수정 가이드**:
  1. 파일 상단의 `import winsound` 구문을 삭제하고, 아래와 같이 플랫폼 환경을 검사하여 동적으로 가드 임포트 처리합니다.
```python
WINSOUND_AVAILABLE = False
if sys.platform == "win32":
    try:
        import winsound
        WINSOUND_AVAILABLE = True
    except ImportError:
        pass
```
  2. `speak` 내의 `winsound.Beep` 호출 지점을 `WINSOUND_AVAILABLE` 분기 처리하고, 비-윈도우(macOS/Linux) 환경에서는 `sys.stdout.write('\a')` 및 CLI print 경고로 안전하게 폴백하도록 수정합니다.
* **수정 이유**: 리포지토리 기동 시 macOS/Linux 계열 개발 환경에서 `winsound` 모듈 부재로 유발되는 `ImportError` 크래시를 원천 해결하여 기동 안정성을 확보하기 위함입니다.

---

## 4. Piper CLI 로컬 TTS 배포 가이드 (인지 경로용)

인지 경로(Cognitive Path)에서는 자연스러운 20자 이내의 종합 우회 안내문을 출력해야 하므로 로컬 TTS인 Piper를 정상 가동합니다.

### 4.1. 설치 절차
* **바이너리**: [GitHub Piper Releases (v1.2.0)](https://github.com/rhasspy/piper/releases) 에서 플랫폼에 맞는 압축 파일 다운로드 및 압축 해제.
* **가중치**: `ko_KR-giga-medium.onnx` 및 `.onnx.json` 파일을 `server/models/piper/`에 배치.
* **Python 연동**: `asyncio.create_subprocess_exec` 서브프로세스를 기동하여 텍스트를 stdin으로 넣고 Raw PCM 오디오를 stdout으로 받아 WAV 인코딩 후 웹소켓 응답합니다.
