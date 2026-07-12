"""LLM이 캐릭터 Tool을 호출할 때 주고받는 입력·출력 계약.

도메인 데이터(CharacterProfile)는 ``schemas/character.py``에, Tool 호출용 포장 형식은
이 파일에 둔다. 이렇게 하면 Tool 함수는 실행 로직에만 집중할 수 있다.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.character import CharacterProfile


class ToolResultStatus(str, Enum):
    """Tool 실행의 최상위 결과 상태."""

    SUCCESS = "success"
    ERROR = "error"


class CharacterToolCode(str, Enum):
    """캐릭터 Tool이 반환할 수 있는 도메인 결과 코드 목록.

    status(success/error)는 공통 Tool envelope의 책임이며 이 Enum은
    "어떤 일이 일어났는지"만 표현한다.
    """

    PERSONA_FOUND = "persona_found"
    PERSONA_NOT_FOUND = "persona_not_found"

    CHARACTER_FOUND = "character_found"
    CHARACTER_NOT_FOUND = "character_not_found"
    CHARACTER_SAVED = "character_saved"

    INVALID_ARGUMENTS = "invalid_arguments"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    UNEXPECTED_ERROR = "unexpected_error"


# 코드와 기본 메시지를 한 곳에서 관리한다. 입력 필드 목록처럼 동적으로 달라지는 내용은
# character_tool_message(..., detail=...)로 뒤에 덧붙인다.
CHARACTER_TOOL_DEFAULT_MESSAGES: dict[CharacterToolCode, str] = {
    CharacterToolCode.PERSONA_FOUND: "페르소나를 조회했습니다.",
    CharacterToolCode.PERSONA_NOT_FOUND: "페르소나가 없습니다.",
    CharacterToolCode.CHARACTER_FOUND: "캐릭터를 조회했습니다.",
    CharacterToolCode.CHARACTER_NOT_FOUND: "캐릭터가 없습니다.",
    CharacterToolCode.CHARACTER_SAVED: "캐릭터를 저장했습니다.",
    CharacterToolCode.INVALID_ARGUMENTS: "Tool 입력 형식이 올바르지 않습니다.",
    CharacterToolCode.STORAGE_UNAVAILABLE: "저장소에 일시적으로 접근할 수 없습니다.",
    CharacterToolCode.UNEXPECTED_ERROR: "예상하지 못한 Tool 오류가 발생했습니다.",
}


def character_tool_message(code: CharacterToolCode, detail: str | None = None) -> str:
    """결과 코드의 기본 메시지와 선택적 실행 상세를 결합한다."""
    message = CHARACTER_TOOL_DEFAULT_MESSAGES[code]
    return f"{message} {detail}" if detail else message


class CharacterToolResult(BaseModel):
    """캐릭터 Tool 공통 결과 계약 — 모델이 성공/실패를 안정적으로 구분한다."""

    status: ToolResultStatus
    code: CharacterToolCode
    message: str
    data: dict[str, Any] | None = None


class SaveCharacterInput(BaseModel):
    """문자열 JSON 대신 Tool 스키마에 직접 노출하는 구조화 입력."""

    profile: CharacterProfile = Field(description="저장할 캐릭터 전체 프로파일")
