"""페르소나 구축 / 대신받기 실시간 응답 오케스트레이션."""

from collections.abc import Iterator
from datetime import datetime, timezone

from app.agents import factory, prompts, runner
from app.errors import EmptyBuildInput, PersonaNotFound
from app.schemas.character import Character
from app.schemas.persona import (
    AnswerTurnRequest,
    Persona,
    PersonaBuildRequest,
    PersonaProfile,
)
from app.store.character_store import character_store
from app.store.conversation_store import conversation_store
from app.store.persona_store import persona_store


def build_persona(user_id: str, request: PersonaBuildRequest) -> Persona:
    if request.is_empty():
        raise EmptyBuildInput("통화(calls) 또는 AI 비서 상호작용(assistant_events)이 최소 1건 필요합니다.")

    prompt = (
        f"다음은 user_id={user_id} 의 원시 통화 데이터다.\n\n"
        f"{request.model_dump_json(indent=2)}\n\n"
        "이 데이터를 분석해 사용자의 페르소나를 구조화 출력으로 생성하라."
    )
    agent = factory.build_persona_agent()
    profile: PersonaProfile = runner.invoke_structured(agent, prompt, PersonaProfile)

    persona = Persona(
        user_id=user_id,
        updated_at=datetime.now(timezone.utc),
        **profile.model_dump(),
    )
    persona_store.save(persona)
    return persona


def get_persona(user_id: str) -> Persona:
    persona = persona_store.get(user_id)
    if persona is None:
        raise PersonaNotFound(user_id)
    return persona


def answer_turn(user_id: str, request: AnswerTurnRequest) -> Iterator[tuple[str, dict]]:
    """대신받기 한 턴: 상대방 발화(text) → 페르소나 응답(text) 을 이벤트로 스트리밍한다.

    STT/TTS 는 서비스 밖. 본 함수는 text in → text out 만 담당한다.
    call_id 로 통화 전체를 하나의 멀티턴 대화로 잇는다.

    (검증은 제너레이터를 만들기 '전에' 즉시 수행한다. 스트리밍이 시작된 뒤에는
    헤더가 나간 상태라 예외를 404 로 매핑할 수 없기 때문.)

    이벤트: ("token", {"delta": ...}) 를 여러 번, 마지막에 ("done", {"reply": 전체}).
    """
    # 캐릭터가 있으면 우선 사용, 없으면 페르소나 사용
    character = character_store.get(user_id)
    persona = persona_store.get(user_id)
    if character is None and persona is None:
        raise PersonaNotFound(user_id)

    system_prompt = _answer_system_prompt(character, persona, request.caller)
    history = conversation_store.get(request.call_id)

    def _events() -> Iterator[tuple[str, dict]]:
        parts: list[str] = []
        for delta in runner.stream_reply(system_prompt, history, request.utterance):
            parts.append(delta)
            yield "token", {"delta": delta}
        reply = "".join(parts)

        # 다음 턴이 이어받을 문맥 갱신 (빈 인사 턴이면 상대 발화는 기록하지 않음)
        if request.utterance:
            conversation_store.append(request.call_id, "counterpart", request.utterance)
        conversation_store.append(request.call_id, "assistant", reply)

        yield "done", {"call_id": request.call_id, "reply": reply}

    return _events()


def _answer_system_prompt(
    character: Character | None, persona: Persona | None, caller: str | None
) -> str:
    """대신받기 응답용 시스템 프롬프트 = 규칙 + 캐릭터/페르소나 정의 + 발신자 힌트."""
    if character is not None:
        basis = f"[캐릭터 정의]\n{character.model_dump_json(indent=2)}"
    else:
        basis = f"[사용자 페르소나]\n{persona.model_dump_json(indent=2)}"  # type: ignore[union-attr]
    caller_line = f"발신자: {caller}" if caller else "발신자: 미상 (저장되지 않은 번호일 수 있음)"
    return f"{prompts.ANSWER_TURN_PROMPT}\n\n{basis}\n\n[걸려온 전화]\n{caller_line}"
