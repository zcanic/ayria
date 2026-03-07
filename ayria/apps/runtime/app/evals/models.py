"""Typed models for eval scenarios and run outputs.

These are intentionally small and explicit so scenario meaning stays in data
files rather than being buried in procedural code.
"""

from pydantic import BaseModel, ConfigDict, Field


class EvalStep(BaseModel):
    step_id: str
    kind: str
    method: str | None = None
    path: str | None = None
    payload: dict = Field(default_factory=dict)
    fixture_ref: str | None = None
    delay_ms: int | None = None


class ScoreRule(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_id: str
    type: str
    target: str
    expected: object | None = None
    max_ms: int | None = None
    schema_definition: dict | None = Field(default=None, alias='schema')


class EvalScenario(BaseModel):
    scenario_id: str
    scenario_version: str
    purpose: str
    runtime_mode: str
    provider: str
    model: str
    mock_profile: str | None = None
    config_overrides: dict = Field(default_factory=dict)
    fixture_refs: list[str] = Field(default_factory=list)
    steps: list[EvalStep]
    scoring: list[ScoreRule]


class StepResult(BaseModel):
    step_id: str
    status: str
    duration_ms: int
    response_status: int | None = None
    response_body: object | None = None


class ScoreResult(BaseModel):
    rule_id: str
    passed: bool
    actual: object | None = None
    expected: object | None = None
    details: str | None = None


class EvalRunResult(BaseModel):
    run_id: str
    scenario_id: str
    scenario_version: str
    git_commit: str
    runtime_mode: str
    provider: str
    model: str
    started_at: str
    finished_at: str
    duration_ms: int
    passed: bool
    environment: dict = Field(default_factory=dict)
    config_snapshot: dict = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    scores: list[ScoreResult]
    steps: list[StepResult]
