"""대신받기 통화 대화 저장소.

call_id(통화) 단위로 상대방↔페르소나 발화 히스토리를 인메모리로 유지해 멀티턴을 잇는다.
role 은 'counterpart'(상대방 발화) / 'assistant'(대신받기 응답) 두 가지다.
운영 전환 시 Protocol 을 유지한 채 TTL/정리 정책이나 외부 저장소로 교체하면 된다.
"""

from threading import Lock
from typing import Protocol


class ConversationStore(Protocol):
    def get(self, call_id: str) -> list[tuple[str, str]]: ...
    def append(self, call_id: str, role: str, text: str) -> None: ...


class InMemoryConversationStore:
    def __init__(self) -> None:
        self._data: dict[str, list[tuple[str, str]]] = {}
        self._lock = Lock()

    def get(self, call_id: str) -> list[tuple[str, str]]:
        with self._lock:
            return list(self._data.get(call_id, []))

    def append(self, call_id: str, role: str, text: str) -> None:
        with self._lock:
            self._data.setdefault(call_id, []).append((role, text))


# 프로세스 전역 싱글턴
conversation_store: ConversationStore = InMemoryConversationStore()