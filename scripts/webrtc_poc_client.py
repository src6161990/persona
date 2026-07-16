"""MRF 역할의 로컬 WebRTC PCM DataChannel 검증 클라이언트.

실행:
    uv run --extra webrtc python scripts/webrtc_poc_client.py

실행 중인 Persona gateway에 SDP offer를 보내고, 반환된 SDP answer를 적용한다.
그 뒤 binary PCM frame 하나를 전송해 동일 frame이 echo되는지 확인한다.
"""

from __future__ import annotations

import argparse
import asyncio
import uuid

import httpx
from aiortc import RTCPeerConnection, RTCSessionDescription


async def run(base_url: str, session_id: str, pcm_frame: bytes) -> None:
    # 1) 이 프로세스가 MRF 역할의 WebRTC peer가 된다.
    # PeerConnection은 ICE/DTLS/SCTP 등 WebRTC 연결 수립을 관리한다.
    peer = RTCPeerConnection()

    # 2) MRF가 PCM을 싣는다고 가정한 DataChannel을 생성한다.
    # 실제 MRF 명세에서 label이 정해지면 "pcm" 대신 그 값을 사용한다.
    channel = peer.createDataChannel("pcm")

    # DataChannel은 비동기로 열린다. PCM을 보내기 전에 open 상태가 될 때까지 기다린다.
    opened = asyncio.Event()
    # 아직 값이 없는 '응답 한 건 대기 상자'다.
    # 아래 on_message가 gateway의 echo PCM을 받으면 set_result(message)로 값을 채우고,
    # 뒤의 ``await response_frame``은 그때까지 다른 WebRTC 작업을 막지 않고 기다린다.
    # 이 PoC는 PCM frame 하나의 왕복만 검증하므로 Future 하나만 사용한다.
    # 실제 STT streaming에서는 frame마다 Queue에 넣어 계속 소비하는 구조로 바꾼다.
    response_frame: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    @channel.on("open")
    def on_open() -> None:
        opened.set()

    @channel.on("message")
    def on_message(message: str | bytes) -> None:
        if isinstance(message, bytes) and not response_frame.done():
            response_frame.set_result(message)

    try:
        # 3) offerer(MRF 역할)인 이 peer가 SDP offer를 만든다.
        # setLocalDescription은 offer를 적용하고 ICE candidate gathering을 수행한다.
        offer = await peer.createOffer()
        await peer.setLocalDescription(offer)
        local = peer.localDescription
        assert local is not None

        async with httpx.AsyncClient(base_url=base_url, timeout=15) as client:
            # 4) HTTP는 WebRTC 자체가 아니라 signaling 전달용이다.
            # Persona gateway는 이 offer를 받고 SDP answer를 HTTP 응답으로 돌려준다.
            response = await client.post(
                "/webrtc/offer",
                json={"session_id": session_id, "type": local.type, "sdp": local.sdp},
            )
            response.raise_for_status()
            answer = response.json()

            # 5) 받은 answer를 MRF peer에 적용한다.
            # 이 뒤에는 두 peer가 ICE/DTLS/SCTP를 통해 DataChannel 연결을 수립한다.
            await peer.setRemoteDescription(
                RTCSessionDescription(sdp=answer["sdp"], type=answer["type"])
            )
            await asyncio.wait_for(opened.wait(), timeout=10)

            # 6) 연결된 DataChannel으로 binary PCM frame을 전송한다.
            # PoC gateway는 binary message를 변형 없이 echo하도록 구현돼 있다.
            channel.send(pcm_frame)
            echoed = await asyncio.wait_for(response_frame, timeout=5)
            if echoed != pcm_frame:
                raise RuntimeError(f"PCM echo mismatch: sent={pcm_frame!r} received={echoed!r}")

            print(
                f"OK: session={session_id}, DataChannel PCM echo verified "
                f"({len(pcm_frame)} bytes)"
            )

            # 7) HTTP lifecycle API로 gateway 세션도 명시적으로 정리한다.
            await client.delete(f"/webrtc/sessions/{session_id}")
    finally:
        # 로컬 peer의 UDP socket 및 WebRTC transport를 정리한다.
        await peer.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persona WebRTC PCM DataChannel PoC client")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--session-id", default=f"local-mrf-{uuid.uuid4().hex[:8]}")
    parser.add_argument(
        "--pcm-hex",
        default="0100feff",
        help="전송할 PCM frame bytes의 hexadecimal 표현 (기본: 4 bytes)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.base_url, args.session_id, bytes.fromhex(args.pcm_hex)))
