# persona

통화 데이터 기반 **사용자 페르소나** 서비스.

AI 기능 3가지(통화요약 / 통화중 AI 비서 호출 / AI 대신받기)가 있다.
원시 통화 데이터를 분석해 사용자의 페르소나(말투·관심사·관계·의사결정 패턴)를 구축하고,
그 페르소나로 **"AI 대신받기"용 캐릭터**를 생성·튜닝하며, 대신 통화할 **컨텍스트**를 생성한다.

- **에이전트**: [DeepAgents](https://github.com/langchain-ai/deepagents) (LangChain/LangGraph 기반)
- **모델**: 프로바이더 격리 — 기본 Databricks endpoint `databricks-claude-opus-4-6`, 설정으로 OpenAI/Azure OpenAI 등 교체 가능
- **인터페이스**: FastAPI REST API

## 빠른 시작

```bash
uv sync                        # 의존성 설치 (기본 프로바이더 anthropic)
cp .env .env           # .env 열어 프로바이더/키 설정
uv run uvicorn app.main:app --reload
```

실행 후 `http://127.0.0.1:8000/docs` 에서 Swagger UI로 API 확인.

## LLM 프로바이더 교체

비즈니스 로직·에이전트는 `app/providers/model_provider.py` 의 `ModelProvider` 인터페이스에만 의존한다.
경계 타입은 LangChain `BaseChatModel` 이며 특정 벤더에 묶이지 않는다. 교체는 **설정만** 바꾸면 된다.

```bash
# 예) Anthropic → OpenAI
uv sync --extra openai
# .env
PERSONA_MODEL_PROVIDER=openai
PERSONA_MODEL_NAME=gpt-4.1
OPENAI_API_KEY=sk-...

# 예) Azure OpenAI (langchain-openai 사용)
PERSONA_MODEL_PROVIDER=azure_openai
PERSONA_MODEL_NAME=<배포명>
# AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT / OPENAI_API_VERSION

# 예) Databricks serving endpoint (OpenAI 호환, OAuth M2M)
uv sync --extra databricks
PERSONA_MODEL_PROVIDER=databricks
PERSONA_MODEL_NAME=<serving-endpoint-name>
# DATABRICKS_WORKSPACE_URL / DATABRICKS_CLIENT_ID / DATABRICKS_CLIENT_SECRET
```

프로바이더별 구현은 `app/providers/` 에 있다(예: `databricks.py`). anthropic/openai/azure_openai/google_genai 등은
LangChain `init_chat_model` 로, Databricks 는 OAuth 토큰 발급 후 `ChatOpenAI` 를 serving endpoint 에 연결한다.
완전 커스텀 백엔드가 필요하면 `ModelProvider` 를 구현해 `BaseChatModel` 을 반환하도록 감싸면 된다.

## 주요 엔드포인트

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/personas/{user_id}/build` | 원시 통화 데이터(body)로 페르소나 구축·저장 |
| `GET` | `/personas/{user_id}` | 페르소나 조회 |
| `POST` | `/personas/{user_id}/answer-context` | 걸려온 전화 정보로 "AI 대신받기" 컨텍스트 생성 |
| `POST` | `/personas/{user_id}/character` | 페르소나 기반 캐릭터 생성 (입력 user_id) |
| `GET` | `/personas/{user_id}/character` | 캐릭터 조회 |
| `POST` | `/personas/{user_id}/character/chat` | 멀티턴 채팅으로 캐릭터 수정 |
| `GET` | `/health` | 헬스체크 |

## 구조

```
app/
├── main.py                 # FastAPI 앱 진입점 + 예외 매핑
├── config.py               # 환경 설정
├── api/routes.py           # REST 엔드포인트
├── schemas/                # call(원시입력) / persona / character
├── providers/              # ModelProvider 인터페이스 (LLM 벤더 격리)
├── agents/                 # DeepAgent 정의(빌더/캐릭터) + 프롬프트 + 툴
├── services/               # 페르소나 / 캐릭터 오케스트레이션
└── store/                  # 인메모리 스토어 (MVP)
```

> 원시 통화 데이터는 **저장하지 않고** build 요청으로 받아 분석만 한다.
> 페르소나·캐릭터는 user_id 단일 문서라 인메모리로 충분(벡터DB 불필요). 운영 시 `store` 를 DB 구현으로 교체.
