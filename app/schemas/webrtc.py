"""MRF WebRTC DataChannel 검증용 signaling 스키마."""

from pydantic import BaseModel, Field


class WebRtcOffer(BaseModel):
    """MRF가 HTTP signaling으로 보내는 SDP offer."""

    session_id: str = Field(min_length=1, max_length=128)
    sdp: str = Field(min_length=1)
    type: str = Field(pattern="^offer$")


class WebRtcAnswer(BaseModel):
    """Persona gateway가 반환하는 SDP answer."""

    session_id: str
    sdp: str
    type: str
