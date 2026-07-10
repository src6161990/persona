"""페르소나 관련 스키마."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.call import RawAssistantInteraction, RawCall


class PersonaProfile(BaseModel):
    """에이전트(LLM)가 원시 통화 데이터를 분석해 생성하는 페르소나 프로파일.

    저장용 메타데이터(user_id, updated_at)는 서버가 부여하므로 여기엔 없다.
    이 스키마가 곧 에이전트의 구조화 출력(response_format) 스펙이 된다.
    """

    speaking_style: str = Field(description="말투·어조·대화 스타일 요약")
    frequent_topics: list[str] = Field(description="자주 다루는 대화 주제")
    key_relationships: list[str] = Field(description="자주 통화하는 상대 및 관계")
    preferences: list[str] = Field(description="드러난 선호/성향")
    decision_patterns: list[str] = Field(description="의사결정·응답 패턴")
    summary: str = Field(description="페르소나 종합 요약")


class Persona(PersonaProfile):
    """저장·조회되는 페르소나 (프로파일 + 메타데이터)."""

    user_id: str
    updated_at: datetime


class PersonaBuildRequest(BaseModel):
    """원시 통화 데이터로 페르소나를 구축하는 요청."""

    calls: list[RawCall] = Field(default_factory=list)
    assistant_events: list[RawAssistantInteraction] = Field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.calls and not self.assistant_events


class PersonaBuildResponse(BaseModel):
    persona: Persona


class AnswerTurnRequest(BaseModel):
    """'AI 대신받기' 한 턴 요청 — 상대방의 발화(STT 결과 text)를 받는다.

    STT/TTS 는 본 서비스 밖이다. 여기서는 text 를 받아 text 로 응답한다.
    통화 전엔 용건을 알 수 없으므로 용건(purpose)을 입력받지 않는다. 용건은 대화가
    진행되며 자연히 드러난다. call_id 로 통화 전체를 하나의 멀티턴 대화로 잇고,
    caller 는 저장된 사용자든 단순 번호든 '알면' 힌트로만 쓴다(없어도 동작).
    """

    call_id: str = Field(description="통화 식별자 = 멀티턴 대화 세션 키")
    utterance: str = Field(
        default="",
        description="상대방(발신자)의 방금 발화(STT 결과 text). 통화 연결 직후 인사 턴이면 빈 값 가능",
    )
    caller: str | None = Field(default=None, description="발신자 (번호 또는 저장된 사용자). 몰라도 됨")
