# Tooling Strategy

## Why Tooling Is Central

For `ayria`, tools are not an accessory.
They are part of the illusion of presence and usefulness.
A companion that can only chat will quickly feel fake.
A companion that can see, read, search, and act with restraint will feel materially more real.

The product goal is not "maximum tool count".
The goal is "the right tools, exposed through the right layers, with explicit user trust boundaries".

## Product-Level Tool Taxonomy

Tools should be grouped by the user mental model, not just by implementation.

### 1. Perception Tools

These let `ayria` understand the current environment.

Examples:
- active window reader
- screenshot capture request
- screenshot analysis
- clipboard reader
- selected text reader
- OCR helper

Product role:
- supports fourth-wall breaking presence
- answers "what is the user looking at right now"
- powers scene-aware assistance

### 2. Knowledge Tools

These let `ayria` bring in external knowledge or structured references.

Examples:
- web search
- URL fetch and summarization
- documentation lookup
- local knowledge base lookup
- memory retrieval

Product role:
- avoids the assistant becoming a closed bubble
- supports answer grounding and up-to-date information
- helps the assistant pivot from social companion to useful collaborator

### 3. Workspace Tools

These let `ayria` understand and work with the user's local project or files.

Examples:
- file reader
- repository grep
- symbol search
- directory listing
- structured file metadata lookup
- current project context summarizer

Product role:
- supports coding and reading assistance
- makes `ayria` feel embedded in the user's actual workspace
- is critical if the assistant is expected to discuss the file currently open on screen

### 4. Action Tools

These let `ayria` do something rather than only explain something.

Examples:
- open file
- open URL
- copy generated text to clipboard
- create note or task item
- desktop automation hooks

Product role:
- turns the system from passive commentator into assistant
- must be tightly permissioned

### 5. Reflection Tools

These are internal-facing tools for better orchestration quality.

Examples:
- memory candidate extraction
- response evaluator
- route debug recorder
- conversation summarizer

Product role:
- improves consistency, quality, and explainability
- usually not exposed to the user directly as tools

## V1 Tool Recommendation

V1 should not try to expose every category deeply.
The first useful tool set should be:

- active window summary
- screenshot capture trigger and screenshot analysis
- clipboard read
- file reader
- web search
- memory lookup

That is enough to support the product fantasy without drowning in permissions and orchestration complexity.

## Tool Design Rules

### Rule 1

Tools should be first-class product surfaces.
The user should usually be able to see that a tool was invoked or that a certain capability required system access.

### Rule 2

Tools should be typed and inspectable.
Every tool should have:
- name
- purpose
- input schema
- permission policy
- timeout policy
- visibility policy

### Rule 3

Tools should not leak backend transport concepts upward.
The orchestrator should ask for a capability like `web_search` or `read_file`, not care whether it is backed by MCP or a local adapter.

### Rule 4

Not every capability should be model-driven.
Some perception steps may be deterministic pipeline steps instead of tool calls exposed to the model.
For example, screenshot analysis may be orchestrator-driven rather than model-requested.

## Which Tools Need MCP

Not all tools should be MCP-backed.

Good MCP candidates:
- filesystem and workspace search
- browser automation
- documentation lookup servers
- specialized code intelligence services
- external app integrations

Not ideal as pure MCP first:
- presence state
- idle state
- internal memory retrieval
- local task state
- screenshot cooldown policy

Reason:
These are core runtime responsibilities and should remain native to the system.

## PM Guidance for Prioritization

If there is pressure to add more tools, apply this filter:

1. Does it improve the fourth-wall presence illusion?
2. Does it improve actual usefulness in the current desktop context?
3. Can it be permissioned clearly?
4. Can the UI explain when it is used?
5. Will it destabilize the orchestration if added too early?

If the answer to 1 and 2 is weak, the tool is probably not a priority.
