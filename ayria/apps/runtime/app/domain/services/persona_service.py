"""Persona rewrite service.

This service exists so capability output stays disciplined while final wording
can still feel like the character.

Important rule:
Do not let persona generation decide tool usage.
Tool and reasoning decisions belong upstream.

Editing guidance:
- Keep persona intensity configurable.
- Preserve meaning exactly unless the upstream result is malformed.
- In safety-sensitive or tool-heavy contexts, personality should soften.
"""

class PersonaService:
    def rewrite(self, capability_text: str, intensity: str = 'normal') -> str:
        # Stub implementation. Replace with model call or prompt policy later.
        return capability_text
