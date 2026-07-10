"""캐릭터 생성 / 멀티턴 수정 오케스트레이션."""

from datetime import datetime, timezone

from app.agents import persona_agent
from app.errors import CharacterNotFound, PersonaNotFound
from app.schemas.character import Character, CharacterChatResponse, CharacterProfile
from app.store.character_store import character_store
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
    return character


def get_character(user_id: str) -> Character:
    character = character_store.get(user_id)
    if character is None:
        raise CharacterNotFound(user_id)
    return character


def chat(user_id: str, message: str) -> CharacterChatResponse:
    if character_store.get(user_id) is None:
        raise CharacterNotFound(user_id)

    # thread_id 로 멀티턴 대화 상태를 유지 (사용자당 하나의 편집 대화)
    agent = persona_agent.character_chat_agent(user_id)
    config = {"configurable": {"thread_id": f"character-chat:{user_id}"}}
    reply = persona_agent.invoke_text(agent, message, config=config)

    # 에이전트가 save_character 로 갱신했을 수 있으니 다시 읽는다
    character = character_store.get(user_id)
    return CharacterChatResponse(reply=reply, character=character)
