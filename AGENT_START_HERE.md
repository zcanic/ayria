# AGENT_START_HERE

This file is the handoff entrypoint for agents continuing work on `ayria`.
Read this before making changes.

## 1. Project Identity

`ayria` is a local-first desktop presence system.
It is not a plain chat application.

Core product idea:
- desktop presence
- world-state awareness
- controlled proactive behavior
- local-first model usage
- capability/persona separation
- explicit tools, permissions, and privacy boundaries

If your implementation starts to look like "a chat endpoint plus some helpers", you are drifting away from the intended architecture.

## 2. Repository Layout

The repository root contains:
- this handoff file
- original PM research and feasibility notes
- the `ayria/` project scaffold

Primary working area:
- [ayria](/Volumes/zcan mac/nyatter/ayria)

Original PM-level design document:
- [ayria-架构设计与可行性研究.md](/Volumes/zcan mac/nyatter/ayria-架构设计与可行性研究.md)

## 3. Read In This Order

1. [ayria/README.md](/Volumes/zcan mac/nyatter/ayria/README.md)
2. [ayria-架构设计与可行性研究.md](/Volumes/zcan mac/nyatter/ayria-架构设计与可行性研究.md)
3. [ayria-architecture-v1.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/ayria-architecture-v1.md)
4. [runtime-policy.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/runtime-policy.md)
5. [engineering-handoff.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/engineering-handoff.md)
6. [tooling-strategy.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/tooling-strategy.md)
7. [mcp-strategy.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/mcp-strategy.md)
8. [skill-system.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/skill-system.md)
9. [structure-enforced-architecture.md](/Volumes/zcan mac/nyatter/ayria/docs/architecture/structure-enforced-architecture.md)
10. [evals/README.md](/Volumes/zcan mac/nyatter/ayria/evals/README.md)
11. [TEST_APP_SPEC.md](/Volumes/zcan mac/nyatter/ayria/evals/TEST_APP_SPEC.md)
12. Then inspect scaffold files under `ayria/apps/runtime` and `ayria/apps/desktop`

## 4. Non-Negotiable Architectural Rules

These rules should be treated as hard constraints.

### Rule 1

Do not collapse the system into a single chat app architecture.
The system is intentionally split into:
- desktop shell
- presence/context collection
- runtime orchestration
- provider/model layer
- persona rewrite layer
- memory/storage layer

### Rule 2

Keep capability and persona separate.

Capability decides:
- facts
- tools
- structured outputs
- scene understanding

Persona decides:
- tone
- warmth
- character flavor
- final presentation style

Persona must not decide:
- tool usage
- hidden facts
- privacy overrides

### Rule 3

Treat `WorldState` as a first-class product concept.
Do not rely only on message history.

### Rule 4

Treat tools as explicit product surfaces.
Do not hide them inside ad hoc helper code.

### Rule 5

Treat MCP as an integration layer, not as the system core.
Presence, privacy, world-state construction, and runtime policy remain first-party responsibilities.

### Rule 6

Do not make LoRA a v1 dependency.
Prompt shaping and persona rewrite come first.

## 5. Product-Critical Concepts

### Presence

The assistant should feel present but not invasive.
This means:
- controlled observation
- visible state
- careful proactive behavior
- interruption discipline

### Runtime Policy

A large part of product quality depends on runtime policy, not model cleverness.
That includes:
- when to speak
- when to stay silent
- when to ask permission
- when to route local vs cloud
- what should become memory

### Tooling

The tool strategy is part of the PM design, not just backend implementation.
The first important classes are:
- perception tools
- knowledge tools
- workspace tools
- action tools
- reflection tools

### Skills

Skills are planned as structured behavior packages, not just prompt variants.
Even if not fully implemented yet, preserve room for this concept.

## 6. Where To Look In Code

### Desktop shell
- [App.tsx](/Volumes/zcan mac/nyatter/ayria/apps/desktop/src/app/App.tsx)
- [ChatPanel.tsx](/Volumes/zcan mac/nyatter/ayria/apps/desktop/src/features/chat/ChatPanel.tsx)
- [PresenceBadge.tsx](/Volumes/zcan mac/nyatter/ayria/apps/desktop/src/features/presence/PresenceBadge.tsx)
- [client.ts](/Volumes/zcan mac/nyatter/ayria/apps/desktop/src/lib/api/client.ts)
- [runtimeSocket.ts](/Volumes/zcan mac/nyatter/ayria/apps/desktop/src/lib/ws/runtimeSocket.ts)

### Runtime entry and routes
- [main.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/main.py)
- [health.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/api/routes/health.py)
- [chat.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/api/routes/chat.py)
- [events.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/api/routes/events.py)

### Runtime domain core
- [orchestrator.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/orchestrator.py)
- [presence_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/presence_service.py)
- [context_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/context_service.py)
- [persona_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/persona_service.py)
- [routing_service.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/services/routing_service.py)

### Runtime domain models
- [world_state.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/world_state.py)
- [task.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/task.py)
- [message.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/message.py)
- [memory.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/memory.py)
- [tool.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/domain/models/tool.py)

### Model and tool integration
- [base.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/llm/base.py)
- [ollama_provider.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/llm/ollama_provider.py)
- [mlx_provider.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/llm/mlx_provider.py)
- [mcp_bridge.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/tools/mcp_bridge.py)
- [screenshot_analyzer.py](/Volumes/zcan mac/nyatter/ayria/apps/runtime/app/providers/vision/screenshot_analyzer.py)

## 7. Recommended Development Priorities

If you are the next agent and need a default path, use this order:

1. preserve architecture and comments
2. preserve runtime policy boundaries
3. preserve capability/persona separation
4. preserve world-state-first thinking
5. only then add implementation detail

Practical sequence:
1. make the runtime boot cleanly
2. make the desktop shell render a minimal surface
3. connect health and debug state
4. expose world state visibly in UI
5. add one provider cleanly
6. add screenshot analysis with policy controls
7. add persona rewrite after capability flow is stable

## 8. Common Ways To Damage The Architecture

Avoid these mistakes:

- putting core business logic in route handlers
- mixing persona instructions into capability prompts
- hard-coding provider-specific logic all over the runtime
- making every perception step a model-triggered tool call
- letting MCP define the product structure
- hiding sensitive actions from the UI
- treating memory as invisible magic
- turning proactive behavior into spam

## 9. What Is Already Done

Already produced in this repository:
- PM-level feasibility and architecture research
- scaffolded monorepo under `ayria/`
- detailed comments in key scaffold files
- architecture docs for event protocol, API contracts, prompt policy, privacy, runtime policy, tool strategy, MCP strategy, skill strategy, and handoff guidance
- a standardized eval/test-app spec and scenario skeletons under `ayria/evals`
- runtime now includes `ModelExecutionService` with explicit stub/live mode semantics
- runtime now includes a real Ollama adapter path for local inference work
- in scaffold defaults, provider execution is intentionally non-live and reported as such

## 10. What Is Intentionally Not Done Yet

Not done on purpose:
- no real feature implementation
- no real WebSocket server
- no real database layer
- no LoRA work
- no final skill registry implementation

These are deferred so implementation agents inherit a coherent structure first.

## 11. Final Reminder

The success condition is not "make the model answer".
The success condition is:
- make `ayria` feel like a trustworthy desktop presence system
- make its behavior explainable
- make its architecture resilient to weaker future contributors
