import json

import httpx
import pytest

from bot.api_client import CubeBotApiClient, CubeBotApiError


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(
        base_url="http://test",
        transport=transport,
    )

    return CubeBotApiClient(
        base_url="http://test",
        client=http_client,
    )


def test_get_session():
    def handler(request):
        assert request.url.path == "/loan/sessions/1"

        return httpx.Response(
            200,
            json={
                "id": 1,
                "status": "CREATED",
                "assignments": [],
            },
        )

    client = make_client(handler)

    result = client.get_session(1)

    assert result["id"] == 1


def test_list_sessions():
    def handler(request):
        assert request.url.path == "/loan/sessions/"

        return httpx.Response(
            200,
            json=[
                {"id": 1, "status": "CREATED", "assignments": []},
                {"id": 2, "status": "COMPLETED", "assignments": []},
            ],
        )

    client = make_client(handler)

    result = client.list_sessions()

    assert len(result) == 2
    assert result[0]["id"] == 1


def test_link_discord_identity_sends_payload():
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)

        return httpx.Response(
            200,
            json={
                "id": 5,
                "discord_user_id": "42",
                "mtgo_username": "Alice",
            },
        )

    client = make_client(handler)

    result = client.link_discord_identity(5, "42", "Alice")

    assert captured["path"] == "/loan/sessions/assignments/5/discord"
    assert captured["body"] == {
        "discord_user_id": "42",
        "mtgo_username": "Alice",
    }
    assert result["mtgo_username"] == "Alice"


def test_confirm_assignment():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/loan/sessions/assignments/7/confirm"

        return httpx.Response(
            200,
            json={
                "id": 7,
                "status": "CONFIRMED",
            },
        )

    client = make_client(handler)

    result = client.confirm_assignment(7)

    assert result["status"] == "CONFIRMED"


def test_return_assignment():
    def handler(request):
        assert request.url.path == "/loan/sessions/assignments/7/return"

        return httpx.Response(
            200,
            json={
                "id": 7,
                "status": "RETURNED",
            },
        )

    client = make_client(handler)

    result = client.return_assignment(7)

    assert result["status"] == "RETURNED"


def test_raises_on_error_response():
    def handler(request):
        return httpx.Response(
            404,
            json={
                "detail": "Loan assignment not found",
            },
        )

    client = make_client(handler)

    with pytest.raises(CubeBotApiError) as exc_info:
        client.confirm_assignment(999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Loan assignment not found"
