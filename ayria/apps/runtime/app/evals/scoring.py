"""Score computation for standardized eval scenarios."""

from __future__ import annotations

import re

from app.evals.models import ScoreResult, ScoreRule, StepResult


def _path_parts(path: str) -> list[object]:
    parts: list[object] = []
    for match in re.finditer(r'([A-Za-z_][A-Za-z0-9_]*)|\[(\d+)\]', path):
        name = match.group(1)
        index = match.group(2)
        if name is not None:
            parts.append(name)
        elif index is not None:
            parts.append(int(index))
    return parts


def resolve_target(steps: dict[str, StepResult], target: str) -> object:
    if not target.startswith('steps.'):
        raise ValueError(f'unsupported target root: {target}')

    parts = target.split('.', 2)
    if len(parts) != 3:
        raise ValueError(f'invalid target: {target}')
    step_id = parts[1]
    remainder = parts[2]
    current: object = steps[step_id]

    for part in _path_parts(remainder):
        if isinstance(part, int):
            current = current[part]  # type: ignore[index]
        else:
            if isinstance(current, StepResult):
                current = getattr(current, part)
            elif isinstance(current, dict):
                current = current[part]
            else:
                current = getattr(current, part)
    return current


def score_rule(rule: ScoreRule, steps: dict[str, StepResult]) -> ScoreResult:
    actual = resolve_target(steps, rule.target)

    if rule.type == 'exact_match':
        passed = actual == rule.expected
        return ScoreResult(rule_id=rule.rule_id, passed=passed, actual=actual, expected=rule.expected)

    if rule.type == 'substring_match':
        passed = str(rule.expected) in str(actual)
        return ScoreResult(rule_id=rule.rule_id, passed=passed, actual=actual, expected=rule.expected)

    if rule.type == 'schema_match':
        # v0 keeps schema_match intentionally simple: exact expected value at a
        # known response location. Broader JSON Schema validation can be added
        # later without changing scenario structure.
        passed = actual == rule.expected
        return ScoreResult(rule_id=rule.rule_id, passed=passed, actual=actual, expected=rule.expected)

    if rule.type == 'latency_budget':
        actual_ms = int(actual)
        passed = actual_ms <= int(rule.max_ms or 0)
        return ScoreResult(
            rule_id=rule.rule_id,
            passed=passed,
            actual=actual_ms,
            expected=rule.max_ms,
            details=f'actual_ms={actual_ms}',
        )

    if rule.type == 'policy_assertion':
        passed = actual == rule.expected
        return ScoreResult(rule_id=rule.rule_id, passed=passed, actual=actual, expected=rule.expected)

    raise ValueError(f'unsupported score type: {rule.type}')
