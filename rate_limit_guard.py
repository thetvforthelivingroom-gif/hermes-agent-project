"""Rate‑limit guard for hermes_tools web calls.

Provides wrapper functions `guarded_web_search` and `guarded_web_extract` that
invoke the original `web_search` / `web_extract` from hermes_tools and then
inspect the `X‑RateLimit‑Remaining` HTTP header of the returned URLs.  If the
remaining quota falls below a configurable threshold the function backs off with
an exponential delay before proceeding.

Usage example:

    from rate_limit_guard import guarded_web_search
    result = guarded_web_search('site:example.com', limit=3)

The guard logs to stdout when throttling and resumes automatically once the
limit is safe.
"""
import time
import subprocess
from typing import Any, Dict, List

# Configurable threshold – when remaining requests drop below this, we back‑off.
THRESHOLD = 5
# Base sleep seconds; actual wait = BASE_SLEEP * (2 ** backoff_step).
BASE_SLEEP = 2


def _check_rate_limit(url: str, threshold: int = THRESHOLD) -> None:
    """Query the URL's HEAD and parse ``X-RateLimit-Remaining``.

    If the header is present and the remaining count is below *threshold*,
    sleep for an exponential back‑off based on how far under the limit we are.
    """
    try:
        # ``-I`` fetches headers only; ``-s`` silences progress output.
        result = subprocess.run(
            ["curl", "-s", "-I", url],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(f"[rate_limit_guard] curl failed for {url}: {result.stderr.strip()}")
            return
        for line in result.stdout.splitlines():
            if line.lower().startswith("x-ratelimit-remaining:"):
                try:
                    remaining = int(line.split(":", 1)[1].strip())
                except ValueError:
                    continue
                if remaining < threshold:
                    # Back‑off step is difference to threshold (e.g. 3 -> 2 steps)
                    step = max(threshold - remaining, 1)
                    wait = BASE_SLEEP * (2 ** step)
                    print(
                        f"[rate_limit_guard] Rate limit low ({remaining} remaining). "
                        f"Sleeping {wait}s before continuing."
                    )
                    time.sleep(wait)
                break
    except Exception as exc:  # pragma: no cover – defensive
        print(f"[rate_limit_guard] Exception checking rate limit for {url}: {exc}")


def _apply_guard(urls: List[str]) -> None:
    """Run the guard on each URL in *urls*.
    """
    for u in urls:
        _check_rate_limit(u)


def guarded_web_search(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Call ``hermes_tools.web_search`` then guard against rate limits.

    The original function returns a dict with ``data['web']`` containing a list of
    result entries, each having at least a ``url`` field.  All URLs are passed to
    the guard before the result is returned to the caller.
    """
    from hermes_tools import web_search

    result = web_search(*args, **kwargs)
    try:
        urls = [entry["url"] for entry in result.get("data", {}).get("web", [])]
        _apply_guard(urls)
    except Exception as exc:  # pragma: no cover – defensive
        print(f"[rate_limit_guard] Unexpected result format: {exc}")
    return result


def guarded_web_extract(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Call ``hermes_tools.web_extract`` then guard against rate limits.

    ``web_extract`` returns ``results`` where each entry includes a ``url`` key.
    The guard checks those URLs.
    """
    from hermes_tools import web_extract

    result = web_extract(*args, **kwargs)
    try:
        urls = [entry["url"] for entry in result.get("results", [])]
        _apply_guard(urls)
    except Exception as exc:  # pragma: no cover – defensive
        print(f"[rate_limit_guard] Unexpected result format: {exc}")
    return result

# End of file
