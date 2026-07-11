"""LLM이 캐릭터 Tool을 호출할 때 주고받는 입력·출력 계약.

도메인 데이터(CharacterProfile)는 ``schemas/character.py``에, Tool 호출용 포장 형식은
이 파일에 둔다. 이렇게 하면 Tool 함수는 실행 로직에만 집중할 수 있다.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.character import CharacterProfile


class CharacterToolResult(BaseModel):
    """캐릭터 Tool 공통 결과 계약 — 모델이 성공/실패를 안정적으로 구분한다."""

    status: Literal["success", "error"]
    code: str
    message: str
    data: dict[str, Any] | None = None


class SaveCharacterInput(BaseModel):
    """문자열 JSON 대신 Tool 스키마에 직접 노출하는 구조화 입력."""

    profile: CharacterProfile = Field(description="저장할 캐릭터 전체 프로파일")
