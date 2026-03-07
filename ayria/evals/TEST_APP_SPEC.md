# Standardized Test App Spec

This document defines the PM-level requirements for a reusable evaluation app
for `ayria`.

This is not the production desktop shell.
This is a controlled test application that exists to make changes measurable.

## Product Name

Working name:
- `ayria-eval-app`

## Objective

Provide a single standard harness that can:

- load fixed scenarios
- drive the runtime with controlled inputs
- capture structured outputs
- score results deterministically where possible
- save historical artifacts for regression comparison

## Non-Goals

The eval app is not meant to:

- replace unit tests
- replace manual UX review
- simulate the full desktop product perfectly
- hide runtime failures behind pretty dashboards

## Required Modes

The eval app should support at least these modes.

### 1. provider mode

Purpose:
- verify provider reachability
- verify installed model inventory
- verify truthful error surfaces

### 2. api mode

Purpose:
- hit runtime HTTP endpoints using fixed payloads
- validate response schema and semantic status

### 3. scenario mode

Purpose:
- load a scenario manifest
- apply runtime config overrides
- send the ordered event/message sequence
- collect outputs
- score the run

## Required Inputs

Each run must be driven by a scenario manifest, not by ad hoc CLI arguments
alone.

Each scenario must define:

- `scenario_id`
- `scenario_version`
- `purpose`
- `runtime_mode`
- `provider`
- `model`
- `config_overrides`
- `fixture_refs`
- `steps`
- `scoring`

## Required Outputs

Each run must emit a single structured result document with:

- run metadata
- environment metadata
- scenario metadata
- raw step outputs
- normalized score summary
- pass/fail decision
- notes for non-deterministic interpretation

## Scoring Classes

The eval app should support multiple score types.

### exact_match

For responses that must equal a known string.

Use cases:
- smoke prompts
- install guidance messages
- route contract sanity checks

### substring_match

For truthful error messages where exact wording may evolve but required key
content must remain.

Use cases:
- missing model install instructions
- provider unavailability messages

### schema_match

For API responses that must preserve required keys and shapes.

Use cases:
- `/chat/send`
- `/health/providers`
- `/providers`

### policy_assertion

For runtime-policy checks.

Use cases:
- screenshot blocked before ingestion
- proactive cooldown enforced
- blacklisted app suppression

### latency_budget

For non-functional constraints.

Use cases:
- exact chat smoke must finish under a configured threshold
- provider health probe must finish under a configured threshold

## Core Architecture

The eval app should be structured as:

1. `scenario loader`
2. `fixture resolver`
3. `runtime client`
4. `step runner`
5. `scorer`
6. `result writer`

Do not collapse scoring into the runner.
Do not bury scenario meaning inside code branches.

## File Placement

Recommended future code layout:

- `apps/eval-app/`
- `apps/eval-app/src/scenarios/`
- `apps/eval-app/src/scorers/`
- `apps/eval-app/src/runtime-client/`
- `apps/eval-app/src/result-writer/`

If the first implementation is done in Python, keep the logical layout the
same under `apps/runtime-eval/`.

## Result Storage Rule

Results should be written to a versioned folder structure:

- `evals/results/<scenario_id>/<timestamp>__<short_commit>.json`

Optional additional files:

- human-readable markdown summary
- raw response payload dump
- system metadata dump

## Determinism Rules

Where possible, exact-match scenarios should use:

- `provider_stub_mode=false`
- fixed local provider
- fixed model
- fixed prompt
- fixed runtime config
- persona rewrite disabled or neutralized
- no screenshot or ambient event noise unless required by the scenario

If determinism cannot be guaranteed, the scenario must declare why and how it
should be interpreted.

## Acceptance Criteria For v1 Eval App

The first usable version of the eval app is good enough if it can:

1. load scenario JSON
2. call runtime HTTP endpoints
3. save result JSON
4. compute exact-match and substring-match scores
5. print a one-line pass/fail summary
6. support at least two scenarios from this directory

## PM Direction

The eval app should become part of normal development discipline.

A claimed improvement to local inference, runtime policy, or provider behavior
is weak unless it is backed by at least one standardized scenario result.
