"""Persona 서비스가 사용하는 Deep Agents Harness Profile.

``PersonaProfile``(사용자 도메인 데이터)과 달리 ``HarnessProfile``은 특정 모델이
Deep Agent 안에서 Tool·미들웨어·기본 subagent를 어떻게 다룰지를 조정한다.
"""

from __future__ import annotations

from functools import lru_cache

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    register_harness_profile,
)

from app.config import get_settings

# Databricks Serving Endpoint는 OpenAI 호환 ChatOpenAI로 생성된다.
# Deep Agents는 그 모델의 LangSmith 식별값을 ``openai:<endpoint-name>``으로
# 해석하므로, 설정의 ``databricks``가 아니라 이 키로 등록해야 한다.
_DATABRICKS_TRANSPORT_PROVIDER = "openai"

_CLAUDE_TOOL_GUIDANCE = """\
When using tools, follow each tool schema exactly. Do not claim that data was
saved, changed, or retrieved unless the corresponding tool result confirms it.
If a tool returns an error, explain the limitation or choose a safe alternative.
"""


def databricks_harness_profile_key(endpoint_name: str) -> str:
    """Databricks endpoint를 감싼 ChatOpenAI 모델의 실제 Profile 조회 키."""
    return f"{_DATABRICKS_TRANSPORT_PROVIDER}:{endpoint_name}"


def persona_harness_profile() -> HarnessProfile:
    """현재 POC에 필요한 최소 Harness 조정값을 만든다.

    프로젝트는 별도 subagent를 정의하지 않는다. 따라서 Deep Agents가 자동으로
    추가하는 general-purpose subagent와 ``task`` Tool을 끈다. 이는 캐릭터 편집의
    세 Custom Tool과 구조화 Persona 생성 흐름을 바꾸지 않는다.
    """
    return HarnessProfile(
        system_prompt_suffix=_CLAUDE_TOOL_GUIDANCE,
        general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
    )


@lru_cache
def register_persona_harness_profile() -> None:
    """설정된 Databricks 모델에 Persona용 Harness Profile을 한 번 등록한다.

    모델 프로바이더를 Anthropic/OpenAI 등으로 바꾸면 이 함수는 아무것도 등록하지
    않는다. 해당 프로바이더의 내장 또는 별도 Profile 정책을 그대로 사용한다.
    """
    settings = get_settings()
    if settings.model_provider != "databricks":
        return

    register_harness_profile(
        databricks_harness_profile_key(settings.model_name),
        persona_harness_profile(),
    )
