# Prompt Policy

## Purpose

Prompt files in `apps/runtime/app/prompts` are product logic.
Treat them like code.

## Prompt Layers

### Capability Prompt

Responsibilities:
- grounded reasoning
- structured outputs
- tool discipline
- uncertainty signaling

### Persona Prompt

Responsibilities:
- style and warmth
- role flavor
- preserving meaning
- avoiding contradiction with capability output

### Proactive Prompt

Responsibilities:
- short suggestions
- low interruption
- humility about partial observation

## Editing Rules

When editing prompts:
- change one thing at a time
- note the reason in commit messages or changelog
- evaluate with explicit test cases
- do not mix tool schema changes with tone changes in the same edit if avoidable

## Anti-Patterns

Avoid:
- putting persona instructions into capability prompt
- telling the capability prompt to roleplay heavily
- hiding safety-critical routing logic in prompt prose
- relying on prompts to enforce privacy policy without code support

## Desired Output Discipline

Capability layer should prefer outputs that can be parsed or normalized into:
- summary
- answer
- uncertainty
- tool instructions
- scene classification
- next-step suggestions
