"""페르소나 저장소.

페르소나는 user_id 로 정확 조회되는 사용자당 단일 문서라 인메모리(딕셔너리)로 충분하다.
운영 전환 시 Protocol 을 유지한 채 RDB 구현으로 교체하면 된다.
"""

from threading import Lock
from typing import Protocol

from app.schemas.persona import Persona


class PersonaStore(Protocol):
    def save(self, persona: Persona) -> None: ...
    def get(self, user_id: str) -> Persona | None: ...


class InMemoryPersonaStore:
    def __init__(self) -> None:
        self._data: dict[str, Persona] = {}
        self._lock = Lock()

    def save(self, persona: Persona) -> None:
        with self._lock:
            self._data[persona.user_id] = persona

    def get(self, user_id: str) -> Persona | None:
        return self._data.get(user_id)


# 프로세스 전역 싱글턴
persona_store: PersonaStore = InMemoryPersonaStore()
