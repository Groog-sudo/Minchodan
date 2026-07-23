# Minchodan FastAPI Server Dockerfile
# 상세 명세: docs/ops/deployment_guide.md 6절

FROM python:3.13-slim

# 시스템 패키지 설치 (OpenCV 의존성 libgl1 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    espeak \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치 (캐시 최적화)
COPY requirements.txt .
# chromadb/faster-whisper/supertonic/piper-tts가 onnxruntime(CPU)를 재의존으로
# 끌어와 onnxruntime-gpu 휠을 덮어쓴다. GPU EP를 쓰려면 CPU 패키지를 제거한 뒤
# gpu 휠을 강제 재설치해야 한다(둘 다 동일 모듈명 onnxruntime).
RUN pip install --no-cache-dir -r requirements.txt \
    && pip uninstall -y onnxruntime \
    && pip install --no-cache-dir --force-reinstall onnxruntime-gpu==1.27.0

# onnxruntime-gpu 1.27(CUDA 13)은 시스템 toolkit 대신 PyTorch NVIDIA wheel의
# libcudart/cudnn을 찾는다. 빌드 타임 Supertonic 캐시 RUN과 런타임 공통.
# cublas(cu12)는 ctranslate2(faster-whisper CUDA) dlopen 대상.
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.13/site-packages/nvidia/cu13/lib:/usr/local/lib/python3.13/site-packages/nvidia/cudnn/lib:/usr/local/lib/python3.13/site-packages/nvidia/cublas/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

# 런타임 프로세스와 모델 캐시 준비는 권한이 제한된 전용 사용자로 수행한다.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin minchodan \
    && chown -R minchodan:minchodan /app
ENV HOME=/home/minchodan
USER minchodan

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

# 2026-07-19 실측 발견: ultralytics가 모델 로드/추론 시마다 체크포인트에 내장된
# requirements를 현재 설치본과 비교해 불일치하면 런타임 중 pip install로 조용히
# 갱신한다(AUTOINSTALL 기본값 True). 이미 임포트된 모듈과 방금 갱신된 디스크 상의
# 패키지가 어긋나면서 'Conv' object has no attribute 'bn' 추론 오류가 프레임마다
# 재발했다. requirements.txt로 버전을 이미 고정하고 있으므로 이미지 레벨에서
# 기본값으로 런타임 자동 설치를 끈다(비협상 아님, 순수 안정성 수정). 캐시 무효화를
# 피하기 위해 무거운 RUN 레이어(위 pygoruut/Supertonic 다운로드) 이후에 배치한다.
ENV YOLO_AUTOINSTALL=False

# 앱 코드는 docker-compose.yml에서 볼륨 마운트로 전달
# 포트 노출
EXPOSE 8000

# uvicorn 실행 (WS_HOST, WS_PORT는 .env에서 로드)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
