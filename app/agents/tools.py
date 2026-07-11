"""캐릭터 챗 에이전트용 커스텀 툴.

멀티턴으로 캐릭터를 수정할 때 에이전트가 사용한다. user_id 를 클로저로 바인딩해
에이전트가 대상 사용자를 혼동하지 않게 한다.
"""

from datetime import datetime, timezone
from typing import Any, Literal

from langchain_core.tools import BaseTool, ToolException, tool
from pydantic import BaseModel, Field, ValidationError

from app.schemas.character import Character, CharacterProfile
from app.store.character_store import character_store
from app.store.persona_store import persona_store


class CharacterToolResult(BaseModel):
    """캐릭터 Tool 공통 결과 계약 — 모델이 성공/실패를 안정적으로 구분한다."""

    status: Literal["success", "error"]
    code: str
    message: str
    data: dict[str, Any] | None = None


class SaveCharacterInput(BaseModel):
    """문자열 JSON 대신 Tool 스키마에 직접 노출하는 구조화 입력."""

    profile: CharacterProfile = Field(description="저장할 캐릭터 전체 프로파일")


def _result(
    status: Literal["success", "error"],
    code: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> str:
    return CharacterToolResult(
        status=status,
        code=code,
        message=message,
        data=data,
    ).model_dump_json()


def _validation_error(exc: ValidationError) -> str:
    """잘못된 모델 인자를 재시도 가능한 Tool 결과로 변환한다."""
    fields = sorted({".".join(str(part) for part in error["loc"]) for error in exc.errors()})
    return _result(
        "error",
        "invalid_arguments",
        f"Tool 입력 스키마가 올바르지 않습니다. 확인할 필드: {', '.join(fields)}",
    )


def _execution_error(exc: ToolException) -> str:
    """내부 예외 상세를 노출하지 않고 안정적인 실패 코드만 모델에 반환한다."""
    code = str(exc) or "tool_execution_failed"
    return _result("error", code, "캐릭터 저장 중 오류가 발생했습니다. 저장하지 않았습니다.")


def make_character_tools(user_id: str) -> list[BaseTool]:
    """지정한 user_id 에 바인딩된 캐릭터 편집 툴 3종을 만든다."""

    @tool
    def get_persona() -> str:
        """이 사용자의 페르소나를 공통 Tool 결과 JSON 으로 반환한다."""
        try:
            persona = persona_store.get(user_id)
        except Exception as exc:
            raise ToolException("persona_lookup_failed") from exc
        if persona is None:
            return _result("error", "persona_not_found", "페르소나가 없습니다.")
        return _result(
            "success", "persona_found", "페르소나를 조회했습니다.", persona.model_dump()
        )

    @tool
    def get_current_character() -> str:
        """현재 캐릭터를 공통 Tool 결과 JSON 으로 반환한다."""
        try:
            character = character_store.get(user_id)
        except Exception as exc:
            raise ToolException("character_lookup_failed") from exc
        if character is None:
            return _result("error", "character_not_found", "캐릭터가 없습니다.")
        return _result(
            "success", "character_found", "캐릭터를 조회했습니다.", character.model_dump()
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
            raise ToolException("character_save_failed") from exc
        return _result(
            "success", "character_saved", "캐릭터를 저장했습니다.", character.model_dump()
        )

    # Pydantic 입력 오류와 실행 오류를 예외로 graph 밖까지 전파하지 않고 ToolMessage 로 돌려준다.
    # 모델은 status/code 를 보고 인자를 고쳐 재시도하거나 사용자에게 실패를 설명할 수 있다.
    get_persona.handle_tool_error = _execution_error
    get_current_character.handle_tool_error = _execution_error
    save_character.handle_validation_error = _validation_error
    save_character.handle_tool_error = _execution_error

    return [get_persona, get_current_character, save_character]
