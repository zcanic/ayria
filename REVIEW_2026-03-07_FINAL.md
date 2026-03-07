# Review 2026-03-07

Scope:

- existing `ayria` runtime code
- desktop shell scaffold
- newly added standardized eval runner and scenarios

Review standard:

- prefer truthful behavior over optimistic placeholder behavior
- prefer reproducible evals over ad hoc smoke tests
- prefer buildability over partial scaffolding that cannot be checked

## Findings

### 1. High: desktop shell was not build-checkable

Before changes:

- `apps/desktop/src-tauri/` had Rust source
- but there was no `Cargo.toml`
- and no `tauri.conf.json`

Impact:

- `cargo check` could not run at all
- the scaffold looked more complete than it really was

Action taken:

- added `Cargo.toml`
- added `tauri.conf.json`
- verified `cargo check` now passes

### 2. High: eval scenario naming was misleading

Before changes:

- `provider_health_and_install_guidance` only tested healthy provider status
- it did not exercise missing-model install guidance at all

Impact:

- the eval layer could report green while the named behavior was never tested
- historical results would be mislabeled and low-value

Action taken:

- split the scenario into:
  - `provider_live_health_ok`
  - `provider_missing_model_install_guidance`
- updated docs, tests, and scenario discovery

### 3. High: eval scenario metadata could drift from runtime execution

Before changes:

- a scenario could declare `runtime_mode=live`
- while `config_overrides.provider_stub_mode=true`
- or declare one provider/model while running another

Impact:

- results could be recorded under false labels
- this directly harms reproducibility and historical comparison

Action taken:

- added `_effective_config_overrides(...)`
- runtime mode is now enforced against `provider_stub_mode`
- default provider is aligned to the scenario
- Ollama capability model is aligned to the scenario model
- mismatches now fail fast

### 4. Medium: deterministic failure-path evals were missing

Before changes:

- install-guidance and similar failure-path checks depended on machine state
- that is weak for CI and weak for historical baselines

Impact:

- important failure behavior could not be tested reproducibly

Action taken:

- added built-in eval mock profiles
- implemented `missing_model_ollama`
- added a standardized missing-model scenario that now passes deterministically

### 5. Medium: tests were polluting the eval results directory

Before changes:

- unit tests called `run_scenario(...)`
- which wrote formal JSON result artifacts into `evals/results/`

Impact:

- the result directory mixed real baselines with test side-effects
- committed or inspected results would be less trustworthy

Action taken:

- added `write_artifacts=False` control path
- tests now validate logic without writing artifacts
- added `evals/results/.gitignore`

### 6. Medium: eval runner output was too thin for historical use

Before changes:

- result writing was JSON only
- environment and config context were incomplete

Impact:

- manual review and cross-run comparison were weaker than needed

Action taken:

- added environment metadata
- added config snapshot
- added Markdown summary output beside JSON

## Current Quality Assessment

Current state is good enough to push.

Reasons:

- runtime tests pass
- eval runner tests pass
- desktop TypeScript typecheck passes
- Rust shell now passes `cargo check`
- all five standardized eval scenarios pass
- eval results are now more honest and reproducible than before

## Residual Risks

These are real but not blockers for this push:

1. desktop UI remains mostly placeholder UX rather than real feature-complete UI
2. screenshot analyzer is still stubbed and does not provide meaningful scene understanding
3. eval runner still uses simple target-path and score logic, not full JSON-schema validation
4. tool execution and WebSocket/event streaming are still not implemented as production-grade systems

## Verification Performed

- `uv run python -m pytest -q` -> `23 passed`
- `npx tsc --noEmit` -> pass
- `cargo check` in `apps/desktop/src-tauri` -> pass
- `uv run python -m app.evals.runner --list` -> pass
- all 5 standardized scenarios executed successfully
