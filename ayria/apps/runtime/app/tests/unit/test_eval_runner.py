from pathlib import Path

from app.evals.catalog import list_scenario_paths
from app.evals.runner import run_scenario


def test_basic_chat_exact_match_scenario_runs_with_fake_provider(monkeypatch) -> None:
    from app.evals import runtime_harness as harness
    from app.evals import runner as eval_runner
    from app.domain.services.model_execution_service import ModelExecutionService

    original_runtime_client = harness.runtime_client

    class FakeWorkingProvider:
        implemented = True
        provider_id = 'ollama'

        def normalize_model_name(self, model: str) -> str:
            return model

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            return {'provider': 'ollama', 'model': model, 'message': 'runtime-smoke-ok'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    def fake_runtime_client(config_overrides: dict | None = None):
        ctx = original_runtime_client(config_overrides)
        client, container = ctx.__enter__()
        container.llm_providers['ollama'] = FakeWorkingProvider()
        container.model_execution_service = ModelExecutionService(provider_stub_mode=False, providers=container.llm_providers)
        container.orchestrator._model_execution_service = container.model_execution_service

        class _Wrapped:
            def __enter__(self):
                return client, container

            def __exit__(self, exc_type, exc, tb):
                return ctx.__exit__(exc_type, exc, tb)

        return _Wrapped()

    monkeypatch.setattr(harness, 'runtime_client', fake_runtime_client)
    monkeypatch.setattr(eval_runner, 'runtime_client', fake_runtime_client)
    scenario_path = Path(__file__).resolve().parents[5] / 'evals/scenarios/basic_chat_exact_match/scenario.json'
    result, _ = run_scenario(scenario_path, write_artifacts=False)
    assert result.passed is True
    assert result.scenario_id == 'basic_chat_exact_match'
    exact_score = next(item for item in result.scores if item.rule_id == 'assistant_text_exact')
    assert exact_score.actual == 'runtime-smoke-ok'


def test_provider_health_scenario_runs_with_fake_provider(monkeypatch) -> None:
    from app.evals import runtime_harness as harness
    from app.evals import runner as eval_runner
    from app.domain.services.model_execution_service import ModelExecutionService

    original_runtime_client = harness.runtime_client

    class FakeHealthyProvider:
        implemented = True
        provider_id = 'ollama'

        def normalize_model_name(self, model: str) -> str:
            return model

        async def chat(self, messages: list[dict], model: str, tools: list[dict] | None = None) -> dict:
            return {'provider': 'ollama', 'model': model, 'message': 'unused'}

        async def health_check(self, model: str | None = None) -> dict:
            return {'configured': True, 'implemented': True, 'reachable': True, 'status': 'ok'}

    def fake_runtime_client(config_overrides: dict | None = None):
        ctx = original_runtime_client(config_overrides)
        client, container = ctx.__enter__()
        container.llm_providers['ollama'] = FakeHealthyProvider()
        container.model_execution_service = ModelExecutionService(provider_stub_mode=False, providers=container.llm_providers)
        container.orchestrator._model_execution_service = container.model_execution_service

        class _Wrapped:
            def __enter__(self):
                return client, container

            def __exit__(self, exc_type, exc, tb):
                return ctx.__exit__(exc_type, exc, tb)

        return _Wrapped()

    monkeypatch.setattr(harness, 'runtime_client', fake_runtime_client)
    monkeypatch.setattr(eval_runner, 'runtime_client', fake_runtime_client)
    scenario_path = Path(__file__).resolve().parents[5] / 'evals/scenarios/provider_health_and_install_guidance/scenario.json'
    result, _ = run_scenario(scenario_path, write_artifacts=False)
    assert result.passed is True
    assert result.scenario_id == 'provider_health_and_install_guidance'
    live_mode_score = next(item for item in result.scores if item.rule_id == 'providers_live_mode')
    assert live_mode_score.actual == 'live'


def test_scenario_catalog_lists_new_standard_scenarios() -> None:
    names = {path.parent.name for path in list_scenario_paths()}
    assert 'basic_chat_exact_match' in names
    assert 'provider_health_and_install_guidance' in names
    assert 'screenshot_blocked_blacklisted_app' in names
    assert 'stub_mode_truthful_chat' in names


def test_stub_mode_truthful_chat_scenario_runs() -> None:
    scenario_path = Path(__file__).resolve().parents[5] / 'evals/scenarios/stub_mode_truthful_chat/scenario.json'
    result, out_path = run_scenario(scenario_path, write_artifacts=False)
    assert result.passed is True
    assert out_path.suffix == '.json'
    stub_score = next(item for item in result.scores if item.rule_id == 'stub_inference_mode')
    assert stub_score.actual == 'stub'


def test_screenshot_blocked_blacklisted_app_scenario_runs() -> None:
    scenario_path = Path(__file__).resolve().parents[5] / 'evals/scenarios/screenshot_blocked_blacklisted_app/scenario.json'
    result, _ = run_scenario(scenario_path, write_artifacts=False)
    assert result.passed is True
    blocked_score = next(item for item in result.scores if item.rule_id == 'policy_blocked')
    assert blocked_score.actual is True
