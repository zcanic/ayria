"""Scenario and fixture loading utilities."""

from __future__ import annotations

import json
from pathlib import Path

from app.evals.models import EvalScenario
from app.evals.paths import evals_root, repo_root
from app.evals.schema_validation import validate_scenario_document


def load_scenario(path: str | Path) -> EvalScenario:
    scenario_path = Path(path)
    if not scenario_path.is_absolute():
        cwd_candidate = scenario_path.resolve()
        repo_candidate = (repo_root() / scenario_path).resolve()
        scenario_path = cwd_candidate if cwd_candidate.exists() else repo_candidate
    document = json.loads(scenario_path.read_text())
    validate_scenario_document(document)
    return EvalScenario.model_validate(document)


def load_fixture(rel_path: str) -> object:
    fixture_path = evals_root() / rel_path
    return json.loads(fixture_path.read_text())
