"""Screenshot analyzer.

This analyzer prefers a real multimodal model path when the runtime is in live
mode and a vision-capable provider is configured. If that path is unavailable,
it falls back to a deterministic heuristic classifier so policy and eval tests
still remain reproducible.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.domain.services.model_execution_service import ModelExecutionService


class ScreenshotAnalyzer:
    def __init__(
        self,
        *,
        model_execution_service: ModelExecutionService | None = None,
        provider_name: str = 'ollama',
        model: str = 'qwen3.5:0.8b',
    ) -> None:
        self._model_execution_service = model_execution_service
        self._provider_name = provider_name
        self._model = model

    async def analyze(self, image_path: str) -> dict:
        if self._model_execution_service is not None and not self._model_execution_service.provider_stub_mode:
            try:
                provider_result = await self._model_execution_service.run_chat(
                    provider_name=self._provider_name,
                    model=self._model,
                    text=(
                        'Describe this screenshot for desktop-assistant context. '
                        'State the likely scene type, notable UI elements, and the likely user goal.'
                    ),
                    image_paths=[image_path],
                )
                raw_summary = str(provider_result.get('message', '')).strip()
                if raw_summary:
                    structured = self._classify_from_text(raw_summary)
                    structured['summary'] = raw_summary
                    structured['analysis_mode'] = 'provider_vision'
                    structured['provider'] = provider_result.get('provider')
                    structured['model'] = provider_result.get('model')
                    return structured
            except Exception:
                pass

        heuristic = self._heuristic_analyze(image_path)
        heuristic['analysis_mode'] = 'heuristic_fallback'
        return heuristic

    def _classify_from_text(self, text: str) -> dict:
        lowered = text.lower()
        scene_type = 'unknown'
        confidence = 0.82
        detected_entities: list[str] = []
        likely_user_goal = 'inspect_desktop_context'

        if self._matches_any(lowered, ('source code', 'editor', 'function', 'terminal', 'cursor', 'vscode', 'ide')):
            scene_type = 'code'
            detected_entities.extend(['editor', 'source_code'])
            likely_user_goal = 'edit_or_review_code'
        elif self._matches_any(lowered, ('browser', 'web page', 'website', 'tab', 'search', 'url')):
            scene_type = 'browser'
            detected_entities.append('browser')
            likely_user_goal = 'read_or_search_web_content'
        elif self._matches_any(lowered, ('document', 'pdf', 'article', 'notes', 'notion')):
            scene_type = 'document'
            detected_entities.append('document')
            likely_user_goal = 'read_or_edit_document'
        elif self._matches_any(lowered, ('chat', 'message', 'discord', 'slack', 'conversation')):
            scene_type = 'chat'
            detected_entities.append('chat')
            likely_user_goal = 'communicate'
        elif self._matches_any(lowered, ('image', 'photo', 'illustration', 'picture')):
            scene_type = 'image'
            detected_entities.append('image')
            likely_user_goal = 'view_image_content'
        elif self._matches_any(lowered, ('desktop', 'window', 'screen', 'application')):
            scene_type = 'desktop'

        if self._matches_any(lowered, ('login', 'password', 'credential', '2fa', 'verification code')):
            detected_entities.append('credential')
        if self._matches_any(lowered, ('payment', 'card', 'checkout', 'invoice')):
            detected_entities.append('payment')

        return {
            'summary': text,
            'detected_entities': sorted(set(detected_entities)),
            'scene_type': scene_type,
            'likely_user_goal': likely_user_goal,
            'confidence': confidence,
        }

    def _heuristic_analyze(self, image_path: str) -> dict:
        path = Path(image_path)
        text = f'{path.name} {" ".join(path.parts)}'.lower()

        scene_type = 'desktop'
        detected_entities: list[str] = []
        confidence = 0.58
        likely_user_goal = 'inspect_desktop_context'

        if any(token in text for token in ('code', 'cursor', 'vscode', 'py', 'ts', 'js')):
            scene_type = 'code'
            detected_entities.extend(['editor', 'source_code'])
            confidence = 0.72
            likely_user_goal = 'edit_or_review_code'
        elif any(token in text for token in ('browser', 'chrome', 'safari', 'firefox', 'edge')):
            scene_type = 'browser'
            detected_entities.append('browser')
            confidence = 0.7
            likely_user_goal = 'read_or_search_web_content'
        elif any(token in text for token in ('doc', 'pdf', 'notion', 'word', 'pages')):
            scene_type = 'document'
            detected_entities.append('document')
            confidence = 0.68
            likely_user_goal = 'read_or_edit_document'
        elif any(token in text for token in ('chat', 'discord', 'slack', 'telegram', 'wechat')):
            scene_type = 'chat'
            detected_entities.append('chat')
            confidence = 0.69
            likely_user_goal = 'communicate'
        elif any(token in text for token in ('image', 'photo', 'png', 'jpg', 'jpeg', 'webp')):
            scene_type = 'image'
            detected_entities.append('image')
            confidence = 0.66
            likely_user_goal = 'view_image_content'

        summary = f'Heuristic screenshot analysis suggests a {scene_type} scene from {path.name}.'
        return {
            'summary': summary,
            'detected_entities': detected_entities,
            'scene_type': scene_type,
            'likely_user_goal': likely_user_goal,
            'confidence': confidence,
        }

    def _matches_any(self, text: str, tokens: tuple[str, ...]) -> bool:
        for token in tokens:
            if ' ' in token or token.isdigit():
                if token in text:
                    return True
                continue
            if re.search(rf'\b{re.escape(token)}\b', text):
                return True
        return False
