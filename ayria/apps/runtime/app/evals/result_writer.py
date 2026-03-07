"""Persist eval run outputs to the standardized results directory."""

from __future__ import annotations

from pathlib import Path

from app.evals.loader import evals_root
from app.evals.models import EvalRunResult


def write_result(result: EvalRunResult) -> tuple[Path, Path]:
    out_dir = evals_root() / 'results' / result.scenario_id
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f'{result.started_at.replace(":", "-")}__{result.git_commit}'
    out_path = out_dir / f'{stem}.json'
    out_path.write_text(result.model_dump_json(indent=2))
    md_path = out_dir / f'{stem}.md'
    md_path.write_text(_markdown_summary(result, out_path))
    return out_path, md_path


def default_result_path(result: EvalRunResult) -> Path:
    out_dir = evals_root() / 'results' / result.scenario_id
    return out_dir / f'{result.started_at.replace(":", "-")}__{result.git_commit}.json'


def _markdown_summary(result: EvalRunResult, json_path: Path) -> str:
    lines = [
        f'# Eval Result: {result.scenario_id}',
        '',
        f'- `passed`: `{str(result.passed).lower()}`',
        f'- `scenario_version`: `{result.scenario_version}`',
        f'- `git_commit`: `{result.git_commit}`',
        f'- `runtime_mode`: `{result.runtime_mode}`',
        f'- `provider`: `{result.provider}`',
        f'- `model`: `{result.model}`',
        f'- `duration_ms`: `{result.duration_ms}`',
        f'- `json_result`: `{json_path}`',
        '',
        '## Scores',
        '',
    ]
    for score in result.scores:
        marker = 'PASS' if score.passed else 'FAIL'
        lines.append(f'- `{marker}` `{score.rule_id}` actual=`{score.actual}` expected=`{score.expected}`')

    lines.extend(['', '## Steps', ''])
    for step in result.steps:
        lines.append(
            f'- `{step.step_id}` status=`{step.status}` response_status=`{step.response_status}` duration_ms=`{step.duration_ms}`'
        )
    return '\n'.join(lines) + '\n'
