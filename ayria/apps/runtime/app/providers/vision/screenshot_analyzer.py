"""Screenshot analyzer placeholder.

This module should produce structured summaries from desktop screenshots.
Do not return only a free-form paragraph. Structured outputs are needed for
`WorldState` updates and proactive decision logic.

Expected future fields:
- summary
- scene_type
- detected_entities
- likely_user_goal
- confidence

This is one of the highest leverage modules in the whole product because it
turns passive desktop observation into actionable context.
"""

class ScreenshotAnalyzer:
    async def analyze(self, image_path: str) -> dict:
        return {
            'summary': 'stub screenshot summary',
            'detected_entities': [],
            'scene_type': 'unknown',
            'confidence': 0.0,
        }
