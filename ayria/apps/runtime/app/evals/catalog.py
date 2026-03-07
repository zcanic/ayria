"""Scenario discovery helpers."""

from __future__ import annotations

from pathlib import Path

from app.evals.loader import evals_root


def list_scenario_paths() -> list[Path]:
    return sorted((evals_root() / 'scenarios').glob('**/scenario.json'))
