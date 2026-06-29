# Minchodan FastAPI Server Dockerfile
# 상세 명세: docs/deployment_guide.md 6절

FROM python:3.13-slim

# 시스템 패키지 설치 (OpenCV 의존성 libgl1 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python 의존성 설치 (캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드는 docker-compose.yml에서 볼륨 마운트로 전달
# 포트 노출
EXPOSE 8000

# uvicorn 실행 (WS_HOST, WS_PORT는 .env에서 로드)
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
