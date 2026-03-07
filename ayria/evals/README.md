# ayria Evals

This directory defines the standardized, reproducible evaluation surface for
`ayria`.

The point is not "more tests". The point is to create a stable test
application and test protocol so future model, prompt, routing, and runtime
changes can be compared against the same workload.

## Why This Exists

Ad hoc smoke tests are useful for immediate debugging, but they are weak as a
long-term product instrument.

`ayria` needs a repeatable evaluation layer that can answer:

- did a code change break local live inference
- did a routing change improve or degrade contract truthfulness
- did a model change improve capability while hurting latency
- did persona changes pollute factual exactness
- did runtime policy changes reduce noise or introduce regressions

## Design Goal

The eval system should make these things explicit and comparable:

1. fixed inputs
2. fixed world state fixtures
3. fixed runtime mode and config
4. fixed scoring rubric
5. structured result output
6. historical baselines that can be compared across commits

## What Belongs Here

- scenario manifests
- fixture inputs
- scoring contracts
- result schemas
- baseline examples
- reproducibility rules

## What Does Not Belong Here

- hidden prompt tweaks
- one-off manual notes
- unversioned screenshots used as secret references
- benchmark scripts that produce unstructured stdout only

## Directory Layout

- `contracts/`
  JSON schemas for scenario and run outputs.
- `fixtures/`
  Frozen input payloads and world-state samples.
- `scenarios/`
  Versioned scenario definitions and score rules.
- `results/`
  Intended output location for saved run artifacts.

## Evaluation Layers

The eval system should eventually cover multiple layers.

### Layer 1: provider connectivity

Questions:
- is the local provider reachable
- is the configured model installed
- does the runtime return truthful failure messages

### Layer 2: capability exactness

Questions:
- does the system return the required exact string
- does it preserve contract fields
- does it avoid persona drift in exact-output tasks

### Layer 3: runtime policy

Questions:
- are screenshots blocked before ingestion when required
- does proactive cooldown behave correctly
- are provider statuses honest

### Layer 4: user-facing quality

Questions:
- does latency stay within an acceptable budget
- does the system avoid unnecessary noise
- does it preserve persona without corrupting capability outputs

## Reproducibility Rules

Every serious evaluation should record:

- git commit
- scenario id and version
- runtime config
- provider id
- model name
- whether provider stub mode was enabled
- start/end timestamps
- duration
- pass/fail result
- structured score details

If any of those fields are missing, the result is weak for historical
comparison.

## First Standard Scenarios

The first scenarios in this repo are intentionally narrow:

1. `basic_chat_exact_match`
2. `provider_health_and_install_guidance`

These are valuable because they test the things most likely to silently rot:

- live local provider truthfulness
- correct model naming
- install guidance for missing models
- exact-output compliance

## Expected Workflow

When changing provider, routing, prompt, or runtime-policy code:

1. run targeted unit tests
2. run at least one standardized eval scenario from this directory
3. save the result in a structured format
4. compare it to the previous baseline before claiming improvement

## Important Constraint

Do not let persona formatting contaminate exact-match capability evals.

For exact-match scenarios, the system should either:

- disable persona rewrite for the scenario, or
- use prompts that explicitly verify persona does not alter exact-output tasks

Capability measurement must remain separable from style measurement.
