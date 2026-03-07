"""Screenshot analyzer.

This remains heuristic rather than model-backed, but it is no longer a constant
stub. It extracts a structured best-effort scene classification from file/path
signals so runtime-policy and world-state tests can exercise meaningful data.
"""

from __future__ import annotations

from pathlib import Path


class ScreenshotAnalyzer:
    async def analyze(self, image_path: str) -> dict:
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
