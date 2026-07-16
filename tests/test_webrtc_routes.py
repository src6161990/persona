"""WebRTC signaling route와 최소 PCM DataChannel gateway를 검증한다."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.api import webrtc_routes
from app.main import app
from app.webrtc.gateway import WebRtcGateway

client = TestClient(app)


def test_webrtc_offer_returns_answer_from_gateway(monkeypatch):
    async def fake_accept_offer(session_id: str, sdp: str, sdp_type: str) -> tuple[str, str]:
        assert session_id == "mrf-1"
        assert sdp == "remote-sdp"
        assert sdp_type == "offer"
        return "local-sdp", "answer"

    monkeypatch.setattr(webrtc_routes.gateway, "accept_offer", fake_accept_offer)

    response = client.post(
        "/webrtc/offer",
        json={"session_id": "mrf-1", "sdp": "remote-sdp", "type": "offer"},
    )

    assert response.status_code == 201
    assert response.json() == {"session_id": "mrf-1", "sdp": "local-sdp", "type": "answer"}


def test_webrtc_offer_requires_offer_type():
    response = client.post(
        "/webrtc/offer",
        json={"session_id": "mrf-1", "sdp": "remote-sdp", "type": "answer"},
    )

    assert response.status_code == 422


def test_webrtc_gateway_echoes_binary_pcm_frames():
    """실제 aiortc peer 간 DataChannel binary frame 왕복을 검증한다."""
    aiortc = pytest.importorskip("aiortc", reason="WebRTC PoC extra is not installed")
    RTCPeerConnection = aiortc.RTCPeerConnection
    RTCSessionDescription = aiortc.RTCSessionDescription

    async def run() -> None:
        mrf_peer = RTCPeerConnection()
        gateway = WebRtcGateway()
        channel = mrf_peer.createDataChannel("pcm")
        received: asyncio.Queue[bytes] = asyncio.Queue()

        @channel.on("message")
        def on_message(message: bytes) -> None:
            received.put_nowait(message)

        try:
            offer = await mrf_peer.createOffer()
            await mrf_peer.setLocalDescription(offer)
            local = mrf_peer.localDescription
            assert local is not None

            answer_sdp, answer_type = await gateway.accept_offer(
                "loopback", local.sdp, local.type
            )
            await mrf_peer.setRemoteDescription(
                RTCSessionDescription(sdp=answer_sdp, type=answer_type)
            )

            for _ in range(100):
                if channel.readyState == "open":
                    break
                await asyncio.sleep(0.01)
            assert channel.readyState == "open"

            pcm_frame = b"\x01\x00\xfe\xff"
            channel.send(pcm_frame)
            assert await asyncio.wait_for(received.get(), timeout=2) == pcm_frame
        finally:
            await gateway.close("loopback")
            await mrf_peer.close()

    asyncio.run(run())
