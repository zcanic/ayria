"""CLI runner for standardized ayria eval scenarios.

Usage:
`uv run python -m app.evals.runner --scenario ../../evals/scenarios/basic_chat_exact_match/scenario.json`
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import platform
import subprocess
import time
from pathlib import Path

from app.evals.catalog import list_scenario_paths
from app.evals.loader import load_fixture, load_scenario, repo_root
from app.evals.mock_profiles import apply_mock_profile
from app.evals.models import EvalRunResult, StepResult
from app.evals.result_writer import default_result_path, write_result
from app.evals.runtime_harness import delay_ms, runtime_client, seed_world_state
from app.evals.scoring import score_rule


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return 'unknown'


def _effective_config_overrides(scenario) -> dict:
    overrides = dict(scenario.config_overrides)

    desired_stub_mode = scenario.runtime_mode == 'stub'
    if 'provider_stub_mode' in overrides and bool(overrides['provider_stub_mode']) != desired_stub_mode:
        raise ValueError(
            f"scenario_runtime_mode_mismatch:{scenario.scenario_id}:runtime_mode={scenario.runtime_mode}:provider_stub_mode={overrides['provider_stub_mode']}"
        )
    overrides['provider_stub_mode'] = desired_stub_mode

    if 'default_provider' in overrides and overrides['default_provider'] != scenario.provider:
        raise ValueError(
            f"scenario_provider_mismatch:{scenario.scenario_id}:provider={scenario.provider}:default_provider={overrides['default_provider']}"
        )
    overrides['default_provider'] = scenario.provider

    if scenario.provider == 'ollama':
        if 'capability_model' in overrides and overrides['capability_model'] != scenario.model:
            raise ValueError(
                f"scenario_model_mismatch:{scenario.scenario_id}:model={scenario.model}:capability_model={overrides['capability_model']}"
            )
        overrides['capability_model'] = scenario.model

    return overrides


def run_scenario(scenario_path: str | Path, *, write_artifacts: bool = True) -> tuple[EvalRunResult, Path]:
    scenario = load_scenario(scenario_path)
    config_overrides = _effective_config_overrides(scenario)
    started_at = _now_iso()
    run_started = time.perf_counter()
    step_results: list[StepResult] = []
    notes: list[str] = []

    with runtime_client(config_overrides=config_overrides) as (client, container):
        if scenario.mock_profile:
            apply_mock_profile(container, scenario.mock_profile)
        for fixture_ref in scenario.fixture_refs:
            if fixture_ref.startswith('fixtures/world_state/'):
                seed_world_state(container, load_fixture(fixture_ref))

        for step in scenario.steps:
            t0 = time.perf_counter()
            if step.kind == 'delay':
                delay_ms(int(step.delay_ms or 0))
                step_results.append(StepResult(step_id=step.step_id, status='completed', duration_ms=int((time.perf_counter() - t0) * 1000)))
                continue

            if step.kind == 'world_state_seed':
                payload = step.payload
                if step.fixture_ref:
                    payload = load_fixture(step.fixture_ref)
                seed_world_state(container, payload)
                step_results.append(StepResult(step_id=step.step_id, status='completed', duration_ms=int((time.perf_counter() - t0) * 1000)))
                continue

            if step.kind != 'http_request':
                raise ValueError(f'unsupported step kind: {step.kind}')

            method = str(step.method or 'GET').upper()
            payload = step.payload or {}
            if method == 'GET':
                response = client.get(str(step.path))
            elif method == 'POST':
                response = client.post(str(step.path), json=payload)
            elif method == 'PUT':
                response = client.put(str(step.path), json=payload)
            else:
                raise ValueError(f'unsupported HTTP method: {method}')

            step_results.append(
                StepResult(
                    step_id=step.step_id,
                    status='completed' if response.status_code < 500 else 'failed',
                    duration_ms=int((time.perf_counter() - t0) * 1000),
                    response_status=response.status_code,
                    response_body=response.json(),
                )
            )

    step_map = {step.step_id: step for step in step_results}
    score_results = [score_rule(rule, step_map) for rule in scenario.scoring]
    passed = all(item.passed for item in score_results)

    finished_at = _now_iso()
    result = EvalRunResult(
        run_id=f'{scenario.scenario_id}__{int(time.time())}',
        scenario_id=scenario.scenario_id,
        scenario_version=scenario.scenario_version,
        git_commit=_git_commit(),
        runtime_mode=scenario.runtime_mode,
        provider=scenario.provider,
        model=scenario.model,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=int((time.perf_counter() - run_started) * 1000),
        passed=passed,
        environment={
            'platform': platform.platform(),
            'python_version': platform.python_version(),
        },
        config_snapshot=config_overrides,
        notes=notes,
        scores=score_results,
        steps=step_results,
    )
    out_path = default_result_path(result)
    if write_artifacts:
        out_path, _ = write_result(result)
    return result, out_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Run a standardized ayria eval scenario.')
    parser.add_argument('--scenario', help='Path to a scenario.json file')
    parser.add_argument('--list', action='store_true', help='List available scenarios')
    args = parser.parse_args()

    if args.list:
        for scenario_path in list_scenario_paths():
            print(scenario_path)
        return 0

    if not args.scenario:
        parser.error('--scenario is required unless --list is used')

    result, out_path = run_scenario(args.scenario)
    status = 'PASS' if result.passed else 'FAIL'
    print(f'[{status}] {result.scenario_id}@{result.scenario_version} provider={result.provider} model={result.model}')
    print(f'result={out_path}')
    for score in result.scores:
        marker = 'ok' if score.passed else 'bad'
        print(f'  - {marker} {score.rule_id}: actual={score.actual!r} expected={score.expected!r}')
    return 0 if result.passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
