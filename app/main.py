"""FastAPI 앱 진입점."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.errors import CharacterNotFound, EmptyBuildInput, PersonaNotFound

app = FastAPI(
    title="Persona Service",
    version="0.1.0",
    description="통화 데이터 기반 사용자 페르소나 구축 / 캐릭터 생성·튜닝 / 대신받기 컨텍스트 생성",
)

app.include_router(router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# --- 도메인 예외 → HTTP 매핑 ---

@app.exception_handler(PersonaNotFound)
async def _persona_not_found(request: Request, exc: PersonaNotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": f"페르소나를 찾을 수 없습니다: user_id={exc}"})


@app.exception_handler(CharacterNotFound)
async def _character_not_found(request: Request, exc: CharacterNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": f"캐릭터를 찾을 수 없습니다(먼저 생성 필요): user_id={exc}"},
    )


@app.exception_handler(EmptyBuildInput)
async def _empty_build_input(request: Request, exc: EmptyBuildInput) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})
