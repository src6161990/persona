"""스모크 테스트 — LLM 을 호출하지 않는다.

에이전트 팩토리/호출 헬퍼를 monkeypatch 로 대체해 라우팅·검증·스토어·예외 매핑만 검증한다.
"""

import pytest
from fastapi.testclient import TestClient

from app.agents import persona_agent
from app.main import app
from app.schemas.character import CharacterProfile
from app.schemas.persona import PersonaProfile
from app.store.character_store import character_store
from app.store.conversation_store import conversation_store
from app.store.persona_store import persona_store

client = TestClient(app)

SAMPLE_PROFILE = PersonaProfile(
    speaking_style="정중하고 간결한 말투",
    frequent_topics=["업무 일정", "예약"],
    key_relationships=["팀 동료", "가족"],
    preferences=["빠른 확인 선호"],
    decision_patterns=["즉답을 선호"],
    summary="정중하고 효율을 중시하는 사용자",
)

SAMPLE_CHARACTER = CharacterProfile(
    name="대리 비서",
    tone="정중함",
    speaking_style="간결하고 예의 바름",
    do=["존댓말 사용"],
    dont=["확답이 필요한 약속을 대신 하지 않기"],
    catchphrases=["확인 후 다시 연락드리겠습니다"],
    greeting="안녕하세요, 대신 전화를 받았습니다.",
    summary="정중하게 용건만 확인하는 대리 응대 캐릭터",
)


@pytest.fixture(autouse=True)
def _no_llm(monkeypatch):
    """에이전트를 가짜로 대체하고 스토어를 초기화한다."""
    monkeypatch.setattr(persona_agent, "build_persona_agent", lambda: object())
    monkeypatch.setattr(persona_agent, "create_character_agent", lambda: object())
    monkeypatch.setattr(persona_agent, "character_chat_agent", lambda user_id: object())

    def fake_structured(agent, prompt, model_cls, config=None):
        return SAMPLE_PROFILE if model_cls is PersonaProfile else SAMPLE_CHARACTER

    monkeypatch.setattr(persona_agent, "invoke_structured", fake_structured)
    monkeypatch.setattr(
        persona_agent, "invoke_text", lambda agent, prompt, config=None: "테스트 응답입니다."
    )
    # 대신받기 스트리밍: LLM 대신 고정 토큰을 흘려보낸다.
    monkeypatch.setattr(
        persona_agent,
        "stream_reply",
        lambda system_prompt, history, utterance: iter(["테스트 ", "응답입니다."]),
    )

    persona_store._data.clear()  # type: ignore[attr-defined]
    character_store._data.clear()  # type: ignore[attr-defined]
    conversation_store._data.clear()  # type: ignore[attr-defined]
    yield


def _build_payload() -> dict:
    return {
        "calls": [
            {
                "call_id": "c1",
                "started_at": "2026-07-01T10:00:00+09:00",
                "direction": "inbound",
                "counterpart": "카페 사장",
                "utterances": [
                    {"speaker": "user", "text": "네, 오후 3시 예약 확인 부탁드려요."},
                    {"speaker": "counterpart", "text": "확인됐습니다."},
                ],
            }
        ],
        "assistant_events": [],
    }


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_get_persona_404():
    assert client.get("/personas/u1").status_code == 404


def test_build_empty_returns_400():
    resp = client.post("/personas/u1/build", json={"calls": [], "assistant_events": []})
    assert resp.status_code == 400


def test_build_then_get():
    resp = client.post("/personas/u1/build", json=_build_payload())
    assert resp.status_code == 201
    persona = resp.json()["persona"]
    assert persona["user_id"] == "u1"
    assert persona["speaking_style"] == SAMPLE_PROFILE.speaking_style

    got = client.get("/personas/u1")
    assert got.status_code == 200
    assert got.json()["user_id"] == "u1"


def test_character_requires_persona_first():
    assert client.post("/personas/u1/character").status_code == 404


def test_character_chat_requires_character_first():
    client.post("/personas/u1/build", json=_build_payload())
    assert client.post("/personas/u1/character/chat", json={"message": "더 친근하게"}).status_code == 404


def test_full_flow():
    client.post("/personas/u1/build", json=_build_payload())

    created = client.post("/personas/u1/character")
    assert created.status_code == 201
    assert created.json()["name"] == SAMPLE_CHARACTER.name

    got = client.get("/personas/u1/character")
    assert got.status_code == 200

    chatted = client.post("/personas/u1/character/chat", json={"message": "인사말을 더 밝게"})
    assert chatted.status_code == 200
    assert "reply" in chatted.json()
    assert chatted.json()["character"]["user_id"] == "u1"

    # 대신받기 한 턴 — SSE 스트리밍(text in → text out)
    resp = client.post(
        "/personas/u1/answer-context",
        json={"call_id": "call-1", "utterance": "안녕하세요, 택배 왔습니다.", "caller": "택배기사"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "event: token" in body
    assert "event: done" in body
    assert "테스트 응답입니다." in body


def test_answer_requires_persona_or_character():
    resp = client.post(
        "/personas/u1/answer-context", json={"call_id": "c", "utterance": "여보세요"}
    )
    assert resp.status_code == 404


def test_answer_multiturn_accumulates_history():
    client.post("/personas/u1/build", json=_build_payload())

    for text in ["여보세요", "택배 왔어요"]:
        r = client.post(
            "/personas/u1/answer-context", json={"call_id": "call-x", "utterance": text}
        )
        assert r.status_code == 200

    history = conversation_store.get("call-x")
    # 상대 발화 2 + 페르소나 응답 2 = 4, 번갈아 기록
    assert len(history) == 4
    assert history[0] == ("counterpart", "여보세요")
    assert history[1][0] == "assistant"
    assert history[2] == ("counterpart", "택배 왔어요")
