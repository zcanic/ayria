# MCP Strategy

## Positioning

MCP should be treated as an integration layer, not as the core architecture.

That means:
- `ayria` should remain coherent even if no MCP server is connected
- MCP should enrich the system, not define the system
- core product capabilities should not depend on fragile third-party MCP behavior

## What MCP Is Good For In ayria

MCP is best used for capabilities that are:
- modular
- replaceable
- externally sourced
- likely to expand over time

Examples:
- workspace search
- code/documentation context providers
- browser control
- app connectors
- knowledge providers

## What Should Not Depend On MCP

The following should remain first-party runtime responsibilities:
- world state construction
- proactive timing and cooldown logic
- persona rewrite
- memory policy
- screenshot policy
- route selection
- privacy enforcement

If these depend on MCP, the product loses internal coherence.

## Recommended MCP Layers

### Layer A: Native Runtime Capability

This is where the most product-critical capabilities live.
Examples:
- presence state
- world state
- screenshot summaries
- memory retrieval
- route decisions

### Layer B: MCP-Adapted Tool Capability

This is where interchangeable integrations live.
Examples:
- grep or code search
- browser actions
- documentation context
- external knowledge connectors

### Layer C: Experimental MCP Capability

This is where optional or unstable integrations live.
Examples:
- niche app connectors
- advanced automation servers
- research or prototype-only tools

## Initial MCP Recommendation

For early development, plan for these MCP families:

- workspace/file context
- browser and web interaction
- documentation lookup
- maybe specialized code intelligence

Concrete examples of likely future MCP classes:
- `filesystem`
- `grep_app` or equivalent workspace search
- `context7` or equivalent docs/reference retrieval
- browser control or devtools bridge

## Operational Rule

MCP tools should be normalized into internal `ToolSpec` records.
The rest of the runtime should not care whether a tool came from:
- native Python code
- an MCP server
- an HTTP microservice

## PM-Level Risk Notes

### Risk 1: MCP Sprawl

Too many connected MCP servers can make the product feel random and uncontrollable.

Mitigation:
- maintain a curated allowlist
- group tools by product-facing capability
- do not expose every MCP tool to every model prompt

### Risk 2: Explainability Loss

Users may not understand why the assistant did something if MCP tool usage is invisible.

Mitigation:
- show tool activity in UI
- keep tool names human-readable
- surface source and permission context

### Risk 3: Architecture Inversion

A team may be tempted to let MCP define the product because it is easy to bolt on tools.

Mitigation:
- preserve first-party runtime ownership of presence, memory, and orchestration
