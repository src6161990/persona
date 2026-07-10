---
name: api-flow-view
description: persona 서비스의 API 호출 플로우를 애니메이션 웹 뷰(아티팩트)로 생성·갱신한다. 코드(라우트/서비스/에이전트/스토어)를 바꾼 뒤 "플로우 뷰 업데이트", "API 흐름도 갱신", "flow tracer 반영" 같은 요청에 사용. 엔드포인트가 추가·삭제되거나 호출 경로/가드/스트리밍이 바뀌었을 때 tracer.html 의 FLOW DATA 를 실제 코드에 맞춰 재생성하고 같은 URL 로 다시 게시한다.
---

# API Flow View — 유지보수 스킬

persona 서비스의 각 API가 `Client → API → Service → Agent → Provider → Store` 계층을
어떻게 타고 흐르는지 보여주는 **인터랙티브 트레이서 아티팩트**를 코드와 동기화한다.

- 아티팩트 원본 HTML: `.claude/skills/api-flow-view/tracer.html`
- **게시 URL(업데이트 대상)**: `https://claude.ai/code/artifact/89b0658c-7be1-48a3-a99e-d624cdd1cc0b`
- 디자인/재생 엔진(CSS·JS)은 이미 완성돼 있다. **평소 갱신은 HTML 안의 `FLOW DATA` 블록만 고친다.**

## 언제 무엇을 하나

코드가 바뀌면 아래 순서로 `tracer.html` 의 `FLOW DATA` 를 실제 코드에 맞춰 갱신하고 재게시한다.

### 1) 진실의 원천(source of truth) 읽기

플로우 데이터는 항상 이 파일들의 **현재 코드**에서 파생한다. 기억이나 과거 상태로 쓰지 말고 매번 읽는다.

| 계층(lane) | 파일 | 여기서 뽑는 것 |
|---|---|---|
| `api` | `app/api/routes.py` | 엔드포인트(method·path·핸들러), 어느 서비스 함수로 위임하는지, SSE(`StreamingResponse`) 여부 |
| `service` | `app/services/persona_service.py`, `app/services/character_service.py` | 오케스트레이션 순서, 가드(조기 반환/예외), 프롬프트 조립, 저장소 호출 순서 |
| `agent` | `app/agents/persona_agent.py`, `app/agents/prompts.py`, `app/agents/tools.py` | 에이전트 팩토리(`create_deep_agent`/`stream_reply`), `response_format`, 시스템 프롬프트명, 도구 목록, 루프(ReAct/스트리밍) |
| `provider` | `app/providers/model_provider.py`, `app/providers/databricks.py` | LLM 호출 지점(구조화 출력 vs 스트리밍) |
| `store` | `app/store/*.py` | 어떤 저장소를 언제 get/save/append 하는지 |
| `errors` | `app/errors.py`, `app/main.py` | 예외 → HTTP 상태 매핑(가드의 `→ 4xx` 라벨) |

빠르게 훑는 명령: `grep -n "@router" app/api/routes.py` 로 엔드포인트 목록부터 잡고,
각 핸들러가 부르는 서비스 함수를 따라가며 호출 체인을 복원한다.

### 2) `FLOW DATA` 블록 갱신

`tracer.html` 안 `// === FLOW DATA ===` ~ `// === END FLOW DATA ===` 사이의
`LANES` 와 `ENDPOINTS` 만 편집한다. 그 밖의 CSS·재생 엔진은 건드리지 않는다.

- **`LANES`**: 아키텍처 계층이 늘거나 줄 때만 수정(보통 그대로 둔다). 순서 = 화면상 위→아래 밴드.
- **`ENDPOINTS`**: API 하나당 객체 하나. 아래 스키마를 따른다.

