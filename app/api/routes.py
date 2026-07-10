"""REST 엔드포인트."""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.character import Character, CharacterChatRequest, CharacterChatResponse
from app.schemas.persona import (
    AnswerTurnRequest,
    Persona,
    PersonaBuildRequest,
    PersonaBuildResponse,
)
from app.services import character_service, persona_service

router = APIRouter(prefix="/personas", tags=["persona"])


def _sse(event: str, data: dict) -> str:
    """(event, data) → SSE 프레임 문자열."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# --- 페르소나 ---

@router.post("/{user_id}/build", response_model=PersonaBuildResponse, status_code=201)
def build_persona(user_id: str, request: PersonaBuildRequest) -> PersonaBuildResponse:
    """원시 통화 데이터로 페르소나를 구축·저장한다."""
    persona = persona_service.build_persona(user_id, request)
    return PersonaBuildResponse(persona=persona)


@router.get("/{user_id}", response_model=Persona)
def get_persona(user_id: str) -> Persona:
    """구축된 페르소나를 조회한다."""
    return persona_service.get_persona(user_id)


@router.post("/{user_id}/answer-context")
def answer_context(user_id: str, request: AnswerTurnRequest) -> StreamingResponse:
    """상대방 발화(text)에 대한 'AI 대신받기' 응답을 SSE 로 스트리밍한다.

    STT→text 를 입력받아 text→TTS 로 나갈 응답을 토큰 단위(event: token)로 흘려보내고,
    끝에 전체 응답(event: done)을 준다. call_id 로 통화 전체가 멀티턴으로 이어진다.
    """
    # 검증(페르소나/캐릭터 존재)은 여기서 즉시 수행 → 없으면 스트리밍 전에 404 로 매핑.
    events = persona_service.answer_turn(user_id, request)
    return StreamingResponse(
        (_sse(event, data) for event, data in events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- 캐릭터 ---

@router.post("/{user_id}/character", response_model=Character, status_code=201)
def create_character(user_id: str) -> Character:
    """페르소나를 바탕으로 대신받기 캐릭터를 생성한다."""
    return character_service.create_character(user_id)


@router.get("/{user_id}/character", response_model=Character)
def get_character(user_id: str) -> Character:
    """캐릭터를 조회한다."""
    return character_service.get_character(user_id)


@router.post("/{user_id}/character/chat", response_model=CharacterChatResponse)
def character_chat(user_id: str, request: CharacterChatRequest) -> CharacterChatResponse:
    """멀티턴 채팅으로 캐릭터를 수정한다."""
    return character_service.chat(user_id, request.message)
