"""페르소나 캐릭터 스키마.

캐릭터는 'AI 대신받기'가 실제로 연기할 대화형 인격 정의다.
페르소나(분석 프로파일)를 바탕으로 생성하고, 사용자와의 멀티턴 채팅으로 다듬는다.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CharacterProfile(BaseModel):
    """에이전트가 생성/수정하는 캐릭터 정의 (저장용 메타데이터 제외).

    캐릭터 생성 에이전트의 구조화 출력(response_format) 스펙이자,
    캐릭터 챗 에이전트가 save_character 로 저장하는 페이로드 스펙이다.
    """

    name: str = Field(description="캐릭터 호칭/이름")
    tone: str = Field(description="전반적인 말투·어조")
    speaking_style: str = Field(description="대화 스타일 상세")
    do: list[str] = Field(default_factory=list, description="대신받기 시 지켜야 할 규칙")
    dont: list[str] = Field(default_factory=list, description="하지 말아야 할 것")
    catchphrases: list[str] = Field(default_factory=list, description="자주 쓰는 표현")
    greeting: str = Field(description="전화를 대신 받을 때 첫 인사말")
    summary: str = Field(description="캐릭터 한 줄 요약")


class Character(CharacterProfile):
    """저장·조회되는 캐릭터 (프로파일 + 메타데이터)."""

    user_id: str
    updated_at: datetime
    # 투명 배경 캐릭터 PNG 를 data URI(data:image/png;base64,...)로 실어 나른다.
    # 이미지 바이트는 image_store 에 분리 보관하고, 응답 시점에 병합된다(저장 객체엔 None).
    image: str | None = Field(default=None, description="투명 배경 캐릭터 이미지 (data URI, 없으면 null)")


class CharacterChatRequest(BaseModel):
    """캐릭터를 다듬기 위한 사용자 채팅 메시지 (멀티턴)."""

    message: str = Field(description="캐릭터 수정 요청/피드백")


class CharacterChatResponse(BaseModel):
    reply: str = Field(description="에이전트의 대화체 응답 (무엇을 바꿨는지 등)")
    character: Character = Field(description="현재(갱신된) 캐릭터 상태")
