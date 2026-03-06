# ayria Architecture V1

## Purpose

This document translates the PM-facing architecture into engineering-facing implementation guidance.
Use it together with the scaffold comments in `apps/`.

## Core Principle

ayria is a desktop presence system with chat capability, not a chat product with a few desktop hooks.
The architecture must preserve that distinction.

Related documents:
- `event-protocol.md`
- `api-contracts.md`
- `tooling-strategy.md`
- `mcp-strategy.md`
- `skill-system.md`
- `structure-enforced-architecture.md`
- `privacy-boundaries.md`
- `runtime-policy.md`

## Runtime Loop

The product should eventually operate as a loop, not a single request handler:

1. ingest input or environmental signal
2. normalize the signal into a domain event
3. update world state
4. decide whether to respond, observe, wait, or ask for confirmation
5. execute the selected task path
6. emit user-visible and system-visible events
7. persist only what policy allows

## System Layers

### Desktop Shell

Primary concerns:
- windows and panels
- system affordances
- user control and privacy controls
- rendering of message and task state

### Presence and Watchers

Primary concerns:
- active window detection
- idle detection
- screenshot capture policy
- clipboard policy
- app blacklist enforcement

### Runtime Orchestration

Primary concerns:
- event intake
- task lifecycle
- route selection
- capability/persona sequencing
- cooldown and interruption logic

### Model Layer

Primary concerns:
- provider abstraction
- local-first routing
- optional cloud fallback
- multimodal prompt packaging

### Memory Layer

Primary concerns:
- inspectable memory
- explicit retention
- deletion support
- retrieval for current context only when relevant

## Product-Critical Architectural Themes

### Tools Are Product Surface, Not Hidden Helpers

The system must visibly model tools and tool policies.
This matters because much of the product value comes from the feeling that `ayria`
can read, search, inspect, and assist within the user's real context.

### MCP Is an Enrichment Layer

MCP should expand capability without owning product identity.
Core runtime responsibilities such as presence, world state, privacy, and
persona sequencing must remain first-party logic.

### Skills Are Named Behavior Packages

The product should eventually expose a small number of structured skills rather
than allowing every behavior to emerge implicitly from prompts.
This supports better UI, better routing, and clearer permission boundaries.

### File Structure Must Reinforce Core Ideas

Presence, world state, persona separation, tools, and skill concepts should all
be visible in the repository layout so weaker contributors do not accidentally
flatten the system into a generic chat stack.

## Capability and Persona Separation

The most important architectural boundary is between:

- capability output
- persona rendering

Capability should decide:
- what happened
- what is true
- whether a tool is needed
- what structured result to produce

Persona should decide:
- tone
- warmth
- degree of character expression
- whether a follow-up question feels natural

Persona must not decide:
- which tool to call
- whether a fact is true
- whether hidden context should be exposed

## Recommended Initial Event Sources

V1 event sources should stay small:
- desktop user message
- active window changed
- screenshot captured
- user idle
- user returned
- config updated

Avoid adding too many sensors early. Too many raw inputs will create a noisy system that is harder to debug.

## Recommended Task Types

Keep task taxonomy stable and explicit:
- chat reply
- screenshot analysis
- proactive suggestion
- tool execution
- memory extraction
- reflection or evaluation

## Recommended Debug Surfaces

The desktop app should expose a debug drawer or page with:
- last 20 domain events
- current world state
- current provider route
- current task list
- last screenshot summary
- memory retrieval results for current turn

A presence system is difficult to build without transparent debugging.
