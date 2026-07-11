"""캐릭터 이미지 저장소.

생성된 캐릭터 이미지를 user_id 당 하나의 data URI(``data:image/png;base64,...``)로
인메모리 보관한다. GET /character 응답이 이 값을 실어 나른다. 이미지 바이트를 Character
객체(=character_store)에 섞지 않고 분리 보관해, 프로파일 저장/조회를 가볍게 유지한다.
운영 전환 시 Protocol 을 유지한 채 오브젝트 스토리지(S3/MinIO) 구현으로 교체하면 된다.
"""

from threading import Lock
from typing import Protocol


class ImageStore(Protocol):
    def save(self, user_id: str, data_uri: str) -> None: ...
    def get(self, user_id: str) -> str | None: ...


class InMemoryImageStore:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._lock = Lock()

    def save(self, user_id: str, data_uri: str) -> None:
        with self._lock:
            self._data[user_id] = data_uri

    def get(self, user_id: str) -> str | None:
        return self._data.get(user_id)


# 프로세스 전역 싱글턴
image_store: ImageStore = InMemoryImageStore()
