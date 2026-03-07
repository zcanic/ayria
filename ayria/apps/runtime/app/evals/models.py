"""Typed models for eval scenarios and run outputs.

These are intentionally small and explicit so scenario meaning stays in data
files rather than being buried in procedural code.
"""

from pydantic import BaseModel, Field


class EvalStep(BaseModel):
    step_id: str
    kind: str
    method: str | None = None
    path: str | None = None
    payload: dict = Field(default_factory=dict)
    fixture_ref: str | None = None
    delay_ms: int | None = None


class ScoreRule(BaseModel):
    rule_id: str
    type: str
    target: str
    expected: object | None = None
    max_ms: int | None = None


class EvalScenario(BaseModel):
    scenario_id: str
    scenario_version: str
    purpose: str
    runtime_mode: str
    provider: str
    model: str
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
