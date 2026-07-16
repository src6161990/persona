"""일반 WebRTC peer로 PCM DataChannel을 echo하는 최소 gateway.

이 모듈은 MRF와의 연결성 검증만 담당한다. 받은 binary message(PCM frame)를
그대로 되돌려 보내므로, MRF 측에서 frame 왕복 및 순서를 바로 검증할 수 있다.
실제 STT/TTS 연결은 이 경계가 확인된 뒤 별도의 PCM stream adapter로 붙인다.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WebRtcGateway:
    """세션별 aiortc PeerConnection을 관리하는 PoC gateway."""

    def __init__(self) -> None:
        self._peers: dict[str, Any] = {}

    async def accept_offer(self, session_id: str, sdp: str, sdp_type: str) -> tuple[str, str]:
        """offer를 수락하고 answer를 반환한다.

        aiortc import를 지연시켜 기본 Persona API는 WebRTC optional extra 없이도
        실행되게 한다.
        """
        try:
            from aiortc import RTCPeerConnection, RTCSessionDescription
        except ImportError as exc:  # pragma: no cover - 환경 의존 분기
            raise WebRtcUnavailableError from exc

        await self.close(session_id)
        peer = RTCPeerConnection()
        self._peers[session_id] = peer

        @peer.on("datachannel")
        def on_datachannel(channel: Any) -> None:
            logger.info("WebRTC DataChannel opened: session=%s label=%s", session_id, channel.label)

            @channel.on("message")
            def on_message(message: str | bytes) -> None:
                # PoC 계약: binary message는 PCM frame이며 변형 없이 echo 한다.
                # text message는 signaling/debug 용도로만 로그를 남긴다.
                if isinstance(message, bytes):
                    channel.send(message)
                    return
                logger.debug("WebRTC text message: session=%s message=%s", session_id, message)

        @peer.on("connectionstatechange")
        async def on_connection_state_change() -> None:
            state = peer.connectionState
            logger.info("WebRTC connection state: session=%s state=%s", session_id, state)
            if state in {"failed", "closed"}:
                self._peers.pop(session_id, None)

        await peer.setRemoteDescription(RTCSessionDescription(sdp=sdp, type=sdp_type))
        answer = await peer.createAnswer()
        await peer.setLocalDescription(answer)
        local_description = peer.localDescription
        if local_description is None:  # 방어적 검사; aiortc 정상 흐름에서는 발생하지 않는다.
            await self.close(session_id)
            raise RuntimeError("WebRTC local description was not created")
        return local_description.sdp, local_description.type

    async def close(self, session_id: str) -> None:
        """세션을 명시적으로 종료한다."""
        peer = self._peers.pop(session_id, None)
        if peer is not None:
            await peer.close()


class WebRtcUnavailableError(RuntimeError):
    """WebRTC optional dependency가 설치되지 않은 경우."""
