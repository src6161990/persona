# PM — persona 프로젝트 관리 문서

> 진행 상황·결정사항·다음 할 일을 추적하는 리빙 문서. 작업이 진행되면 계속 갱신한다.
> 최종 갱신: 2026-07-10
> 참고: 프로젝트 구현 조율용 PM은 런타임 API가 아니라 Claude Code 서브에이전트(`.claude/agents/pm-orchestrator.md`)로 둔다.

## 1. 개요 / 바운더리

통화 데이터 기반 **사용자 페르소나** 서비스. 담당 기능만 유지하고 나머지는 상위/별도 서비스 몫.

- **담당**: ①페르소나 구축 ②조회 ③대신받기 컨텍스트 생성 ④캐릭터 생성 ⑤캐릭터 멀티턴 수정 ⑥캐릭터 조회
- **비담당(바운더리 밖)**: 통화요약·AI비서 원시데이터의 적재/저장, 통화 파이프라인 연동, 벡터DB
- 스택: DeepAgents(LangChain/LangGraph) + FastAPI, 모델은 **프로바이더 격리**(기본 Databricks endpoint `databricks-claude-opus-4-6`)

## 2. 구현 현황

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 프로젝트 세팅 (uv, deps, .env.example, README) | ✅ 완료 | |
| 설정 `app/config.py` | ✅ 완료 | 프로바이더/모델/토큰 |
| 스키마 `app/schemas` (call/persona/character) | ✅ 완료 | 원시 통화데이터 입력 모델 포함 |
| 스토어 `app/store` (persona/character, 인메모리) | ✅ 완료 | Protocol + 싱글턴 |
| **LLM 프로바이더 격리** `app/providers` | ✅ 완료 | `ModelProvider` 포트 + LangChain 어댑터 + Databricks(OAuth M2M) |
| 에이전트 `app/agents` (prompts/tools/persona_agent) | ✅ 완료 | 에이전트 4종 + 호출 헬퍼 |
| 서비스 `app/services` (persona/character) | ✅ 완료 | |
| API `app/api/routes.py` + `app/main.py` | ✅ 완료 | 엔드포인트 6 + health + 예외매핑 |
| PM 오케스트레이터 (개발용) `.claude/agents/pm-orchestrator.md` | ✅ 완료 | 런타임 아님 — 구현 조율용 서브에이전트 |
| 프로바이더 필수값 검증 (선언적 표) `app/providers/model_provider.py` | ✅ 완료 | 프로바이더별 필수 env fail-fast, 미등록 프로바이더는 통과 |
| 스모크 테스트 `tests/test_smoke.py` | ✅ 작성 | LLM 미호출 |
| 로컬 테스트 `requests.http` | ✅ 완료 | PyCharm HTTP Client |
| **런타임 검증 (import/pytest/e2e)** | ⏳ 대기 | 아래 4번 참고 |

## 3. 엔드포인트

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| POST | `/personas/{user_id}/build` | 원시 통화데이터로 페르소나 구축·저장 (입력 없으면 400) |
| GET | `/personas/{user_id}` | 페르소나 조회 (404) |
| POST | `/personas/{user_id}/answer-context` | 대신받기 한 턴: 상대 발화(text)→응답(text) SSE 스트리밍, call_id 멀티턴 (404) |
| POST | `/personas/{user_id}/character` | 캐릭터 생성 (페르소나 없으면 404) |
| GET | `/personas/{user_id}/character` | 캐릭터 조회 (404) |
| POST | `/personas/{user_id}/character/chat` | 멀티턴 채팅으로 캐릭터 수정 (404) |
| GET | `/health` | 헬스체크 |

## 4. 검증 현황 / 다음 할 일

- [x] `uv run python -c "import app.main"` — 임포트 확인 (OK)
- [x] `uv run --extra dev pytest -q` — 스모크 7건 전부 pass (LLM 미호출)
- [x] **실 Databricks e2e**: `build_persona` + `create_character` 실호출 성공 (endpoint `databricks-claude-opus-4-8`).
  - ✅ Databricks OAuth 토큰 발급 → serving endpoint 라우팅
  - ✅ deepagents 구조화 출력 `structured_response` 추출 정상 (Persona/Character 필드 정상 생성)
  - ✅ `InMemorySaver` import 경로 정상
- [ ] (선택) 서버 띄워 `requests.http` 로 character/chat(멀티턴)→answer-context 까지 확인 (구조화 경로는 확인됨, 잔여 저위험)

### 확정된 프로바이더/모델 설정
- **프로바이더는 databricks 로 확정** (config 기본값도 databricks).
- serving endpoint 이름 = 워크스페이스 목록 값. Claude 계열: `databricks-claude-opus-4-8` / `-opus-4-7` / `-fable-5` / `-sonnet-5` / `-haiku-4-5` 등.
- 기본값: `PERSONA_MODEL_NAME=databricks-claude-opus-4-6`.

## 5. 주요 결정 (Decision Log)

- **DeepAgents 채택**: 사용자가 지정. LangChain/LangGraph 기반.
- **모델 기본값 `databricks-claude-opus-4-6`**.
- **프로바이더 격리**: 모델 벤더 미확정(OpenAI/Azure OpenAI/Databricks 가능성) → `ModelProvider` 포트로 분리, 교체는 설정만. 경계 타입 `BaseChatModel`.
  - anthropic/openai/azure_openai/google_genai: LangChain `init_chat_model`.
  - **Databricks**: serving endpoint 가 OpenAI 호환 → `get_databricks_token`(OAuth M2M, client_credentials)로 토큰 발급 후 `ChatOpenAI(base_url=.../serving-endpoints)`. 토큰 만료 대비해 `_model()` 캐시 제거(호출 시 발급). 운영은 짧은 TTL 캐시/401 재발급 고려.
- **원시 데이터는 build 요청 body 수신**: 요약본이 아닌 원시 통화데이터라야 추론 정확도↑. 원시데이터는 저장 안 함.
- **벡터DB 미사용**: 페르소나·캐릭터는 user_id 단일 문서 → 인메모리(추후 RDB)로 충분. 의미검색이 필요한 곳은 원시 이력 쪽(상위 서비스, 범위 밖).
- **캐릭터 멀티턴 수정**: LangGraph checkpointer(thread_id=user_id) + `save_character` 툴로 상태 반영.
- **PM은 런타임 기능이 아님**: 초기에 `/pm` 런타임 엔드포인트로 오해해 구현했다가 제거함. PM은 이 프로젝트를 **구현·조율하는 개발용 Claude Code 서브에이전트**(`.claude/agents/pm-orchestrator.md`)로 둔다.

## 6. 리스크 / 향후

- 인메모리 스토어·checkpointer는 프로세스 재시작 시 소실(MVP). 운영은 RDB/영속 checkpointer로 교체.
- 원시 데이터를 프롬프트에 탑재 → 대용량 이력은 최근 N건 제한/파일시스템 시딩 필요.
- 페르소나/캐릭터 스토어를 상위 DB와 어떻게 공유·영속화할지 추후 결정.
