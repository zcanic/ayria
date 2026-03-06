# Structure-Enforced Architecture

## Why This Matters

Some architectural ideas are too important to leave as "team conventions".
They need to be reflected directly in file structure, naming, and module boundaries.

For `ayria`, this is especially important because a weaker engineer or agent may otherwise collapse the product into a generic chat stack.

## Architectural Ideas That Must Be Visible In Structure

### 1. Presence Is First-Class

This must appear in the repository structure.
There should be explicit modules for:
- presence service
- event ingress
- world state
- screenshot analysis

Why:
If presence is not visible in structure, it will be treated as an afterthought.

### 2. Capability and Persona Are Separate

This must appear in:
- separate services
- separate prompt files
- separate agent modules
- separate route decisions where relevant

Why:
If this separation becomes only conceptual, it will erode during implementation.

### 3. Tools Are an Explicit Product Surface

This must appear in:
- a dedicated tool registry
- tool schemas
- MCP bridge modules
- UI-visible task or tool activity events

Why:
If tools are hidden in ad hoc helper functions, the system becomes impossible to reason about.

### 4. World State Is the Product Brain, Not Just Message History

This must appear in:
- dedicated `world_state` models
- dedicated repositories or state services
- debug routes and UI panels

Why:
A desktop presence system must think in scenes and context, not only in message turns.

### 5. Skills Are Reusable Behavior Packages

This should eventually appear in:
- dedicated skill definitions
- skill registry
- skill selection or routing layer

Why:
Without explicit skill structure, recurring behaviors become prompt spaghetti.

## Recommended Structural Additions

The current scaffold can later add these directories without changing the core idea:

```text
apps/runtime/app/
  skills/
    definitions/
    policies/
    registry.py
  policies/
    privacy_policy.py
    proactive_policy.py
    retention_policy.py
  state/
    world_state_manager.py
    event_bus.py
    task_bus.py
  evaluators/
    proactive_evaluator.py
    privacy_evaluator.py
```

## Design Rule

If an important product concept cannot be pointed to in the file tree, it is at risk of being under-implemented.

## PM Checklist

Ask these questions periodically:
- Can a new engineer find where proactive behavior lives?
- Can they find where privacy rules live?
- Can they find where persona is separated from capability?
- Can they find where world state is built?
- Can they find where tool permissions are enforced?

If not, the architecture is not explicit enough.
