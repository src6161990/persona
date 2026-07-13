"""에이전트 호출·스트리밍·출력 파싱 헬퍼.

factory 가 만든 에이전트(또는 채팅 모델)를 '실행'하는 책임만 진다.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any, TypeVar

from pydantic import BaseModel

from app.agents.factory import build_model

T = TypeVar("T", bound=BaseModel)


# --- 대신받기(실시간 턴) 스트리밍 ---

def stream_reply(
    system_prompt: str, history: list[tuple[str, str]], utterance: str
) -> Iterator[str]:
    """대신받기 한 턴을 토큰 단위로 스트리밍한다.

    지연을 줄이기 위해 deep agent 를 쓰지 않고 채팅 모델을 직접 스트리밍한다
    (단일 응답 한 번에 멀티 서브에이전트 오케스트레이션은 과함).
    상대방 발화 = Human, 페르소나 응답 = AI 로 매핑해 멀티턴 문맥을 구성한다.
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    messages: list[Any] = [SystemMessage(content=system_prompt)]
    for role, text in history:
        messages.append(
            HumanMessage(content=text) if role == "counterpart" else AIMessage(content=text)
        )
    if utterance:
        messages.append(HumanMessage(content=utterance))

    for chunk in build_model().stream(messages):
        text = _message_text(chunk.content)
        if text:
            yield text


# --- 호출 헬퍼 ---

def invoke_text(agent, prompt: str, config: dict | None = None) -> str:
    """에이전트를 호출하고 마지막 메시지 텍스트를 반환한다."""
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]}, config=config)
    messages = result.get("messages", [])
    if not messages:
        return ""
    return _message_text(messages[-1].content)


def invoke_structured(agent, prompt: str, model_cls: type[T], config: dict | None = None) -> T:
    """response_format 을 쓰는 에이전트를 호출해 구조화 출력을 반환한다.

    deepagents/langchain 버전에 따라 구조화 출력의 상태 키가 다를 수 있어
    'structured_response' 를 우선 시도하고, 없으면 마지막 메시지의 JSON 을 파싱한다.
    """
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]}, config=config)

    structured = result.get("structured_response")
    if structured is not None:
        if isinstance(structured, model_cls):
            return structured
        return model_cls.model_validate(structured)

    # 폴백: 마지막 메시지 텍스트에서 JSON 추출
    text = _message_text(result.get("messages", [])[-1].content) if result.get("messages") else ""
    return model_cls.model_validate(_extract_json(text))


# --- 내부 파싱 유틸 ---

def _message_text(content: Any) -> str:
    """AIMessage.content(문자열 또는 블록 리스트)를 순수 텍스트로 정규화한다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content)


def _extract_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise