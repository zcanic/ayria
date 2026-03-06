# AGENT_REVIEW_COMMENTS

This file is a direct review and modification instruction set for the next agent.
It is intentionally concrete.
Do not treat it as optional advice.

## Scope

Target project:
- [ayria](/Volumes/zcan mac/nyatter/ayria)

Review basis:
- current v1 implementation using `Qwen3.5-0.8B` as the intended local trial model
- current runtime and desktop scaffold under `ayria/apps/runtime` and `ayria/apps/desktop`

## Top-Level Assessment

The current code is not yet a true v1 of a local desktop presence system.
It is still a partial scaffold with some live routes.

The main architectural problem is this:
- the code claims routing and model selection
- but the runtime does not actually execute provider-backed inference
- therefore the system presents itself as more functional than it is

This must be corrected first.

## Priority Order

Fix in this order:

1. stop pretending provider-backed chat exists if it does not
2. enforce privacy/runtime policy before screenshot ingestion
3. fix proactive cooldown behavior
4. align routing metadata with actual execution behavior
5. remove or defer broken WebSocket assumptions
6. add real tests for the above

## 1. Provider Path Is Fake

### Problem

Current chat flow does not call any LLM provider.
The runtime builds a route and then returns the input text, optionally with window title context appended.

Relevant files:
- [chat.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/api/routes/chat.py)
- [orchestrator.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/orchestrator.py)
- [persona_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/persona_service.py)
- [ollama_provider.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/llm/ollama_provider.py)

### Why This Is A Real Bug

This is not just "unfinished implementation".
It creates false product behavior:
- tasks are marked completed
- routes claim a model/provider choice
- the assistant response looks successful
- but no inference occurred

This makes debugging and product validation misleading.

### Modification Instruction

Choose one of these and implement it consistently:

#### Option A

Wire the orchestrator to a real provider call.
Minimum acceptable path:
- instantiate an LLM provider in the runtime container
- route chat through that provider
- include model/provider used in task output
- fail honestly if provider is unavailable

#### Option B

If provider-backed inference is not ready yet, make the runtime explicitly return a degraded or stub state.
Do not mark it as a successful model-backed assistant response.

If using Option B, the response must clearly indicate:
- no provider call occurred
- this is scaffold behavior
- task status should not imply real model completion

### Additional Constraint

Do not hard-code Ollama calls directly inside route handlers.
Provider invocation belongs in orchestration or a dedicated model execution layer.

## 2. Screenshot Privacy Policy Is Violated

### Problem

`/events/screenshot-captured` analyzes and stores screenshot summaries before enforcing policy checks.
This violates the runtime policy and privacy design.

Relevant files:
- [events.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/api/routes/events.py)
- [core/config.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/core/config.py)
- [runtime-policy.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/runtime-policy.md)

### Why This Is A Real Bug

Even if the system later decides not to proactively speak, the sensitive content has already been:
- analyzed
- normalized into state
- stored in `WorldState`

That defeats the intended privacy boundary.

### Modification Instruction

Move policy enforcement ahead of screenshot analysis.
Before calling `ScreenshotAnalyzer.analyze(...)`, check at least:
- `screenshot_enabled`
- whether the active app is blacklisted
- whether the current scene is allowed to be ingested

If blocked:
- do not analyze the screenshot
- do not store a screenshot summary
- return an explicit policy-blocked result

### Additional Constraint

Do not bury this policy in prompt logic.
It must remain runtime code.

## 3. Proactive Cooldown Is Broken

### Problem

`PresenceService.should_consider_proactive_message(...)` can return `True`, but the cooldown timestamp is never updated because `mark_proactive_emitted(...)` is never called.

Relevant files:
- [presence_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/presence_service.py)
- [events.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/api/routes/events.py)

### Why This Is A Real Bug

The runtime policy explicitly depends on cooldown and interruption control.
Without state update, repeated screenshot events can repeatedly pass the same proactive gate.

### Modification Instruction

Decide the intended semantics and implement them explicitly:

- if `proactive_considered` means only "eligible", then do not treat it as a cooldown-consuming event
- if the runtime actually emits a proactive message, call `mark_proactive_emitted(...)`

Better structure:
- separate `eligible_for_proactive` from `proactive_message_emitted`
- only consume cooldown when a message is truly emitted

