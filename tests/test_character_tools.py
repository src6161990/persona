"""캐릭터 Tool 자체의 스키마, 사용자 바인딩, 성공/실패 계약 단위 테스트.

Python 학습 메모:
- ``test_``로 시작하는 함수는 pytest가 자동으로 찾아 실행한다.
- ``assert 조건``은 조건이 거짓이면 테스트를 실패시킨다.
- 테스트는 한 가지 동작만 검증하고, 서로 영향을 주지 않도록 저장소를 매번 비운다.
"""

import json
from datetime import datetime, timezone

import pytest

from app.agents.tools import make_character_tools
from app.schemas.character import Character
from app.store.character_store import character_store


# 딕셔너리(dict): ``키: 값`` 쌍을 묶는 자료형. 테스트에서 재사용할 입력 데이터다.
PROFILE = {
    "name": "밝은 비서",
    "tone": "밝고 정중함",
    "speaking_style": "짧고 친근하게 말함",
    "do": ["존댓말 사용"],
    "dont": ["약속을 확정하지 않기"],
    "catchphrases": ["확인해볼게요"],
    "greeting": "안녕하세요! 대신 전화받았습니다.",
    "summary": "밝고 신뢰감 있는 대리 응대 캐릭터",
}


def _tools(user_id: str):
    """user_id에 묶인 Tool 목록을 ``{도구 이름: Tool 객체}`` 딕셔너리로 바꾼다.

    ``{tool.name: tool for tool in ...}``는 *dict comprehension*이다.
    반복하면서 ``tool.name``을 키로, ``tool``을 값으로 넣는다.
    """
    return {tool.name: tool for tool in make_character_tools(user_id)}


def _character(user_id: str, name: str) -> Character:
    """테스트용 Character 객체를 만든다.

    ``-> Character``는 반환 타입 힌트다. Python 실행을 강제하지는 않지만,
    사람·IDE·타입 검사기가 이 함수의 결과를 이해하는 데 도움을 준다.
    ``**{**PROFILE, "name": name}``은 딕셔너리 복사 뒤 name만 덮어쓰는 문법이다.
    """
    return Character(
        user_id=user_id,
        updated_at=datetime.now(timezone.utc),
        **{**PROFILE, "name": name},
    )


@pytest.fixture(autouse=True)
def _clear_store():
    """각 테스트 전후에 공유 인메모리 저장소를 비우는 pytest fixture.

    ``yield`` 앞은 테스트 시작 전(setup), 뒤는 테스트가 끝난 뒤(teardown)에 실행된다.
    ``autouse=True``라 테스트 함수가 이 fixture 이름을 인자로 받지 않아도 자동 적용된다.
    """
    character_store._data.clear()  # type: ignore[attr-defined]
    yield
    character_store._data.clear()  # type: ignore[attr-defined]


def test_save_character_exposes_structured_profile_schema():
    """문자열 인자 대신 profile 객체 스키마가 Tool에 공개되는지 확인한다."""
    schema = _tools("u1")["save_character"].args_schema.model_json_schema()

    assert "character_json" not in schema["properties"]
    assert schema["properties"]["profile"]["$ref"].endswith("/CharacterProfile")
    assert "greeting" in schema["$defs"]["CharacterProfile"]["required"]


def test_tools_are_bound_to_factory_user_id():
    """u1용 Tool이 호출돼도 u2 데이터를 읽지 않는지 확인한다."""
    character_store.save(_character("u1", "사용자 1 캐릭터"))
    character_store.save(_character("u2", "사용자 2 캐릭터"))

    result = json.loads(_tools("u1")["get_current_character"].invoke({}))

    assert result["status"] == "success"
    assert result["code"] == "character_found"
    assert result["data"]["user_id"] == "u1"
    assert result["data"]["name"] == "사용자 1 캐릭터"


def test_save_character_returns_success_contract_and_persists():
    """성공 결과 계약과 실제 저장 상태를 둘 다 확인한다."""
    result = json.loads(_tools("u1")["save_character"].invoke({"profile": PROFILE}))

    assert result["status"] == "success"
    assert result["code"] == "character_saved"
    assert result["data"]["user_id"] == "u1"
    assert character_store.get("u1").greeting == PROFILE["greeting"]


def test_save_character_returns_validation_failure_contract_without_persisting():
    # ``{**PROFILE}``은 PROFILE을 복사한다. 원본 PROFILE을 바꾸지 않기 위해 사용한다.
    invalid_profile = {**PROFILE}
    # ``pop``은 키를 꺼내면서 딕셔너리에서 삭제한다. 필수 필드 누락 상황을 만든다.
    invalid_profile.pop("greeting")

    result = json.loads(
        _tools("u1")["save_character"].invoke({"profile": invalid_profile})
    )

    assert result["status"] == "error"
    assert result["code"] == "invalid_arguments"
    assert "profile.greeting" in result["message"]
    assert character_store.get("u1") is None


def test_save_character_returns_execution_failure_without_internal_details(monkeypatch):
    """저장소 예외가 내부 비밀을 노출하지 않는 Tool 결과로 바뀌는지 확인한다."""

    def fail_save(character):
        # 함수 안에 함수를 정의한 예. 아래 monkeypatch가 이 함수로 기존 save를 교체한다.
        raise RuntimeError("database password leaked in exception")

    # monkeypatch는 이 테스트가 끝나면 원래 메서드를 자동 복원한다.
    monkeypatch.setattr(character_store, "save", fail_save)

    result = json.loads(_tools("u1")["save_character"].invoke({"profile": PROFILE}))

    assert result["status"] == "error"
    assert result["code"] == "character_save_failed"
    assert "password" not in result["message"]


def test_get_current_character_returns_execution_failure_contract(monkeypatch):
    """조회 Tool도 같은 실패 계약을 지키는지 확인한다."""
    def fail_get(user_id):
        raise RuntimeError("database password leaked in exception")

    monkeypatch.setattr(character_store, "get", fail_get)

    result = json.loads(_tools("u1")["get_current_character"].invoke({}))

    assert result["status"] == "error"
    assert result["code"] == "character_lookup_failed"
    assert "password" not in result["message"]
