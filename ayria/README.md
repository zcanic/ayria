# ayria

`ayria` is a local-first desktop presence system.

This repository is intentionally scaffolded with heavy comments. The goal is to let a weaker coding agent or a junior engineer continue implementation without needing to rediscover the architecture.

## Product Shape

`ayria` is not a plain chat bot.
It should eventually:

- live on the desktop as a persistent companion
- observe desktop context with explicit user controls
- maintain a `WorldState`
- decide when to stay quiet and when to speak
- use local models first, with optional cloud fallback
- separate capability reasoning from persona rendering

## Current State

This repo is a scaffold, not a running product.
What exists now:

- monorepo layout
- desktop app skeleton
- python runtime skeleton
- shared schema placeholders
- detailed comments that explain implementation intent

Default runtime mode is scaffold mode: `provider_stub_mode=true` in runtime config.
The runtime now includes a real Ollama adapter path for local inference work.
That live path has been smoke-tested against local `Ollama` using `qwen3.5:0.8b`.
The runtime now also includes:
- a real websocket event stream
- a controlled tool execution route
- a standardized eval runner with scenario/result schema validation
Stub mode remains the default so contributors can distinguish clearly between:
- scaffold behavior
- truthful provider errors
- actual local inference through Ollama

## Main Architectural Rule

Do not collapse the system into a single chat endpoint.
The system is split into:

1. desktop shell
2. presence and context collection
3. runtime orchestration
4. model providers
5. persona rewrite
6. memory and storage

Additional non-negotiable architectural rules:

- capability and persona stay separate
- tools are explicit and inspectable
- MCP is an integration layer, not the product core
- world state matters more than raw message history
- skills should eventually be structured, not just hidden in prompts

## Suggested Development Order

1. Get the Python runtime booting with `/api/v1/health`.
2. Get the desktop shell rendering a basic chat window.
3. Connect desktop to runtime over HTTP + WebSocket.
4. Add a stub `WorldState` endpoint and render it in the UI.
5. Add one model provider adapter, preferably `Ollama`.
6. Add screenshot analysis as a controlled pipeline.
7. Add persona rewrite only after the capability pipeline is stable.

## Important Constraint

Do not add LoRA support first.
LoRA is not a v1 requirement. Prompt shaping and persona rewrite come first.

## Important Docs

Start with:

- `docs/architecture/ayria-architecture-v1.md`
- `docs/architecture/engineering-handoff.md`
- `docs/architecture/tooling-strategy.md`
- `docs/architecture/mcp-strategy.md`
- `docs/architecture/skill-system.md`
- `docs/architecture/structure-enforced-architecture.md`
- `docs/architecture/runtime-policy.md`

For reproducible evaluation work, also read:

- `evals/README.md`
- `evals/TEST_APP_SPEC.md`
