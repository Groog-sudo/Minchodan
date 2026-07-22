"""
LLMClientFactory 구현 파일.
Ollama 공식 SDK 및 httpx를 사용하여, 외부 langchain_community/langchain_openai 의존성 없이
로컬 gemma4-e4b 및 상용 GPT-4o-mini 모델 간의 비동기 호출 및 핫스왑을 지원합니다.
"""

import asyncio
import contextlib
import logging
import os
import sys

import httpx
from dotenv import load_dotenv

# 💡 [면접 대비 주석 - 왜 ollama import를 top에서 빼나]
# Q. ollama 패키지를 그냥 top에서 import하면 안 되나요?
# A. "시연/운영 환경에서는 Ollama 프로세스를 띄우지 않고 상용 Gemini API만 쓴다.
#    ollama 파이썬 패키지도 시연 환경에서는 설치하지 않으므로, top에서 import하면
#    LLMClientFactory 모듈 로드 자체가 ImportError로 실패해 서버 기동이 막힌다.
#    그래서 SimpleOllamaClient.__init__ 안에서 지연 import한다. 시연 환경에서는
#    LLM_PROVIDER=gemini이므로 SimpleOllamaClient 인스턴스가 생성되지 않아
#    ollama 패키지가 없어도 서버가 정상 기동한다."

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != "utf-8":
    with contextlib.suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

logger = logging.getLogger(__name__)

# Compute relative paths safely (guide 3.3)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
env_path = os.path.join(root_dir, ".env")

# Load environment configuration (guide 3.4)
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)


class LLMResponse:
    """
    LangChain의 AIMessage 응답 규격을 가상화한 경량 응답 객체.
    """

    def __init__(self, content: str):
        self.content = content


class SimpleOllamaClient:
    """
    Ollama 공식 SDK를 활용한 비동기 LLM 호출 클라이언트.
    """

    def __init__(self, model_name: str, base_url: str):
        # ollama 패키지 지연 import (시연 환경에서는 ollama 패키지 미설치 허용)
        import ollama

        self.model_name = model_name
        self.base_url = base_url
        # AsyncClient 인스턴스 생성 (CPU 환경의 Ollama Gemma4 추론 지연을 고려하여 타임아웃을 120초로 대폭 상향)
        self.client = ollama.AsyncClient(host=base_url, timeout=120.0)

    async def ainvoke(self, messages: list) -> LLMResponse:
        """
        SystemMessage, HumanMessage 리스트를 Ollama 메시지 포맷으로 변환해 비동기 호출합니다.
        """
        formatted_messages = []
        for msg in messages:
            # LangChain 메시지 객체 대응 및 dict 대응
            if hasattr(msg, "type"):
                role = "system" if msg.type == "system" else "user"
                content = msg.content
            else:
                role = msg.get("role", "user")
                content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        logger.info(f"Ollama async chat invocation: model={self.model_name}")
        # think=False: gemma4:e4b는 추론(thinking) 모드가 기본 활성화된 모델이라,
        # 이를 끄지 않으면 응답 토큰 예산(num_predict)을 내부 추론에서 전부 소진해
        # content가 항상 빈 문자열로 반환되는 문제가 있었다(2026-07-08 실측 확인).
        response = await self.client.chat(
            model=self.model_name,
            messages=formatted_messages,
            options={"temperature": 0.3, "num_predict": 100},
            think=False,
        )
        content = response.get("message", {}).get("content", "").strip()
        return LLMResponse(content)


