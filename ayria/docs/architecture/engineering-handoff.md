# Engineering Handoff Guide

## Audience

This guide is for an engineer or weaker coding agent picking up the ayria scaffold.
Read this before making large changes.

## First Files to Read

1. `README.md`
2. `docs/architecture/ayria-architecture-v1.md`
3. `docs/architecture/event-protocol.md`
4. `docs/architecture/api-contracts.md`
5. `apps/runtime/app/main.py`
6. `apps/runtime/app/domain/services/orchestrator.py`
7. `apps/runtime/app/domain/models/world_state.py`

## Mental Model

There are three different concerns in this repo:

- desktop shell and UX
- runtime orchestration and policy
- model/provider execution

Do not merge them mentally or in code.

## What To Build First

### Backend-first track

1. make FastAPI app runnable
2. make `/api/v1/health` work
3. make `/api/v1/chat/send` return accepted tasks
4. add `GET /api/v1/world-state`
5. add one provider adapter

### Frontend-first track

1. render a shell and placeholder chat
2. show runtime connection state
3. call health route
4. render a fake world state panel
5. connect WebSocket placeholders

## Common Failure Modes

### Failure Mode 1

Treating ayria like a normal chat app.

Correction:
- keep `WorldState`, events, tasks, and presence visible in the design

### Failure Mode 2

Letting persona logic creep into capability or tool code.

Correction:
- keep persona in `persona_service.py` and prompt files only

### Failure Mode 3

Hard-coding Ollama or MLX details across the codebase.

Correction:
- isolate provider-specific logic under `providers/llm`

### Failure Mode 4

Triggering proactive messages directly from watchers.

Correction:
- watchers emit events, runtime services decide whether to speak

## Code Placement Rules

If you need to add:

- a new HTTP route: `app/api/routes`
- a new domain model: `app/domain/models`
- orchestration or policy logic: `app/domain/services`
- model provider adapter: `app/providers/llm`
- tool integration: `app/providers/tools`
- prompt text: `app/prompts`
- persistence detail: `app/infra`

## What Not To Optimize Early

Do not optimize these in v1 scaffold work:
- async job queues
- advanced memory ranking
- automatic desktop control
- multi-agent debate systems
- LoRA integration

## Definition of Good Progress

A good step is one that makes the architecture clearer.
Examples:
- adding a stable route contract
- adding a typed event shape
- adding a debug UI panel for world state
- adding explicit provider health reporting

A bad step is one that hides logic in ad hoc code paths.
