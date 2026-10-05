"""In-memory sliding-window rate limiter.

Simplest option for a single-process `uvicorn --reload` deployment (see
CLAUDE.md section 8: rate-limit POST /auth/login to 5/min/IP). Not shared
across multiple worker processes — if the backend is ever run with
`--workers > 1` or behind multiple instances, replace this with a shared
store (e.g. Redis) instead. Documented in docs/decisions.md.
"""

import time
from collections import defaultdict

_hits: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(key: str, max_hits: int, window_seconds: float) -> bool:
    now = time.monotonic()
    cutoff = now - window_seconds
    hits = [t for t in _hits[key] if t > cutoff]
    hits.append(now)
    _hits[key] = hits
    return len(hits) > max_hits
