"""Web search tool.

This remains intentionally lightweight, but it now performs a real HTTP lookup
against DuckDuckGo's instant-answer endpoint and normalizes a compact result
shape.
"""

from __future__ import annotations

import httpx


async def web_search(query: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
        response = await client.get(
            'https://api.duckduckgo.com/',
            params={
                'q': query,
                'format': 'json',
                'no_html': '1',
                'no_redirect': '1',
            },
        )
        response.raise_for_status()
        body = response.json()

    results: list[dict] = []
    abstract_text = body.get('AbstractText')
    abstract_url = body.get('AbstractURL')
    if abstract_text:
        results.append({'title': body.get('Heading') or query, 'snippet': abstract_text, 'url': abstract_url})

    for item in body.get('RelatedTopics', [])[:5]:
        if isinstance(item, dict) and item.get('Text'):
            results.append(
                {
                    'title': item.get('FirstURL') or item.get('Text'),
                    'snippet': item.get('Text'),
                    'url': item.get('FirstURL'),
                }
            )
    return {'query': query, 'results': results}