```js
{
  id: "build",                       // 고유 키(영문)
  method: "POST",                    // "GET" | "POST" ...
  group: "페르소나",                  // 사이드바 묶음("페르소나" | "대신받기" | "캐릭터")
  name: "페르소나 구축",              // 사람이 읽는 이름
  path: "/personas/{user_id}/build", // 라우트 경로(routes.py 와 일치)
  sse: true,                         // (선택) SSE 스트리밍이면 true → SSE 배지
  purpose: "…",                      // 한두 문장 목적
  result: "201 · PersonaBuildResponse { persona }", // 성공 응답 요약
  steps: [ /* 실제 호출 순서대로 */ ]
}
```

**step(각 호출 단계) 스키마**:

```js
{
  lane: "service",     // "client" | "api" | "service" | "agent" | "provider" | "store"
  fn:   "build_persona()",                 // 함수/호출 이름(모노스페이스로 표시)
  file: "services/persona_service.py",     // 위치(짧게). client 레인은 "요청"/"응답" 등
  desc: "입력 검증 후 에이전트 오케스트레이션", // 한 줄 설명
  kind: "call",        // 아래 표 참고 — 엣지/색/애니메이션이 달라진다
  guard: "if request.is_empty() → 400 EmptyBuildInput", // (선택) 이 단계의 조기 반환/예외 분기
  loop:  "event: token {delta} × N → SSE"               // (선택) 반복/스트리밍 루프. 재생 시 펄스
}
```

**`kind` 값**:

| kind | 뜻 | 표현 |
|---|---|---|
| `req` | 클라이언트 요청 진입 | 시작점 |
| `call` | 정방향 호출 | 실선 엣지 |
| `ret` | 반환/역방향 | 점선 엣지 |
| `build` | 프롬프트/데이터 조립 등 내부 가공 | 실선 |
| `loop` | 반복(ReAct 루프)·스트리밍(토큰) | 점선 루프 배지 + 재생 중 펄스 |
| `ok` | 성공 응답(2xx) | 틸그린, 점선 엣지, 종료점 |

**작성 원칙**
- `steps` 순서 = 코드가 실제로 실행하는 순서. 마지막 step 은 보통 `client` 레인의 `ok`.
- 가드는 별도 노드로 만들지 말고 그 단계 객체의 `guard` 필드로 붙인다(로그에도 분기로 찍힌다).
- 파일 경로는 `app/` 를 떼고 짧게(`services/persona_service.py`). `provider`·LLM 호출은 `"→ Databricks Claude"` 처럼 표기.
- 지어내지 말 것. 코드에 없는 단계·가드·루프는 넣지 않는다. 확신이 없으면 해당 파일을 다시 읽는다.

### 3) 재게시(같은 URL 유지)

`tracer.html` 을 수정한 뒤 Artifact 도구로 **위의 게시 URL 을 `url` 인자로 넘겨** 같은 링크에 덮어쓴다.

- `file_path`: `.claude/skills/api-flow-view/tracer.html`
- `url`: 위 "게시 URL" (이 대화에서 이미 이 파일로 게시했다면 `url` 없이 같은 `file_path` 재게시만으로도 URL 유지)
- `favicon`: `🛰️` (변경 금지 — 탭 아이콘 유지)
- `label`: 이번 변경을 요약한 짧은 이름(예: `add-delete-endpoint`)
- `description`: 한 문장 요약

게시 후 사용자에게 **최종 URL 과 바뀐 점(추가/삭제/변경된 엔드포인트·단계)**을 한국어로 간단히 보고한다.

## 자가 점검
- [ ] `routes.py` 의 모든 `@router` 엔드포인트가 `ENDPOINTS` 에 1:1로 있는가? (없어진 건 삭제)
- [ ] 각 엔드포인트의 `steps` 가 핸들러→서비스→에이전트/스토어 실제 호출 순서와 맞는가?
- [ ] 서비스의 모든 조기 반환/예외가 `guard` 로 표현됐고 상태코드가 `errors.py`/`main.py` 매핑과 일치하는가?
- [ ] SSE·ReAct·토큰 스트리밍 등 루프가 `loop` 로 표시됐는가?
- [ ] CSS·재생 엔진(FLOW DATA 바깥)은 건드리지 않았는가?
