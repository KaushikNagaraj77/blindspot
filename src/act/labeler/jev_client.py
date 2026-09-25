"""TypeSafe JEV client: caching, max 3 retries on transient errors, and
explicit logging of every attempt. Never retries to get a 'better' answer.

Failure types are kept distinct (per the JEV paper):
  transport  - network / 5xx / timeout
  contract   - 200 response whose payload is missing the expected answers
"""

import os
import time

import httpx

from act.config import CACHE_DIR, JEV_MODEL, JEV_URL
from act.labeler.cache import JsonlCache

_cache = JsonlCache(CACHE_DIR / "jev.jsonl")


def ask(state: dict, questions: dict, model: str = JEV_MODEL) -> dict:
    """Return {"answers": {...}, "usage": {...}, "error": None | "transport" | "contract"}."""
    payload = {"model": model, "state": state, "questions": questions}
    if (hit := _cache.get(payload)) is not None:
        return hit

    headers = {"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}"}
    result = {"answers": {}, "usage": {}, "error": "transport", "attempts": 0}
    for attempt in range(1, 4):
        result["attempts"] = attempt
        try:
            r = httpx.post(JEV_URL, json=payload, headers=headers, timeout=20)
            if r.status_code >= 500:
                raise httpx.HTTPStatusError("server", request=r.request, response=r)
            r.raise_for_status()
            body = r.json()
            answers = body.get("answers", {})
            missing = [q for q in questions if q not in answers]
            result = {
                "answers": answers,
                "usage": body.get("usage", {}),
                "error": "contract" if missing else None,
                "attempts": attempt,
            }
            break
        except (httpx.TransportError, httpx.HTTPStatusError):
            time.sleep(2**attempt)

    _cache.put(payload, result)
    return result