class SimpleOpenAIClient:
    """
    httpx를 활용한 비동기 OpenAI API 호출 클라이언트.
    """

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY가 비어 있습니다.")

    async def ainvoke(self, messages: list) -> LLMResponse:
        """
        SystemMessage, HumanMessage 리스트를 OpenAI 메시지 포맷으로 변환해 API 호출합니다.
        """
        formatted_messages = []
        for msg in messages:
            if hasattr(msg, "type"):
                role = "system" if msg.type == "system" else "user"
                content = msg.content
            else:
                role = msg.get("role", "user")
                content = msg.get("content", "")
            formatted_messages.append({"role": role, "content": content})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": 0.3,
            "max_tokens": 50,
        }

        logger.info(f"OpenAI API async invocation: model={self.model_name}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            res_data = response.json()

        content = res_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return LLMResponse(content)


class SimpleGeminiClient:
    """
    httpx를 활용한 비동기 Google Gemini API 호출 클라이언트.
    """

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY가 비어 있습니다.")

    async def ainvoke(self, messages: list) -> LLMResponse:
        """
        SystemMessage, HumanMessage 리스트를 Gemini API에 맞는 메시지 형식으로 변환하여 비동기 호출합니다.
        """
        contents = []
        system_instruction_text = ""

        for msg in messages:
            if hasattr(msg, "type"):
                role_type = msg.type
                content = msg.content
            else:
                role_type = msg.get("role", "user")
                content = msg.get("content", "")

            if role_type == "system":
                # Gemini API v1beta에서는 system_instruction을 별도 필드로 설정하거나
                # 또는 대화의 처음에 포함할 수 있음. 여기서는 system_instruction 텍스트로 보관.
                system_instruction_text = content
            else:
                # Gemini 역할은 'user'와 'model'만 허용됨
                role = "user" if role_type in ("user", "human") else "model"
                contents.append({"role": role, "parts": [{"text": content}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        # 💡 [면접 대비 주석 - maxOutputTokens vs 컨텍스트]
        # Q. GEMINI_MAX_OUTPUT_TOKENS=180 이면 입력 RAG 문서가 잘리나?
        # A. 아니다. maxOutputTokens는 "생성(출력)" 토큰 상한이다. 입력 컨텍스트 창과는 별개.
        #    생활지원 답이 512로 길면 TTS가 중간에 끊기는 실측이 있어 기본 180으로 짧게 둔다.
        # [하드 코딩 부분 - 핵심] 기본 180, env로 조정, 32~8192 클램프.
        try:
            max_output_tokens = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "180"))
        except ValueError:
            max_output_tokens = 180
        max_output_tokens = max(32, min(max_output_tokens, 8192))

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": max_output_tokens,
            },
        }

        if system_instruction_text:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction_text}]}

        headers = {"Content-Type": "application/json"}

        logger.info(f"Gemini API async invocation: model={self.model_name}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            res_data = response.json()

        try:
            content = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            logger.error(f"Gemini API 응답 파싱 실패: {e}, 응답: {res_data}")
            content = ""

        return LLMResponse(content)


class LLMClientFactory:
    """
    BaseChatModel과 호환되는 클라이언트의 싱글톤 인스턴스를 동적으로 핫스왑 관리하는 팩토리 클래스.
    """

    _ollama: SimpleOllamaClient = None
    _openai: SimpleOpenAIClient = None
    _gemini: SimpleGeminiClient = None
    # 시연/운영 기본 gemini(상용 API). start_gpu_monitor가 LLM_PROVIDER로 덮어쓴다.
    _current_provider: str = ""
    _monitor_task: asyncio.Task = None
    # 2026-07-21: 메트릭 발행(Redis I/O)을 핫스왑 판정 루프와 분리하기 위한 in-flight 태스크.
    # 직전 발행이 진행 중이면 이번 주기 발행은 건너뛰어(최신 상태만 중요) 루프 주기를 지킨다.
    _metric_task: asyncio.Task = None
    _gpu_monitor = None

    @classmethod
    def get_current_provider(cls) -> str:
        """현재 활성 LLM provider("OLLAMA"/"OPENAI")를 반환한다. 콘솔 AI Pipeline Monitor용."""
        return cls._current_provider.upper()

    @classmethod
    def get_ollama(cls) -> SimpleOllamaClient:
        if cls._ollama is None:
            try:
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                model_name = os.getenv("GEMMA_MODEL", "gemma4:e4b")
                cls._ollama = SimpleOllamaClient(model_name=model_name, base_url=base_url)
            except ImportError as e:
                sys.stderr.write(
                    f"[ERROR] ollama 패키지 미설치: {e!s}. "
                    f"시연 환경에서는 LLM_PROVIDER=gemini(openai)를 사용하세요.\n"
                )
                raise
        return cls._ollama

    @classmethod
    def get_openai(cls) -> SimpleOpenAIClient:
        if cls._openai is None:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
            cls._openai = SimpleOpenAIClient(model_name="gpt-4o-mini", api_key=api_key)
        return cls._openai

    @classmethod
    def get_gemini(cls) -> SimpleGeminiClient:
        if cls._gemini is None:
            api_key = os.getenv("GOOGLE_API_KEY", "")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
            cls._gemini = SimpleGeminiClient(model_name=model_name, api_key=api_key)
        return cls._gemini

    @classmethod
    def start_gpu_monitor(cls, interval_seconds: float = 2.0):
        """
        백그라운드에서 GPU 상태를 감시하여 임계치 돌파 시 openai로 자동 핫스왑하도록 설정합니다.
        (아웃오브밴드 비동기 루프)
        """
        from server.mcp.gpu_monitor import GPUMonitorMCP

        if cls._gpu_monitor is None:
            cls._gpu_monitor = GPUMonitorMCP()

        # 기본 provider를 환경변수에서 설정 (시연/운영 기본 gemini)
        cls._current_provider = os.getenv("LLM_PROVIDER", "gemini").lower()

        async def _publish_metric_safe(payload: dict):
            """메트릭 발행을 best-effort로 수행한다. Redis 지연/부재/인증 실패가 핫스왑 판정
            루프의 주기를 막지 않도록(복귀 지연 방지) 별도 태스크로 돌리고 예외는 삼킨다."""
            try:
                from server.mcp.manager import mcp_manager

                await mcp_manager.publish_metric("system_metrics", payload)
            except Exception as e:
                logger.debug(f"[MCP HOTSWAP] system_metrics 발행 실패(무시): {e!s}")

        async def _monitor_loop():
            while True:
                try:
                    status = await cls._gpu_monitor.get_gpu_status()
                    should_fallback = status.get("should_fallback", False)
                    # 1) 핫스왑 판정: I/O 없이 매 주기 즉시 수행한다.
                    if should_fallback and cls._current_provider == "ollama":
                        cls._current_provider = "openai"
                        logger.warning(
                            "[MCP HOTSWAP] GPU 부하 임계치 도달로 인해 OpenAI(gpt-4o-mini)로 핫스왑을 수행합니다."
                        )
                    elif not should_fallback and cls._current_provider == "openai":
                        # 리소스 정상 복구 시 환경변수 기본 provider로 복귀
                        default_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
                        if default_provider in ("ollama", "gemini"):
                            cls._current_provider = default_provider
                            logger.info(
                                f"[MCP HOTSWAP] GPU 부하 정상 복구로 인해 {default_provider}로 복귀합니다."
                            )

                    # 2) 관제 콘솔용 메트릭 발행은 루프 주기를 막지 않도록 분리한다. 직전 발행이
                    #    아직 진행 중(Redis 지연)이면 이번 주기는 건너뛴다(최신 상태만 중요).
                    if cls._metric_task is None or cls._metric_task.done():
                        cls._metric_task = asyncio.create_task(
                            _publish_metric_safe(
                                {
                                    "gpu_usage_pct": status.get("gpu_usage_pct", 0.0),
                                    "memory_used_mb": status.get("memory_used_mb", 0.0),
                                    "current_provider": cls._current_provider.upper(),
                                    "network_rtt_ms": 12,
                                    "queue_depth": 0,
                                    "dropped_frames": 0,
                                }
                            )
                        )
                except Exception as e:
                    logger.error(f"[MCP HOTSWAP] GPU 모니터 루프 예외 발생: {e!s}")
                await asyncio.sleep(interval_seconds)

        if cls._monitor_task is None or cls._monitor_task.done():
            cls._monitor_task = asyncio.create_task(_monitor_loop())
            logger.info("GPU 모니터 백그라운드 태스크가 성공적으로 시작되었습니다.")

    @classmethod
    def get_client(cls, provider: str | None = None):
        """
        지정된 provider 또는 환경변수 설정을 확인해 적절한 클라이언트를 반환합니다.
        시연/운영 기본은 LLM_PROVIDER 환경변수(gemini 권장). 미설정 시 gemini.
        """
        # start_gpu_monitor가 아직 호출되지 않았다면 환경변수 기준으로 결정한다.
        target = provider or cls._current_provider or os.getenv("LLM_PROVIDER", "gemini")
        target_provider = target.lower()

        if target_provider == "openai":
            try:
                return cls.get_openai()
            except ValueError as e:
                # 시연 기본이 gemini일 때는 OpenAI 키 부재를 Ollama 성공으로 위장하지 않는다.
                default_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
                if default_provider == "gemini":
                    raise
                sys.stderr.write(
                    f"[WARN] OpenAI Client init failed: {e!s}. Falling back to Ollama.\n"
                )
                return cls.get_ollama()
        elif target_provider == "gemini":
            try:
                return cls.get_gemini()
            except ValueError as e:
                sys.stderr.write(
                    f"[WARN] Gemini Client init failed: {e!s}. Falling back to Ollama.\n"
                )
                return cls.get_ollama()
        return cls.get_ollama()
