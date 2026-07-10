"""캐릭터 챗 에이전트용 커스텀 툴.

멀티턴으로 캐릭터를 수정할 때 에이전트가 사용한다. user_id 를 클로저로 바인딩해
에이전트가 대상 사용자를 혼동하지 않게 한다.
"""

import json
from datetime import datetime, timezone

from langchain_core.tools import BaseTool, tool

from app.schemas.character import Character, CharacterProfile
from app.store.character_store import character_store
from app.store.persona_store import persona_store


def make_character_tools(user_id: str) -> list[BaseTool]:
    """지정한 user_id 에 바인딩된 캐릭터 편집 툴 3종을 만든다."""

    @tool
    def get_persona() -> str:
        """이 사용자의 페르소나(분석 프로파일)를 JSON 으로 반환한다."""
        persona = persona_store.get(user_id)
        if persona is None:
            return "페르소나 없음"
        return persona.model_dump_json()

    @tool
    def get_current_character() -> str:
        """현재 저장된 이 사용자의 캐릭터를 JSON 으로 반환한다."""
        character = character_store.get(user_id)
        if character is None:
            return "캐릭터 없음"
        return character.model_dump_json()

    @tool
    def save_character(character_json: str) -> str:
        """수정한 캐릭터를 저장한다.

        character_json 은 CharacterProfile 스키마를 따르는 JSON 문자열이어야 한다
        (name, tone, speaking_style, do[], dont[], catchphrases[], greeting, summary).
        """
        data = json.loads(character_json)
        profile = CharacterProfile.model_validate(data)
        character = Character(
            user_id=user_id,
            updated_at=datetime.now(timezone.utc),
            **profile.model_dump(),
        )
        character_store.save(character)
        return "저장 완료"

    return [get_persona, get_current_character, save_character]
