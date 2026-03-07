"""JSON Schema validation for eval artifacts."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from app.evals.paths import evals_root


def _load_schema(name: str) -> dict:
    schema_path = evals_root() / 'contracts' / name
    return json.loads(schema_path.read_text())


def validate_scenario_document(document: dict) -> None:
    Draft202012Validator(_load_schema('scenario.schema.json')).validate(document)


def validate_run_result_document(document: dict) -> None:
    Draft202012Validator(_load_schema('run-result.schema.json')).validate(document)
