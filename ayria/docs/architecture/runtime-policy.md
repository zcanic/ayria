# Runtime Policy

## Purpose

This document defines the behavioral policy layer for `ayria`.
It exists to stop the runtime from drifting into inconsistent or overly clever behavior.

The runtime is not only a technical coordinator.
It is the product's behavioral governor.

This document should be treated as an implementation constraint for:
- orchestrator logic
- presence logic
- routing logic
- tool invocation logic
- memory logic
- cloud fallback logic

## Policy Design Principle

The product should prefer behavior that is:
- legible
- predictable
- local-first
- privacy-preserving
- interrupt-light
- honest about uncertainty

If there is a choice between "more magical" and "more trustworthy", prefer trustworthy.

## 1. Response Policy

### 1.1 Response Modes

The runtime should explicitly classify each turn or event into one of these response modes:

- `respond_now`
- `suggest_lightly`
- `observe_only`
- `defer`
- `ask_permission`
- `stay_silent`

This should be a real runtime concept, not just a vague internal idea.

### 1.2 When To Respond Immediately

Typical triggers:
- explicit user message
- direct user question about current screen or file
- user-approved task execution
- clarification requested by the system

### 1.3 When To Suggest Lightly

Typical triggers:
- user appears stuck or repeating failed attempts
- user has been reading a long document for a while
- screenshot analysis suggests a confusing or dense interface
- a tool result strongly suggests a useful next step

Suggested output form:
- one short sentence
- optional follow-up question
- easy to ignore

### 1.4 When To Observe Only

Typical triggers:
- a window switch that provides context but does not merit interruption
- a screenshot update taken for state maintenance
- clipboard change without user request

### 1.5 When To Stay Silent

Typical triggers:
- user is actively typing
- current app is blacklisted
- recent proactive cooldown is active
- system confidence is low
- scene relevance is weak

## 2. Proactive Behavior Policy

### 2.1 Core Rule

Proactive behavior is allowed only when it improves perceived support without feeling like surveillance or interruption.

### 2.2 Cooldown

The runtime should maintain at least:
- global proactive cooldown
- per-scene-type cooldown
- repeated-topic suppression

Meaning:
- do not comment on every window switch
- do not repeat the same suggestion in slightly different words
- do not trigger multiple proactive suggestions from one noisy observation burst

### 2.3 Interruption Budget

The runtime should conceptually maintain an interruption budget.
High interruption cost scenarios include:
- coding in active typing bursts
- game or full-screen activity
- rapid application switching
- repeated dismissals of prior proactive suggestions

In these scenarios, bias toward `observe_only` or `stay_silent`.

### 2.4 Confidence Threshold

A proactive message should usually require:
- meaningful scene confidence
- some confidence in likely user need
- low interruption risk

If only one of these is true, do not proactively speak.

## 3. Privacy Policy

### 3.1 Local-First Default

The runtime should assume that observations and model calls stay local unless the user has explicitly enabled cloud fallback for the relevant scenario.

### 3.2 Sensitive Observation Classes

The runtime should treat the following as sensitive by default:
- clipboard contents
- screenshots
- selected text
- local file contents
- browser pages with account or payment context

### 3.3 Blacklisted Contexts

When the active app or scene is blacklisted:
- do not capture screenshots
- do not summarize content
- do not create memory items from that context
- do not send related context to cloud models

### 3.4 Visibility Rule

If a sensitive capability is used, the UI should eventually make that legible.
Examples:
- screenshot analyzed
- clipboard read
- cloud model used
- local file read

## 4. Cloud Fallback Policy

### 4.1 Why Fallback Exists

Cloud fallback exists to cover tasks that exceed local model quality or reliability, not to quietly become the default path.

### 4.2 Allowed Fallback Cases

Typical allowed cases:
- local model repeatedly fails a structured task
- complex multi-step search or synthesis task
- user explicitly requests higher-quality reasoning
- selected premium mode in settings

### 4.3 Disallowed Silent Fallback

The runtime should not silently send the following to the cloud without policy support:
- raw screenshots
- local project files
- clipboard content
- memory items marked sensitive

### 4.4 Fallback Record

Each fallback decision should eventually be recordable as:
- route chosen
- why local was not used or failed
- what content class was sent
- whether the user had allowed that class

## 5. Tool Permission Policy

### 5.1 Tool Permission Classes

Classify tools into at least three permission levels:

- `safe_read`
- `sensitive_read`
- `action_or_external`

Examples:

`safe_read`:
- current active window metadata
- non-sensitive local memory lookup

