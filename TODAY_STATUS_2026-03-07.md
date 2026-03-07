# Today Status 2026-03-07

## Overall Assessment

Today closed the gap between a documentation-heavy scaffold and a more truthful integration-ready runtime baseline.

The repository is still not a finished product, but it is materially better aligned with its own architecture now:
- scaffold mode is explicit
- live mode is more truthful
- a real Ollama execution path exists
- the live path has been smoke-tested successfully against local `Ollama` with `qwen3.5:0.8b`
- model-missing cases now return actionable installation guidance
- chat contract is documented as synchronous for the current v1 state
- presence and conversation state are less misleading than before

## What Changed Today

### Runtime truthfulness
- added a real Ollama adapter path
- made live runtime mode distinguish between:
  - provider unavailable
  - provider not implemented
  - provider reachable but model not pulled
  - provider invalid output
- added explicit install guidance for missing local models
- changed the default Ollama-capable text model name to `qwen3.5:0.8b`
- made Ollama model naming more robust by normalizing common HF-style aliases
- fixed local provider HTTP calls to ignore shell proxy settings when talking to `127.0.0.1`
- fixed provider health handling so runtime aborts early on unhealthy providers instead of continuing into `chat()`

### Contract cleanup
- documented `/api/v1/chat/send` as synchronous in the current v1 state
- aligned runtime responses with `completed`, `degraded`, and `failed` outcomes
- improved provider inventory and provider health semantics

### State cleanup
- user messages now enter structured message history
- context assembly now uses structured recent conversation lines
- presence state has a minimal maintained path during chat and observation flows
- config updates preserve proactive cooldown state

### Repo hygiene
- removed historical `AGENT_REVIEW_COMMENTS*.md` files from the root working tree
- kept `AGENT_START_HERE.md` as the main entrypoint

## Current P1

These are the highest-priority remaining work items.

1. Expand real end-to-end validation beyond the current local smoke test and cover more prompts, latency, and stability
2. Decide whether synchronous `/chat/send` remains acceptable for v1 or should move to task-first async execution
3. Extend provider health semantics from static probe states to actual runtime observability
4. Make Python test execution first-class in local setup and CI

## Current P2

These are important, but not the immediate blockers.

1. Expand presence state transitions beyond the current minimal path
2. Replace in-memory repositories with a persistent storage layer
3. Add real WebSocket/event streaming support
4. Flesh out tool execution beyond registry-level definitions
5. Continue improving memory and skill-system implementation

## Current Repository Position

The repository is now suitable as an internal iteration checkpoint, but it still should not be mistaken for a user-ready desktop agent.

The main positive change is that the codebase is more honest now:
- it is clearer when inference is real
- clearer when it is stubbed
- clearer when a model is missing
- clearer what contract the current chat endpoint actually follows

## Smoke Test Notes

- `ollama pull qwen3.5:0.8b` completed successfully on this machine
- direct HTTP generation through the local Ollama service returned the expected smoke string
- `ayria` live mode returned a completed `/api/v1/chat/send` response against that local model
- the `ollama run` CLI path still crashed in this environment, but the service-backed HTTP path worked and is the path `ayria` uses
