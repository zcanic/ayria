# Skill System Strategy

## Why ayria Needs a Skill Concept

A plain tool gives the model a narrow action.
A skill gives the system a reusable mode of work.

For `ayria`, this distinction matters because the product is not only trying to answer questions.
It is trying to participate in recurring situations:
- reading code
- summarizing articles
- helping with research
- reviewing screenshots
- assisting during focused work

A skill should therefore be understood as:
- a named behavioral package
- with tool preferences
- with prompt framing
- with output style constraints
- sometimes with UI affordances

## Difference Between Tool and Skill

Tool:
- atomic capability
- e.g. `read_file`, `web_search`, `read_clipboard`

Skill:
- orchestrated pattern of behavior
- e.g. `research_assistant`, `code_reader`, `article_companion`, `debug_partner`

A skill may use multiple tools.
A tool should not contain an entire skill.

## Recommended V1 Skills

### 1. Screen Reader

Purpose:
- help the user understand what is currently on screen

Likely ingredients:
- screenshot analysis
- active window summary
- selected text or clipboard

### 2. Research Companion

Purpose:
- help compare sources, summarize findings, track questions

Likely ingredients:
- web search
- URL summarization
- memory of current research thread

### 3. Code Reading Partner

Purpose:
- discuss the current repository or file context without acting like a detached chat bot

Likely ingredients:
- file reader
- grep/workspace search
- screenshot context
- project-local memory

### 4. Writing Companion

Purpose:
- help rewrite, tone-shift, summarize, or expand text in the user's active workflow

Likely ingredients:
- selected text
- clipboard read
- file reader
- persona-aware rewrite style

## Skill Representation

A skill should be structured, not implied only by prompt prose.
Each skill should eventually have:
- skill id
- user-facing label
- description
- allowed tools
- preferred prompt template(s)
- preferred output style
- optional trigger conditions
- optional cooldown behavior

## Why Structure Matters

If skills are only prompt text, the system cannot:
- inspect or debug them clearly
- show them in UI
- reason about permissions cleanly
- route tasks consistently

Skills need explicit representation in files and config.

## Recommended File Layout

Skills should eventually live under a dedicated runtime area, for example:

- `apps/runtime/app/skills/definitions/`
- `apps/runtime/app/skills/registry.py`
- `apps/runtime/app/skills/policies/`

Even if implementation is delayed, the architecture should reserve this concept.

## PM Guidance

Do not launch with too many named skills.
Too many modes create product confusion.

The right V1 skill count is likely between 3 and 5.
Enough to shape behavior, not enough to feel like a confusing mode picker.