`sensitive_read`:
- clipboard read
- file read
- screenshot analysis

`action_or_external`:
- web search
- opening links
- desktop automation
- cloud calls that include user content

### 5.2 Permission Behavior

Suggested defaults:
- `safe_read`: allowed by global product policy
- `sensitive_read`: allowed only if feature enabled and context permitted
- `action_or_external`: often needs user-visible trace and sometimes confirmation

### 5.3 Tool Invocation Auditability

Tool usage should be observable in logs and, where product-appropriate, in UI.
A user should not be left guessing whether the system actually opened a file or read the clipboard.

## 6. Memory Policy

### 6.1 Memory Types

Use explicit categories:
- preference
- stable fact
- relationship signal
- recurring workflow pattern
- temporary task context

### 6.2 Memory Creation Rule

A memory item should be created only if it is:
- likely useful later
- not obviously sensitive
- not a fleeting artifact of one scene

### 6.3 Memory Suppression Cases

Do not create durable memory from:
- blacklisted contexts
- likely secrets or credentials
- accidental clipboard exposure
- one-off transient tasks unless clearly reusable

### 6.4 Memory Retrieval Rule

Memory retrieval should support the current task, not drown the model in personal trivia.
If too many memories match, prefer fewer and more relevant items.

## 7. Routing Policy

### 7.1 Route Decision Priorities

When selecting model/provider/tool path, prioritize in this order:

1. privacy and permission constraints
2. task fit
3. local availability
4. reliability
5. latency
6. style quality

This ordering is intentional.
A faster path is not acceptable if it violates privacy policy.

### 7.2 Default Bias

Default route bias should be:
- local provider
- smaller stable model first
- structured path before clever path
- deterministic preprocessing where useful

### 7.3 Vision Policy

Vision should be used when needed, not on every turn.
Screenshot-based context should be an explicit or policy-triggered input, not a permanent hidden dependency.

## 8. Capability vs Persona Policy

### 8.1 Ordering Rule

The runtime should follow this sequence whenever possible:
- capability interpretation
- tool execution if needed
- factual result assembly
- persona rewrite
- optional evaluator

### 8.2 Persona Limitations

Persona layer should not:
- invent hidden observations
- alter tool arguments
- overstate confidence
- override privacy rules

### 8.3 Persona Intensity Adjustments

Persona should soften in these contexts:
- tool-heavy tasks
- sensitive content
- research summaries
- safety-critical or precision-critical explanations

Persona can strengthen in these contexts:
- casual chat
- encouragement
- light proactive suggestions
- companionship moments not tied to strict factual output

## 9. Skill Policy

### 9.1 Skill Selection Principle

A skill should be selected because it matches the user's situation, not because a prompt happened to mention certain words.

### 9.2 Skill Constraints

Each skill should eventually specify:
- preferred tools
- forbidden tools
- preferred response mode
- preferred persona intensity
- typical output length

### 9.3 Skill Override Rule

Privacy and tool permission policy always outrank skill preferences.
A skill may suggest behavior, but policy decides whether that behavior is allowed.

## 10. Failure Policy

### 10.1 Honest Failure

When the runtime lacks enough confidence or permission, it should say so clearly.
It should not fabricate understanding.

### 10.2 Graceful Degradation

If a provider is unavailable:
- keep the desktop app functional
- surface degraded state clearly
- preserve local context where possible
- suggest the next useful fallback instead of failing opaquely

### 10.3 Retry Discipline

Do not blindly retry everything.
Retries should depend on failure class:
- transient provider/network issue: maybe retry
- permission denied: do not retry automatically
- policy blocked: do not retry automatically
- malformed task input: surface and fix upstream

## 11. Debuggability Policy

### 11.1 Every Important Runtime Decision Should Be Explainable

At minimum, the system should eventually be able to expose:
- why it responded or stayed silent
- why it chose a route
- why it used or did not use a tool
- why it stored or did not store memory
- why it used cloud fallback or refused to

### 11.2 No Hidden Magic Rule

If a behavior is too important to explain, it is too important to leave implicit.
Move it into structured policy or explicit state.

## 12. PM Acceptance Checklist

Before a future implementation is considered healthy, ask:
- Can the system explain why it interrupted?
- Can the system explain why it stayed silent?
- Can the user tell when sensitive tools were used?
- Can the system avoid sending sensitive content to cloud fallback by default?
- Can the system keep persona from corrupting capability output?
- Can the system suppress noisy proactive behavior?
- Can the system keep memory creation selective and inspectable?

If several answers are no, the runtime is not following policy strongly enough.
