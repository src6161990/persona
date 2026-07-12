"""캐릭터 챗 에이전트용 커스텀 툴.

멀티턴으로 캐릭터를 수정할 때 에이전트가 사용한다. user_id 를 클로저로 바인딩해
에이전트가 대상 사용자를 혼동하지 않게 한다.
"""

from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import BaseTool, ToolException, tool
from pydantic import ValidationError

from app.schemas.character import Character, CharacterProfile
from app.schemas.tool import (
    CharacterToolCode,
    CharacterToolResult,
    SaveCharacterInput,
    ToolResultStatus,
    character_tool_message,
)
from app.store.character_store import character_store
from app.store.persona_store import persona_store


def _result(
    status: ToolResultStatus,
    code: CharacterToolCode,
    data: dict[str, Any] | None = None,
    detail: str | None = None,
) -> str:
    return CharacterToolResult(
        status=status,
        code=code,
        message=character_tool_message(code, detail),
        data=data,
    ).model_dump_json()


def _success_result(code: CharacterToolCode, data: dict[str, Any] | None = None) -> str:
    """공통 성공 envelope를 만든다."""
    return _result(ToolResultStatus.SUCCESS, code, data=data)


def _error_result(code: CharacterToolCode, detail: str | None = None) -> str:
    """공통 오류 envelope를 만든다."""
    return _result(ToolResultStatus.ERROR, code, detail=detail)


class CharacterToolError(ToolException):
    """예외가 발생해도 Tool 결과 코드가 문자열에 의존하지 않도록 하는 전용 예외."""

    def __init__(self, code: CharacterToolCode) -> None:
        self.code = code
        super().__init__(code.value)


def _validation_error(exc: ValidationError) -> str:
    """잘못된 모델 인자를 재시도 가능한 Tool 결과로 변환한다."""
    fields = sorted({".".join(str(part) for part in error["loc"]) for error in exc.errors()})
    return _error_result(
        CharacterToolCode.INVALID_ARGUMENTS,
        f"확인할 필드: {', '.join(fields)}",
    )


def _execution_error(exc: ToolException) -> str:
    """내부 예외 상세를 노출하지 않고 안정적인 실패 코드만 모델에 반환한다."""
    code = exc.code if isinstance(exc, CharacterToolError) else CharacterToolCode.UNEXPECTED_ERROR
    return _error_result(code)


def make_character_tools(user_id: str) -> list[BaseTool]:
    """지정한 user_id 에 바인딩된 캐릭터 편집 툴 3종을 만든다."""

    @tool
    def get_persona() -> str:
        """이 사용자의 페르소나를 공통 Tool 결과 JSON 으로 반환한다."""
        try:
            persona = persona_store.get(user_id)
        except Exception as exc:
            raise CharacterToolError(CharacterToolCode.STORAGE_UNAVAILABLE) from exc
        if persona is None:
            return _error_result(CharacterToolCode.PERSONA_NOT_FOUND)
        return _success_result(
            CharacterToolCode.PERSONA_FOUND,
            persona.model_dump(),
        )

    @tool
    def get_current_character() -> str:
        """현재 캐릭터를 공통 Tool 결과 JSON 으로 반환한다."""
        try:
            character = character_store.get(user_id)
        except Exception as exc:
            raise CharacterToolError(CharacterToolCode.STORAGE_UNAVAILABLE) from exc
        if character is None:
            return _error_result(CharacterToolCode.CHARACTER_NOT_FOUND)
        return _success_result(
            CharacterToolCode.CHARACTER_FOUND,
            character.model_dump(),
        )

    @tool(args_schema=SaveCharacterInput)
    def save_character(profile: CharacterProfile) -> str:
        """구조화된 CharacterProfile 전체를 이 사용자의 캐릭터로 저장한다."""
        character = Character(
            user_id=user_id,
            updated_at=datetime.now(timezone.utc),
            **profile.model_dump(),
        )
        try:
            character_store.save(character)
        except Exception as exc:
            raise CharacterToolError(CharacterToolCode.STORAGE_UNAVAILABLE) from exc
        return _success_result(
            CharacterToolCode.CHARACTER_SAVED,
            character.model_dump(),
        )

    # Pydantic 입력 오류와 실행 오류를 예외로 graph 밖까지 전파하지 않고 ToolMessage 로 돌려준다.
    # 모델은 status/code 를 보고 인자를 고쳐 재시도하거나 사용자에게 실패를 설명할 수 있다.
    get_persona.handle_tool_error = _execution_error
    get_current_character.handle_tool_error = _execution_error
    save_character.handle_validation_error = _validation_error
    save_character.handle_tool_error = _execution_error

    return [get_persona, get_current_character, save_character]
