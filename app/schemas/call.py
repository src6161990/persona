"""원시 통화 데이터 입력 스키마.

페르소나 구축의 입력. 요약본이 아니라 발화 단위의 원시 데이터를 받는다.
본 서비스는 이 데이터를 저장하지 않고 분석에만 사용한다.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Utterance(BaseModel):
    """통화 중 한 번의 발화."""

    speaker: str = Field(description='발화자 (예: "user", "counterpart")')
    text: str = Field(description="발화 내용 (원문)")
    offset_seconds: float | None = Field(default=None, description="통화 시작 기준 발화 시각(초)")


class RawCall(BaseModel):
    """한 통의 원시 통화 기록."""

    call_id: str
    started_at: datetime
    direction: str | None = Field(default=None, description="inbound / outbound")
    counterpart: str | None = Field(default=None, description="통화 상대 (이름 또는 번호)")
    duration_seconds: int | None = None
    utterances: list[Utterance] = Field(default_factory=list, description="발화 단위 트랜스크립트")


class RawAssistantInteraction(BaseModel):
    """통화중 AI 비서 호출 한 건의 원시 상호작용."""

    interaction_id: str
    occurred_at: datetime
    user_utterance: str = Field(description="사용자가 AI 비서에게 한 말 (원문)")
    assistant_response: str = Field(description="AI 비서의 응답 (원문)")
    during_call_id: str | None = Field(default=None, description="어떤 통화 중 호출이었는지")
