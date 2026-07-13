"""DeepAgent 팩토리 — 모델/체크포인터 구성과 에이전트 조립.

상태를 들고 있지 않은 조립 로직이라 클래스 대신 모듈 네임스페이스로 노출한다.
에이전트를 '만드는' 책임만 지고, 만들어진 에이전트를 '실행'하는 책임은 runner 에 있다.
"""

from __future__ import annotations

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel

from app.agents import prompts
from app.agents.tools import make_character_tools
from app.providers.model_provider import get_model_provider
from app.schemas.character import CharacterProfile
from app.schemas.persona import PersonaProfile

# 멀티턴 대화 상태 저장용 체크포인터 (버전별 import 경로 차이 방어)
try:  # langgraph 최신
    from langgraph.checkpoint.memory import InMemorySaver as _Saver
except ImportError:  # 구버전 별칭
    from langgraph.checkpoint.memory import MemorySaver as _Saver  # type: ignore

CHECKPOINTER = _Saver()


def build_model() -> BaseChatModel:
    """채팅 모델을 생성한다.

    구체 프로바이더는 provider 계층에서 결정한다 (여기선 벤더에 의존하지 않음).
    매 호출 시 생성 — Databricks 등 만료형 토큰을 재발급하기 위함(모델 생성 자체는 저렴).
    """
    return get_model_provider().get_chat_model()


def build_persona_agent():
    return create_deep_agent(
        model=build_model(),
        system_prompt=prompts.PERSONA_BUILDER_PROMPT,
        response_format=PersonaProfile,
    )


def build_character_agent():
    return create_deep_agent(
        model=build_model(),
        system_prompt=prompts.CHARACTER_CREATE_PROMPT,
        response_format=CharacterProfile,
    )


def build_character_chat_agent(user_id: str):
    return create_deep_agent(
        model=build_model(),
        tools=make_character_tools(user_id),
        system_prompt=prompts.CHARACTER_CHAT_PROMPT,
        checkpointer=CHECKPOINTER,
    )