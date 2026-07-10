"""캐릭터 저장소 (인메모리, MVP)."""

from threading import Lock
from typing import Protocol

from app.schemas.character import Character


class CharacterStore(Protocol):
    def save(self, character: Character) -> None: ...
    def get(self, user_id: str) -> Character | None: ...


class InMemoryCharacterStore:
    def __init__(self) -> None:
        self._data: dict[str, Character] = {}
        self._lock = Lock()

    def save(self, character: Character) -> None:
        with self._lock:
            self._data[character.user_id] = character

    def get(self, user_id: str) -> Character | None:
        return self._data.get(user_id)


# 프로세스 전역 싱글턴
character_store: CharacterStore = InMemoryCharacterStore()
