"""LLM 프로바이더 인터페이스 (격리 계층).

비즈니스 로직·에이전트는 구체 프로바이더(Anthropic/OpenAI/…)에 직접 의존하지 않고
이 인터페이스로만 모델을 얻는다. 경계 타입은 LangChain ``BaseChatModel`` 이며,
deepagents 가 이 타입을 그대로 사용한다.

프로바이더 교체는 설정(PERSONA_MODEL_PROVIDER / PERSONA_MODEL_NAME)만으로 이뤄진다.
LangChain 통합 패키지가 설치돼 있어야 하며(anthropic 은 기본 포함,
openai 는 `uv sync --extra openai`), 완전 커스텀 백엔드가 필요하면
``ModelProvider`` 를 구현해 ``BaseChatModel`` 을 반환하도록 감싸면 된다.
"""

import os
from functools import lru_cache
from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings

# 프로바이더별 필수 환경변수 (선언적 표 — 로직에 프로바이더를 박지 않는다).
# 새 프로바이더는 여기에 한 줄만 추가하면 되고, 표에 없는 프로바이더는 검증을 건너뛴다
# (langchain 이 지원하는 어떤 프로바이더로도 .env 만 바꿔 교체 가능하도록).
PROVIDER_REQUIRED_ENV: dict[str, list[str]] = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "azure_openai": ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "OPENAI_API_VERSION"],
    "databricks": ["DATABRICKS_WORKSPACE_URL", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET"],
}


def _validate_provider_env(provider: str) -> None:
    """선택된 프로바이더의 필수 환경변수가 있는지 시작 시점에 확인(fail-fast)."""
    required = PROVIDER_REQUIRED_ENV.get(provider)
    if not required:  # 미등록 프로바이더는 검증 생략 (자유 교체 보장)
        return
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError(
            f"프로바이더 '{provider}' 실행에 필요한 환경변수가 없습니다: {', '.join(missing)}. "
            ".env 를 확인하세요."
        )


class ModelProvider(Protocol):
    """에이전트가 사용할 채팅 모델을 제공하는 포트."""

    def get_chat_model(self) -> BaseChatModel: ...


class LangChainModelProvider:
    """LangChain ``init_chat_model`` 기반 다중 프로바이더 구현.

    provider 예: "anthropic", "openai", "google_genai" 등.
    """

    def __init__(self, provider: str, model: str, max_tokens: int) -> None:
        self._provider = provider
        self._model = model
        self._max_tokens = max_tokens

    def get_chat_model(self) -> BaseChatModel:
        from langchain.chat_models import init_chat_model

        return init_chat_model(
            self._model,
            model_provider=self._provider,
            max_tokens=self._max_tokens,
        )


@lru_cache
def get_model_provider() -> ModelProvider:
    """설정에 따라 프로바이더 구현을 반환한다. 여기서만 구체 구현을 고른다.

    (프로바이더 객체는 캐시하되, 토큰이 필요한 Databricks 는 get_chat_model 호출 시점에 발급한다.)
    """
    settings = get_settings()
    _validate_provider_env(settings.model_provider)

    if settings.model_provider == "databricks":
        from app.providers.databricks import DatabricksModelProvider

        return DatabricksModelProvider(
            model=settings.model_name,
            max_tokens=settings.max_tokens,
            workspace_url=settings.databricks_workspace_url,
            client_id=settings.databricks_client_id,
            client_secret=settings.databricks_client_secret,
        )

    return LangChainModelProvider(
        provider=settings.model_provider,
        model=settings.model_name,
        max_tokens=settings.max_tokens,
    )
