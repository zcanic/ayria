"""Evaluator agent placeholder.

Optional safety and quality layer.
Use later to reject outputs that are too intrusive, leak hidden context, or
misrepresent what the system actually observed.
"""

class EvaluatorAgent:
    async def run(self, candidate_text: str) -> dict:
        return {'approved': True, 'reason': 'stub'}
