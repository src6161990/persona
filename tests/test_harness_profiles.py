"""Harness Profile이 도메인 Persona와 별개로 정확한 모델 키에 등록되는지 검증한다."""

from types import SimpleNamespace

from app.agents import harness_profiles
from app.agents.harness_profiles import (
    _CLAUDE_TOOL_GUIDANCE,
    databricks_harness_profile_key,
    persona_harness_profile,
)


def test_databricks_profile_uses_the_openai_transport_key():
    """Databricks endpoint를 감싼 ChatOpenAI의 Deep Agents 식별 키를 고정한다."""
    assert (
        databricks_harness_profile_key("databricks-claude-opus-4-6")
        == "openai:databricks-claude-opus-4-6"
    )


def test_persona_harness_profile_keeps_tool_result_guidance_and_disables_default_subagent():
    """Profile 정책 자체는 네트워크나 실제 LLM 호출 없이 확인할 수 있다."""
    profile = persona_harness_profile()

    assert profile.system_prompt_suffix == _CLAUDE_TOOL_GUIDANCE
    assert profile.general_purpose_subagent is not None
    assert profile.general_purpose_subagent.enabled is False


def test_databricks_settings_register_the_profile_for_the_resolved_transport_key(monkeypatch):
    """설정값은 databricks지만 Deep Agents 등록 키는 openai transport임을 검증한다."""
    registered: dict[str, object] = {}
    monkeypatch.setattr(
        harness_profiles,
        "get_settings",
        lambda: SimpleNamespace(
            model_provider="databricks",
            model_name="databricks-claude-opus-4-6",
        ),
    )
    monkeypatch.setattr(
        harness_profiles,
        "register_harness_profile",
        lambda key, profile: registered.update(key=key, profile=profile),
    )

    # lru_cache는 프로세스에서 한 번 등록한 결과를 기억하므로, 독립 테스트를 위해 비운다.
    harness_profiles.register_persona_harness_profile.cache_clear()
    harness_profiles.register_persona_harness_profile()

    assert registered["key"] == "openai:databricks-claude-opus-4-6"
    assert registered["profile"].general_purpose_subagent.enabled is False
    harness_profiles.register_persona_harness_profile.cache_clear()
