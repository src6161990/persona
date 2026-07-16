"""MRF WebRTC DataChannel 검증용 HTTP signaling API."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.webrtc import WebRtcAnswer, WebRtcOffer
from app.webrtc.gateway import WebRtcGateway, WebRtcUnavailableError

router = APIRouter(prefix="/webrtc", tags=["webrtc-poc"])
gateway = WebRtcGateway()


@router.post("/offer", response_model=WebRtcAnswer, status_code=status.HTTP_201_CREATED)
async def accept_offer(offer: WebRtcOffer) -> WebRtcAnswer:
    """MRF offer를 수락하고 SDP answer를 돌려준다.

    PoC에서는 non-trickle ICE만 지원한다. 연결된 DataChannel의 binary message는
    PCM frame으로 간주해 동일 bytes를 echo한다.
    """
    try:
        sdp, sdp_type = await gateway.accept_offer(offer.session_id, offer.sdp, offer.type)
    except WebRtcUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WebRTC PoC dependency is not installed. Run: uv sync --extra webrtc",
        ) from None
    return WebRtcAnswer(session_id=offer.session_id, sdp=sdp, type=sdp_type)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(session_id: str) -> None:
    """MRF 세션 종료 이벤트에 대응한다."""
    await gateway.close(session_id)