## 4. Routing Metadata Lies About Tool Use

### Problem

`RoutingService.choose_for_chat()` claims `use_tools=True` for non-image chat.
The orchestrator never invokes tools and never checks a tool registry.

Relevant files:
- [routing_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/routing_service.py)
- [orchestrator.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/orchestrator.py)
- [registry.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/tools/registry.py)

### Why This Is A Real Bug

Route metadata should reflect actual execution decisions.
Right now it creates misleading state and will confuse UI, logs, and future debugging.

### Modification Instruction

Pick one:
- either implement actual tool planning/execution for chat
- or set `use_tools=False` until that path is real

Preferred near-term fix:
- make route metadata conservative and truthful
- only set `use_tools=True` when a real tool path exists in orchestration

## 5. Desktop WebSocket Assumption Is Broken

### Problem

The desktop app always attempts to connect to `ws://127.0.0.1:8000/api/v1/ws`, but the runtime defines no such route.

Relevant files:
- [runtimeSocket.ts](/Volumes/zcan mac/nyatter/ayria/apps/desktop/src/lib/ws/runtimeSocket.ts)
- [main.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/main.py)

### Why This Is A Real Bug

This creates guaranteed connection errors and trains the UI around a transport that does not exist.
That is worse than leaving the feature absent.

### Modification Instruction

Choose one:

#### Option A

Implement a minimal WebSocket endpoint in the runtime and document which events it emits.

#### Option B

If WebSocket is not ready, disable connection attempts in the desktop app and surface that event streaming is not yet enabled.

Do not leave a guaranteed-failing connection path in startup code.

## 6. Tests Are Missing In Practice

### Problem

The only runtime test is a placeholder.
There is no meaningful test coverage for:
- chat route behavior
- world state mutation
- screenshot policy gating
- proactive cooldown behavior
- config update behavior

Relevant file:
- [test_health_placeholder.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/tests/unit/test_health_placeholder.py)

### Why This Is A Real Bug

The current defects are straightforward enough that even a few basic tests would have caught them.

### Modification Instruction

Replace placeholder tests with real tests for at least:
- `GET /api/v1/health`
- `POST /api/v1/chat/send`
- `POST /api/v1/events/window-changed`
- `POST /api/v1/events/screenshot-captured` under allowed and blocked conditions
- `PresenceService.should_consider_proactive_message(...)`
- config updates changing runtime behavior

### Additional Constraint

Do not write tests that simply snapshot current incorrect behavior.
Tests should encode intended policy and truthful execution semantics.

## 7. Additional Cleanups Required

These are not the top blockers, but should be addressed while touching the affected areas.

### 7.1 Remove misleading artifact files from normal source review flow

Current tree includes:
- `dist/`
- `node_modules/`
- `__pycache__/`
- generated egg-info

These do not belong in architecture review focus.
If you are preparing the repo for continued implementation, ensure generated artifacts are ignored and not treated as source.

### 7.2 Review mutable default patterns

These files still use direct list defaults in some Pydantic models:
- [memory.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/memory.py)
- [world_state.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/world_state.py)

Even if Pydantic handles some copying safely, prefer `Field(default_factory=list)` consistently for clarity and future-proofing.

### 7.3 Make provider naming consistent

Config defaults and routing defaults use different model casing styles:
- `Qwen3.5-0.8B`
- `qwen2.5-vl-3b`
- `qwen3.5-9b`

Normalize naming conventions so UI, config, and provider integration do not drift.

## 8. Expected Deliverable From The Next Agent

Do not just patch code silently.
After making changes, report back with:

1. what was changed
2. which architectural rule each change was protecting
3. whether the runtime now performs real provider inference or still uses a declared stub mode
4. how screenshot policy is enforced before ingestion
5. whether proactive cooldown now consumes only on real emission
6. whether WebSocket is implemented or intentionally disabled
7. which tests were added

## 9. Final Direction

The correct short-term goal is not feature breadth.
The correct short-term goal is to make v1 truthful.

Truthful means:
- a provider call is either real or explicitly declared absent
- a privacy rule is enforced before sensitive ingestion
- a cooldown rule actually changes runtime state
- route metadata matches execution reality
- transports that do not exist are not presented as live
