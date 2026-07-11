"""가짜 채팅 모델로 Deep Agent의 model→tool→model 루프를 검증한다.

Python 학습 메모:
- 외부 API 대신 가짜 객체를 써서 테스트를 빠르고 결정적으로 만든다.
- 클래스 상속과 메서드 재정의로 기존 Fake 모델에 Tool 호출 능력만 추가한다.
"""

import json

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import Field

from app.agents.tools import make_character_tools
from app.store.character_store import character_store
from deepagents import create_deep_agent


UPDATED_PROFILE = {
    "name": "밝은 비서",
    "tone": "밝고 정중함",
    "speaking_style": "짧고 친근하게 말함",
    "do": ["존댓말 사용"],
    "dont": ["약속을 확정하지 않기"],
    "catchphrases": ["확인해볼게요"],
    "greeting": "안녕하세요! 대신 전화받았습니다.",
    "summary": "밝고 신뢰감 있는 대리 응대 캐릭터",
}


class ToolCallingFakeModel(GenericFakeChatModel):
    """스크립트된 tool_calls를 반환하고 Deep Agent의 bind_tools를 수용한다.

    ``class 자식(부모)``는 상속이다. GenericFakeChatModel 기능을 물려받고,
    여기서는 ``bind_tools``만 우리 테스트 목적에 맞게 새로 정의(override)한다.
    """

    # Field(default_factory=list): 인스턴스마다 새로운 빈 리스트를 만든다.
    # ``[]``를 기본값으로 공유하는 실수를 피하는 Pydantic 방식이다.
    bound_tool_names: list[str] = Field(default_factory=list)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        """Deep Agent가 Tool을 모델에 연결할 때 호출하는 메서드.

        ``*`` 뒤 인자는 키워드로만 전달한다.
        ``**kwargs``는 우리가 쓰지 않는 추가 키워드 인자를 모두 받아 호환성을 유지한다.
        """
        # 조건 표현식 ``A if 조건 else B``: Tool 객체면 name 속성을, dict면 name 키를 사용한다.
        # list comprehension은 모든 Tool의 이름을 새 리스트로 만든다.
        self.bound_tool_names = [
            tool.name if hasattr(tool, "name") else tool.get("name", "") for tool in tools
        ]
        return self


def test_character_agent_executes_structured_save_tool_and_returns_to_model():
    """스크립트된 Tool 호출이 저장 후 최종 모델 응답으로 이어지는지 검증한다."""

    character_store._data.clear()  # type: ignore[attr-defined]
    model = ToolCallingFakeModel(
        # ``iter([...])``는 목록을 한 번에 하나씩 꺼내는 iterator로 바꾼다.
        # 가짜 모델은 첫 호출에 Tool 요청, 두 번째 호출에 최종 답변을 차례로 반환한다.
        messages=iter(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "save_character",
                            "args": {"profile": UPDATED_PROFILE},
                            "id": "save-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="인사말을 밝게 바꾸고 저장했습니다."),
            ]
        )
    )
    agent = create_deep_agent(
        model=model,
        tools=make_character_tools("u1"),
        system_prompt="요청에 맞게 캐릭터를 수정하고 save_character로 저장하라.",
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "인사말을 더 밝게 바꿔줘"}]}
    )

    saved = character_store.get("u1")
    assert saved is not None
    assert saved.greeting == UPDATED_PROFILE["greeting"]
    assert "save_character" in model.bound_tool_names

    # list comprehension + isinstance: 전체 메시지 중 ToolMessage 객체만 골라 새 리스트를 만든다.
    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    tool_result = json.loads(tool_messages[0].content)
    assert tool_messages[0].tool_call_id == "save-1"
    assert tool_result["status"] == "success"
    assert tool_result["code"] == "character_saved"
    assert result["messages"][-1].content == "인사말을 밝게 바꾸고 저장했습니다."
