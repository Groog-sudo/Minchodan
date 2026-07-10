# Minchodan FastAPI Server Dockerfile
# 상세 명세: docs/deployment_guide.md 6절

FROM python:3.13-slim

# 시스템 패키지 설치 (OpenCV 의존성 libgl1 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    espeak \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# pygoruut 네이티브 바이너리(goruut, 약 96MB)를 빌드 타임에 미리 받아 이미지에 고정한다.
# server/tts/tts_service.py의 _phonemize()가 Pygoruut(writeable_bin_dir="")로 호출하면
# 라이브러리가 자체적으로 ~/.goruut(USER 미지정이므로 /root/.goruut)에 캐시하는데,
# 이 단계 없이 최초 요청 시점에 처음 다운로드되면 realtime_tts.py의 3초 TTS 타임아웃을
# 초과해 무음으로 폴백되는 문제가 실측 확인됐다(2026-07-09). 컨테이너가 배포마다 새로
# 생성돼도 이 레이어에서 이미 캐시가 채워진 채로 시작하도록, 실제 한국어 phonemize
# 호출까지 수행해 바이너리 다운로드와 정상 동작을 빌드 타임에 함께 검증한다.
RUN python -c "from pygoruut.pygoruut import Pygoruut; p = Pygoruut(writeable_bin_dir=''); print(p.phonemize(language='Korean', sentence='빌드 타임 캐시 확인'))"

# Supertonic TTS 모델 자산(ONNX, 약 380MB)을 빌드 타임에 미리 받아 이미지에 고정한다.
# pygoruut와 동일한 이유: 기본 TTS_ENGINE=supertonic이 컨테이너 최초 요청 시점에
# 다운로드를 시작하면 realtime_tts.py의 3초 TTS 타임아웃을 초과해 무음 폴백된다.
# 캐시 경로는 라이브러리 기본값(~/.cache/supertonic3, /app 바깥)을 그대로 쓴다 -
# server/models/ 하위에 두면 docker-compose.yml의 `../server:/app/server` 볼륨
# 마운트가 컨테이너 시작 시 이 레이어의 내용을 호스트 쪽으로 덮어써 버린다.
RUN python -c "from supertonic import TTS; t = TTS(auto_download=True); s = t.get_voice_style(voice_name='F1'); w, d = t.synthesize(text='빌드 타임 캐시 확인', lang='ko', voice_style=s, total_steps=8); print('Supertonic 캐시 완료, duration=', d)"

# 앱 코드는 docker-compose.yml에서 볼륨 마운트로 전달
# 포트 노출
EXPOSE 8000

# uvicorn 실행 (WS_HOST, WS_PORT는 .env에서 로드)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
