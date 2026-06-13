#!/usr/bin/env python3
"""Linear GraphQL retry policy — exponential backoff on rate limits and server errors."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Optional


def query_with_retry(
    query_fn: Callable[[str, Optional[dict]], dict],
    query: str,
    variables: Optional[dict] = None,
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
) -> dict:
    """Execute a GraphQL query with exponential backoff when rate-limited.

    Args:
        query_fn: Low-level query callable (typically ``LinearClient._query``).
        query: GraphQL query string.
        variables: Optional query variables.
        max_retries: Maximum retry attempts after the first failure.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        Parsed GraphQL response data dict.

    Raises:
        Exception: On non-retryable errors or when retries are exhausted.
    """
    last_exception: Exception | None = None
    is_rate_limit = False
    is_5xx = False

    for attempt in range(max_retries + 1):
        try:
            return query_fn(query, variables)
        except Exception as exc:
            last_exception = exc

            error_msg = str(exc).lower()
            
            # Rate limit errors (429)
            if "429" in error_msg or "ratelimit" in error_msg:
                is_rate_limit = True
            
            # Server errors (5xx)
            if any(code in error_msg for code in ["500", "502", "503", "504"]):
                is_5xx = True

            # Retry on rate limit or 5xx server errors
            if is_rate_limit or is_5xx:
                if "3600000" in error_msg or "per 1 hour" in error_msg:
                    print(
                        "  ❌ Linear 1-Hour Rate Limit (2500 requests) exceeded. Aborting immediately.",
                        file=sys.stderr,
                    )
                    raise

                if "60000" in error_msg and "limit" in error_msg:
                    print(
                        "  ⚠️ Linear 1-Minute Rate Limit (30 searches) hit. "
                        "Sleeping for 32 seconds to bridge the window...",
                        file=sys.stderr,
                    )
                    time.sleep(32)

                if attempt < max_retries:
                    delay = min(base_delay * (2**attempt), 60.0)
                    error_type = "Rate Limit" if is_rate_limit else "Server Error (5xx)"
                    print(
                        f"  ⚠️ Linear {error_type} detected (attempt {attempt + 1}/{max_retries + 1}). "
                        f"Retrying in {delay:.1f} seconds...",
                        file=sys.stderr,
                    )
                    time.sleep(delay)
                else:
                    error_type = "Rate Limit" if is_rate_limit else "Server Error (5xx)"
                    print(
                        f"  ❌ Linear {error_type} exceeded after {max_retries} retries.",
                        file=sys.stderr,
                    )
                    raise
            else:
                # Non-retryable error
                raise

    if last_exception is not None:
        raise last_exception
    raise RuntimeError("query_with_retry exhausted without result")
