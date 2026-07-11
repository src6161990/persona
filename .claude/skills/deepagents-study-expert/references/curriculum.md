# Deep Agents project-based curriculum

Read this file at the start of every study request. The URLs are navigation pointers, not cached documentation: open the selected official page again before teaching it.

## Curriculum

| # | Area | Topic | Official page | Initial persona-project anchor |
|---:|---|---|---|---|
| 1 | Execution environment | Tools | https://docs.langchain.com/oss/python/deepagents/tools | `app/agents/tools.py`, `character_chat_agent()` |
| 2 | Execution environment | Backends | https://docs.langchain.com/oss/python/deepagents/backends | Compare Deep Agents virtual filesystem backends with `app/store/`; do not conflate them |
| 3 | Execution environment | Permissions | https://docs.langchain.com/oss/python/deepagents/permissions | `.env` protection, future filesystem tools, least privilege |
| 4 | Execution environment | Multimodality | https://docs.langchain.com/oss/python/deepagents/multimodality | Possible audio/image inputs versus the current text-only STT boundary |
| 5 | Execution environment | Sandboxes | https://docs.langchain.com/oss/python/deepagents/sandboxes | No current code execution; evaluate only for analysis workflows |
| 6 | Execution environment | Interpreters | https://docs.langchain.com/oss/python/deepagents/interpreters | Deterministic transcript aggregation without shell access |
| 7 | Execution environment | Dynamic subagents | https://docs.langchain.com/oss/python/deepagents/dynamic-subagents | Possible on-demand specialist for relationship or speaking-style analysis |
| 8 | Execution environment | Event streaming | https://docs.langchain.com/oss/python/deepagents/event-streaming | Compare typed run events with the service's custom SSE frames |
| 9 | Execution environment | Streaming | https://docs.langchain.com/oss/python/deepagents/streaming | `stream_reply()`, `StreamingResponse`, token/done events |
| 10 | Context management | Skills | https://docs.langchain.com/oss/python/deepagents/skills | This local study skill; possible persona-analysis domain skills |
| 11 | Context management | Memory | https://docs.langchain.com/oss/python/deepagents/memory | Distinguish AGENTS.md memory, checkpointer state, persona records, and call history |
| 12 | Context management | Context engineering | https://docs.langchain.com/oss/python/deepagents/context-engineering | Raw transcript prompt size, summarization, offloading, prompt caching |
| 13 | Context management | Profiles | https://docs.langchain.com/oss/python/deepagents/profiles | Harness profiles versus the domain `PersonaProfile` name collision |
| 14 | Delegation | Subagents | https://docs.langchain.com/oss/python/deepagents/subagents | Decide whether persona facets merit isolated specialists |
| 15 | Delegation | Async subagents | https://docs.langchain.com/oss/python/deepagents/async-subagents | Background persona rebuilding and lifecycle/consistency concerns |
| 16 | Steering | Human-in-the-loop | https://docs.langchain.com/oss/python/deepagents/human-in-the-loop | Approval before sensitive character changes or consequential actions |
| 17 | Steering | Grading rubrics | https://docs.langchain.com/oss/python/deepagents/grading-rubrics | Evaluate faithfulness, privacy, persona consistency, and phone-response safety |

## Project facts to verify, not blindly repeat

- Agent factories live in `app/agents/persona_agent.py` and call `create_deep_agent` for persona building, character creation, and character editing.
- Character editing receives three custom tools from `app/agents/tools.py` and uses an in-memory LangGraph checkpointer.
- Real-time answering deliberately calls the chat model's `.stream()` directly instead of a Deep Agent, then exposes custom SSE through FastAPI.
- Domain persistence uses in-memory stores in `app/store/`. These are application repositories, not automatically Deep Agents filesystem backends or memory.
- Model construction is isolated behind `app/providers/model_provider.py`; the configured default is the Databricks endpoint `databricks-claude-opus-4-6`.
- Tests mock LLM calls, so they prove API orchestration but not actual tool selection, model behavior, or streaming event semantics.

Re-read the named files before using these anchors because the project evolves during the study.

## Recommended learning path

Follow 1–17 for a systematic first pass. Cross-reference these pairs when useful:

- Tools → Permissions → Human-in-the-loop for safe actions.
- Backends → Memory → Context engineering for state and context boundaries.
- Event streaming → Streaming for observability versus user-facing output.
- Dynamic subagents → Subagents → Async subagents for delegation choices.
- Skills → Profiles for reusable instructions versus harness configuration.
- Grading rubrics after at least one runnable behavior exists to evaluate.

Never mark a topic complete solely because it was summarized. Treat it as learned after the user can answer the check question or complete an equivalent exercise.
