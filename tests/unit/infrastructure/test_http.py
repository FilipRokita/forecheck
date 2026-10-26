import httpx
import pytest
import respx

from forecheck.application.errors import RateLimitedError, SourceUnavailableError
from forecheck.infrastructure.http import HttpClient, RetryPolicy

URL = "https://provider.test/data"


def client(sleeps: list[float]) -> HttpClient:
    return HttpClient(
        user_agent="test", retry=RetryPolicy(max_attempts=4, base_delay=2.0), sleep=sleeps.append
    )


@respx.mock
def test_a_successful_call_returns_the_json() -> None:
    respx.get(URL).respond(200, json={"ok": True})
    assert client([]).get_json(URL) == {"ok": True}


@respx.mock
def test_the_user_agent_and_query_are_sent() -> None:
    route = respx.get(URL).respond(200, json={})
    client([]).get_json(URL, {"latitude": 50.1})
    assert route.calls.last.request.headers["user-agent"] == "test"
    assert route.calls.last.request.url.params["latitude"] == "50.1"


@respx.mock
def test_server_errors_are_retried_with_growing_waits() -> None:
    route = respx.get(URL).mock(
        side_effect=[httpx.Response(503), httpx.Response(502), httpx.Response(200, json={"ok": 1})]
    )
    sleeps: list[float] = []
    assert client(sleeps).get_json(URL) == {"ok": 1}
    assert route.call_count == 3
    assert sleeps == [2.0, 4.0]


@respx.mock
def test_a_dropped_connection_is_retried() -> None:
    respx.get(URL).mock(
        side_effect=[httpx.ConnectError("reset"), httpx.Response(200, json={"ok": 1})]
    )
    assert client([]).get_json(URL) == {"ok": 1}


@respx.mock
def test_a_too_many_requests_answer_honours_retry_after() -> None:
    respx.get(URL).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "9"}, json={"reason": "slow down"}),
            httpx.Response(200, json={}),
        ]
    )
    sleeps: list[float] = []
    client(sleeps).get_json(URL)
    assert sleeps == [9.0]


@respx.mock
def test_an_exhausted_quota_is_not_retried() -> None:
    route = respx.get(URL).respond(
        429,
        json={
            "error": True,
            "reason": "Daily API request limit exceeded. Please try again tomorrow.",
        },
    )
    sleeps: list[float] = []
    with pytest.raises(RateLimitedError, match="Daily API request limit"):
        client(sleeps).get_json(URL)
    assert route.call_count == 1
    assert sleeps == []


@respx.mock
def test_giving_up_names_the_last_problem() -> None:
    route = respx.get(URL).respond(503)
    with pytest.raises(SourceUnavailableError, match=r"4 attempts.*HTTP 503"):
        client([]).get_json(URL)
    assert route.call_count == 4


@respx.mock
def test_a_client_error_is_reported_with_the_providers_reason_and_not_retried() -> None:
    route = respx.get(URL).respond(400, json={"error": True, "reason": "Invalid value: nope"})
    with pytest.raises(SourceUnavailableError, match="HTTP 400: Invalid value: nope"):
        client([]).get_json(URL)
    assert route.call_count == 1


@respx.mock
def test_a_body_that_is_not_json_is_an_error() -> None:
    respx.get(URL).respond(200, text="<html>maintenance</html>")
    with pytest.raises(SourceUnavailableError, match="did not return JSON"):
        client([]).get_json(URL)


@respx.mock
def test_bytes_and_text_are_returned_as_they_are() -> None:
    respx.get(URL).respond(200, content=b"\x00\x01")
    assert client([]).get_bytes(URL) == b"\x00\x01"
    respx.get(URL).respond(200, text="hello")
    assert client([]).get_text(URL) == "hello"
