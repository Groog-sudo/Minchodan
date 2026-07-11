# TTS pyttsx3 교체 작업 결과 보고서

기존에 설치 중이던 무거운 VITS 모델 `sherpa-melotts-kr-int8` (51MB)을 완전 삭제하고, OS 내장 오디오 API 래퍼인 `pyttsx3` 기반으로 실시간 인지 TTS 엔진을 교체 완료했습니다.

---

## 주요 작업 내역

### 1. 의존성 및 패키지 설정 갱신
- [requirements.txt](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/requirements.txt): 무거운 `sherpa-onnx`를 삭제하고 `pyttsx3` 및 `pywin32` 패키지를 추가했습니다.
- [docker/Dockerfile](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docker/Dockerfile): 도커(리눅스) 환경에서 `pyttsx3`가 espeak 오디오 드라이버를 정상적으로 적재할 수 있도록 시스템 의존성에 `espeak` 패키지 설치를 추가했습니다.
- 다운로드 중단 흔적 정리:
  - `scripts/download_sherpa_model.py` 스크립트를 삭제했습니다.
  - `server/models/sherpa-onnx` 하위 임시 폴더 및 파일들을 모두 지웠습니다.

### 2. TTS 서비스 구현 코드 교체
- [server/tts/tts_service.py](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/server/tts/tts_service.py):
  - 무거운 `SherpaTTSService` 구현체를 완전히 삭제했습니다.
  - `Pyttsx3TTSService` 클래스를 새로 정의하여 `NamedTemporaryFile`을 활용해 WAV 형식의 음성을 파일에 합성한 뒤 바이너리 데이터를 읽어 반환하도록 설계했습니다.
  - 비동기 이벤트 루프 블로킹 방지를 위해 `asyncio.to_thread`를 사용하여 별도 OS 스레드에서 합성을 처리하게 위임했습니다.
  - Windows의 SAPI5 드라이버 멀티스레드 세이프성 확보를 위해, 스레드 호출 시 `pythoncom.CoInitialize()` 및 `pythoncom.CoUninitialize()`로 COM 스레드 컨텍스트 가드를 적용하여 런타임 크래시를 방지했습니다.
  - `get_tts_service()` 팩토리의 기본 엔진 반환값을 `pyttsx3`로 업데이트했습니다.

### 3. 설정 및 환경 명세 갱신
- [.env](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/.env) 및 [.env.example](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/.env.example): 기본 TTS 엔진을 `TTS_ENGINE=pyttsx3`로 변경했습니다.
- [docs/ops/environment_variables.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/ops/environment_variables.md): `TTS_ENGINE` 환경변수의 가용 정보에 `pyttsx3`를 추가하고 기본값 설명을 갱신했습니다.
- [docs/changelogs/dg.md](file:///d:/2025_langchain_ydg/TeamProject/Minchodan/docs/changelogs/dg.md): 기존 내용은 보존한 채, 파일 마지막 부분에 안드로이드 실기기 무선 연동 테스트 내역 및 이번 TTS pyttsx3 변경 업데이트 로그를 누적 기록했습니다.

---

## 검증 결과

### 수동 스모크 테스트 수행
- 임시 테스트 파일 `scratch/test_pyttsx3.py`를 실행하여 가상환경(venv)에서의 Pyttsx3TTSService 동작을 정상 확인했습니다.
- 한국어 안내 문장을 합성하여 340,076 바이트의 온전한 WAV 데이터가 성공적으로 생성 및 저장되는 것을 검증했습니다.
- 테스트 완료 후 임시로 생성된 테스트 WAV 파일(`test_output.wav`)을 제거하여 저장소를 정리했습니다.
