# Minchodan 운영 콘솔 Dockerfile (통합 테스트용 dev 이미지)
# 2026-07-19: integration-test-orchestrator 스킬 §5-B가 호스트에서 npm run dev
# 하던 단계를 compose 통합으로 대체하기 위해 신규 추가. prod용 nginx 멀티스테이지는
# 향후 별도 추가 예정.

FROM node:20-alpine

WORKDIR /app

# package.json만 먼저 복사해 의존성 캐시 레이어 분리
COPY package.json package-lock.json* ./

RUN npm install

# 소스는 compose에서 볼륨 마운트하지만 이미지 단독 실행(예: CI)도 대비해 복사
COPY . .

EXPOSE 5174

# Vite dev 서버. compose에서 VITE_PROXY_TARGET 환경 변수로 FastAPI 컨테이너를 가리킴
CMD ["npm", "run", "dev"]
