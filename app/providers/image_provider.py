"""이미지 생성 프로바이더 (격리 계층).

캐릭터 이미지를 만드는 구체 백엔드(Databricks/OpenAI/…)에 서비스가 직접 의존하지 않도록
``ImageProvider`` 포트로만 접근한다. 경계 타입은 **투명 배경 PNG 바이트**다.
프로바이더 교체는 설정(PERSONA_IMAGE_PROVIDER / PERSONA_IMAGE_MODEL)만으로 이뤄진다.

기본값은 ``mock`` — 외부 의존성 없이 표준 라이브러리만으로 투명 배경 플레이스홀더 PNG 를
생성한다. 실제 모델(예: Databricks serving endpoint)이 준비되면 .env 만 바꿔 교체한다.
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from functools import lru_cache
from typing import Protocol

from app.config import get_settings


class ImageProvider(Protocol):
    """캐릭터 이미지를 생성하는 포트. 반환은 투명 배경 PNG 바이트."""

    def generate(self, prompt: str) -> bytes: ...


# --- PNG 인코딩 (표준 라이브러리만; Mock 이 사용) ---

def _encode_png(width: int, height: int, rows: list[bytes]) -> bytes:
    """8-bit RGBA 스캔라인 리스트를 PNG 바이트로 인코딩한다."""
    raw = b"".join(b"\x00" + row for row in rows)  # 각 행 앞에 filter 바이트(0)

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # bit depth 8, color type 6(RGBA)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")


# 플레이스홀더 팔레트 (프롬프트 해시로 하나 선택 → 캐릭터마다 색이 달라짐)
_PALETTE = [
    (99, 132, 220), (86, 178, 150), (214, 138, 78),
    (176, 124, 214), (208, 106, 128), (108, 170, 200),
]


class MockImageProvider:
    """의존성 없는 투명 배경 플레이스홀더 아바타(머리+어깨 실루엣)를 생성한다.

    실제 이미지 모델이 배선되기 전까지 파이프라인(생성→저장→GET 응답→웹뷰)을
    end-to-end 로 동작시키기 위한 것. 진짜 알파 투명(배경 alpha=0)을 낸다.
    """

    def generate(self, prompt: str) -> bytes:
        w = h = 512
        seed = int(hashlib.sha256(prompt.encode()).hexdigest(), 16)
        r, g, b = _PALETTE[seed % len(_PALETTE)]
        head = (min(r + 24, 255), min(g + 24, 255), min(b + 24, 255))  # 머리는 살짝 밝게

        rows: list[bytes] = []
        for y in range(h):
            row = bytearray()
            for x in range(w):
                px = (0, 0, 0, 0)  # 기본: 완전 투명 배경
                if (x - 256) ** 2 + (y - 190) ** 2 <= 96 ** 2:            # 머리(원)
                    px = (*head, 255)
                elif y > 262 and ((x - 256) / 178.0) ** 2 + ((y - 540) / 250.0) ** 2 <= 1.0:  # 어깨(타원)
                    px = (r, g, b, 255)
                row += bytes(px)
            rows.append(bytes(row))
        return _encode_png(w, h, rows)


class DatabricksImageProvider:
    """Databricks serving endpoint 로 이미지를 생성한다. (엔드포인트 규격 확인 필요)

    ⚠️ 워크스페이스의 이미지 생성 serving endpoint 존재/응답 형식이 아직 확정되지 않았다.
    아래는 OpenAI 호환 images API 형태를 가정한 best-effort 구현이며, 실제 배선 시
    엔드포인트 경로와 응답 스키마(b64_json / url 등), 투명 배경 지원 여부를 확인해야 한다.
    대부분의 이미지 모델은 불투명 배경을 내므로, "배경 없이 캐릭터만"이 필요하면
    배경 제거(rembg 등) 후처리 단계를 여기(경계 안)에서 추가한다.
    """

    def __init__(self, model: str, workspace_url: str, client_id: str, client_secret: str) -> None:
        self._model = model
        self._workspace_url = workspace_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret

    def generate(self, prompt: str) -> bytes:
        import base64

        import httpx

        from app.providers.databricks import get_databricks_token

        if not self._model:
            raise RuntimeError(
                "PERSONA_IMAGE_MODEL(이미지 serving endpoint 이름)이 설정되지 않았습니다."
            )
        token = get_databricks_token(
            workspace_url=self._workspace_url,
            client_id=self._client_id or None,
            client_secret=self._client_secret or None,
        )
        # ⚠️ 엔드포인트 경로/요청·응답 스키마는 실제 서빙 규격에 맞춰 확정할 것.
        resp = httpx.post(
            f"{self._workspace_url}/serving-endpoints/{self._model}/invocations",
            headers={"Authorization": f"Bearer {token}"},
            json={"prompt": prompt, "n": 1, "size": "1024x1024"},
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()
        b64 = payload["data"][0]["b64_json"]  # OpenAI images 형태 가정
        return base64.b64decode(b64)


@lru_cache
def get_image_provider() -> ImageProvider:
    """설정에 따라 이미지 프로바이더 구현을 반환한다. 기본은 mock."""
    settings = get_settings()
    if settings.image_provider == "databricks":
        return DatabricksImageProvider(
            model=settings.image_model,
            workspace_url=settings.databricks_workspace_url,
            client_id=settings.databricks_client_id,
            client_secret=settings.databricks_client_secret,
        )
    return MockImageProvider()