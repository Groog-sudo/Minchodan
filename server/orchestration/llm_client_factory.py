# -*- coding: utf-8 -*-
"""
LLMClientFactory 구현 파일.
Ollama 공식 SDK 및 httpx를 사용하여, 외부 langchain_community/langchain_openai 의존성 없이
로컬 Gemma2 및 상용 GPT-4o-mini 모델 간의 비동기 호출 및 핫스왑을 지원합니다.
"""

import os
import sys
import logging
from typing import List

from dotenv import load_dotenv
import httpx
import ollama

# Reconfigure stdout for UTF-8 output formatting support (guide 3.1)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

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
        self.model_name = model_name
        self.base_url = base_url
        # AsyncClient 인스턴스 생성
        self.client = ollama.AsyncClient(host=base_url)

    async def ainvoke(self, messages: List) -> LLMResponse:
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
        response = await self.client.chat(
            model=self.model_name,
            messages=formatted_messages,
            options={"temperature": 0.3, "num_predict": 50}
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

    async def ainvoke(self, messages: List) -> LLMResponse:
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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": 0.3,
            "max_tokens": 50
        }

        logger.info(f"OpenAI API async invocation: model={self.model_name}")
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            res_data = response.json()
            
        content = res_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return LLMResponse(content)


class LLMClientFactory:
    """
    BaseChatModel과 호환되는 클라이언트의 싱글톤 인스턴스를 동적으로 핫스왑 관리하는 팩토리 클래스.
    """
    _ollama: SimpleOllamaClient = None
    _openai: SimpleOpenAIClient = None

    @classmethod
    def get_ollama(cls) -> SimpleOllamaClient:
        if cls._ollama is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = os.getenv("GEMMA_MODEL", "gemma2:9b")
            cls._ollama = SimpleOllamaClient(model_name=model_name, base_url=base_url)
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
    def get_client(cls, provider: str = None):
        """
        지정된 provider 또는 환경변수 설정을 확인해 적절한 클라이언트를 반환합니다.
        """
        target_provider = provider or os.getenv("LLM_PROVIDER", "ollama").lower()
        if target_provider == "openai":
            try:
                return cls.get_openai()
            except ValueError as e:
                sys.stderr.write(f"[WARN] OpenAI Client init failed: {str(e)}. Falling back to Ollama.\n")
                return cls.get_ollama()
        return cls.get_ollama()
