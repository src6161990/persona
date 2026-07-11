"""캐릭터 생성 / 멀티턴 수정 오케스트레이션.

캐릭터가 바뀌는 두 지점(생성 · 채팅 수정)에서 캐릭터 이미지를 (재)생성한다.
이미지는 image_store 에 분리 보관하고, 응답 시점에 Character 에 병합해 내보낸다.
"""

import base64
from datetime import datetime, timezone

from app.agents import persona_agent
from app.errors import CharacterNotFound, PersonaNotFound
from app.providers.image_provider import get_image_provider
from app.schemas.character import Character, CharacterChatResponse, CharacterProfile
from app.store.character_store import character_store
from app.store.image_store import image_store
from app.store.persona_store import persona_store


def create_character(user_id: str) -> Character:
    persona = persona_store.get(user_id)
    if persona is None:
        raise PersonaNotFound(user_id)

    prompt = (
        f"[페르소나]\n{persona.model_dump_json(indent=2)}\n\n"
        "이 페르소나를 바탕으로 'AI 대신받기'가 연기할 캐릭터를 구조화 출력으로 생성하라."
    )
    agent = persona_agent.create_character_agent()
    profile: CharacterProfile = persona_agent.invoke_structured(agent, prompt, CharacterProfile)

    character = Character(
        user_id=user_id,
        updated_at=datetime.now(timezone.utc),
        **profile.model_dump(),
    )
    character_store.save(character)
    _generate_and_store_image(user_id, character)  # 생성 시 이미지도 함께
    return _with_image(character)


def get_character(user_id: str) -> Character:
    character = character_store.get(user_id)
    if character is None:
        raise CharacterNotFound(user_id)
    return _with_image(character)


def chat(user_id: str, message: str) -> CharacterChatResponse:
    before = character_store.get(user_id)
    if before is None:
        raise CharacterNotFound(user_id)

    # thread_id 로 멀티턴 대화 상태를 유지 (사용자당 하나의 편집 대화)
    agent = persona_agent.character_chat_agent(user_id)
    config = {"configurable": {"thread_id": f"character-chat:{user_id}"}}
    reply = persona_agent.invoke_text(agent, message, config=config)

    # 에이전트가 save_character 로 갱신했을 수 있으니 다시 읽는다
    after = character_store.get(user_id)

    # 캐릭터가 실제로 바뀌었거나 아직 이미지가 없으면 이미지를 (재)생성한다.
    # (매 턴 무조건 재생성하면 느리고 낭비 — 프로파일 변경이 있을 때만)
    if _profile_fields(before) != _profile_fields(after) or image_store.get(user_id) is None:
        _generate_and_store_image(user_id, after)

    return CharacterChatResponse(reply=reply, character=_with_image(after))


# --- 이미지 (재)생성 / 병합 ---

def _character_image_prompt(character: Character) -> str:
    """캐릭터 프로파일에서 이미지 생성 프롬프트를 만든다 (투명 배경, 캐릭터만)."""
    return (
        "A friendly upper-body avatar portrait of an AI phone-answering persona "
        f"named '{character.name}'. Personality and tone: {character.tone}. {character.summary}. "
        "Flat modern vector illustration, centered, facing forward, "
        "transparent background, no background, subject only, PNG with alpha channel."
    )


def _generate_and_store_image(user_id: str, character: Character) -> None:
    """이미지를 생성해 data URI 로 저장한다.

    이미지 생성 실패가 캐릭터 생성/수정 자체를 깨뜨리지 않도록 비치명적으로 처리한다
    (프로바이더 미배선/일시 오류 시에도 프로파일 흐름은 성공). 실패 시 이미지는 없음(null).
    """
    try:
        png = get_image_provider().generate(_character_image_prompt(character))
        image_store.save(user_id, "data:image/png;base64," + base64.b64encode(png).decode("ascii"))
    except Exception:  # noqa: BLE001 - 이미지 실패는 비치명적, 프로파일 흐름 보호
        pass


def _with_image(character: Character) -> Character:
    """저장된 이미지(data URI)를 Character 에 병합해 반환한다 (없으면 원본)."""
    data_uri = image_store.get(character.user_id)
    return character.model_copy(update={"image": data_uri}) if data_uri else character


def _profile_fields(character: Character) -> dict:
    """이미지 재생성 판단용 — 프로파일 내용만(메타데이터·이미지 제외) 추출."""
    return character.model_dump(exclude={"user_id", "updated_at", "image"})