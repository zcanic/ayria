"""Capability agent placeholder.

This agent is responsible for disciplined reasoning and structured outputs.
It should be the first model-facing layer for most tasks.
"""

class CapabilityAgent:
    async def run(self, prompt: str) -> dict:
        return {'raw_output': prompt, 'structured': {}}
