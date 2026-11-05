"""A small HTTP client for the data providers: timeouts, retries with backoff, clear errors."""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from forecheck.application.errors import NotFoundError, RateLimitedError, SourceUnavailableError

_RETRIABLE_STATUS = frozenset({500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Waits ``base_delay``, then twice that, and so on, up to ``max_attempts`` tries."""

    max_attempts: int = 4
    base_delay: float = 2.0
    max_delay: float = 30.0
    # A per-minute quota clears with the minute, which is longer than ``max_delay``.
    minute_limit_wait: float = 60.0

    def delay(self, attempt: int) -> float:
        return float(min(self.max_delay, self.base_delay * 2 ** (attempt - 1)))


class HttpClient:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout: float = 30.0,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        )
        self._retry = retry or RetryPolicy()
        self._sleep = sleep

    def get_json(self, url: str, params: Mapping[str, str | int | float] | None = None) -> Any:
        try:
            return self._get(url, params).json()
        except ValueError as error:
            raise SourceUnavailableError(f"{url} did not return JSON") from error

    def get_bytes(self, url: str) -> bytes:
        return self._get(url, None).content

    def get_text(self, url: str) -> str:
        return self._get(url, None).text

    def _get(self, url: str, params: Mapping[str, str | int | float] | None) -> httpx.Response:
        last_problem = "no attempt was made"
        for attempt in range(1, self._retry.max_attempts + 1):
            try:
                response = self._client.get(url, params=params)
            except httpx.RequestError as error:
                last_problem = f"{type(error).__name__}: {error}"
                self._wait(attempt, None)
                continue

            if response.is_success:
                return response
            if response.status_code == 429:
                reason = _reason(response)
                if "minutely" in reason.lower():
                    # Open-Meteo's per-minute quota: waiting out the minute is enough.
                    last_problem = f"HTTP 429: {reason}"
                    self._wait(attempt, None, minimum=self._retry.minute_limit_wait)
                    continue
                if "limit exceeded" in reason.lower():
                    # A quota (such as Open-Meteo's daily or hourly one) does not clear in this run.
                    raise RateLimitedError(reason)
                last_problem = f"HTTP 429: {reason}"
                self._wait(attempt, response.headers.get("Retry-After"))
                continue
            if response.status_code in _RETRIABLE_STATUS:
                last_problem = f"HTTP {response.status_code}"
                self._wait(attempt, None)
                continue
            error_type = NotFoundError if response.status_code == 404 else SourceUnavailableError
            raise error_type(f"{url} answered HTTP {response.status_code}: {_reason(response)}")
        raise SourceUnavailableError(
            f"{url} failed after {self._retry.max_attempts} attempts ({last_problem})"
        )

    def _wait(self, attempt: int, retry_after: str | None, *, minimum: float = 0.0) -> None:
        if attempt >= self._retry.max_attempts:
            return
        delay = self._retry.delay(attempt)
        if retry_after is not None and retry_after.isdigit():
            delay = min(self._retry.max_delay, max(delay, float(retry_after)))
        self._sleep(max(delay, minimum))

    def close(self) -> None:
        self._client.close()


def _reason(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and isinstance(body.get("reason"), str):
        return str(body["reason"])
    return response.text[:200]
