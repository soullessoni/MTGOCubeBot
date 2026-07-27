import json

import httpx

from bot.api_client import CubeBotApiClient


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        base_url="http://test",
        transport=transport,
    )

    return CubeBotApiClient(
        base_url="http://test",
        client=http_client,
    )


async def test_trigger_give_posts_to_session_give_endpoint():
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)

        return httpx.Response(200, json={"id": 1, "job_type": "GIVE", "status": "PENDING"})

    client = make_client(handler)

    result = await client.trigger_give(7, requested_by="discord:1")

    assert captured["path"] == "/mtgo/sessions/7/give"
    assert captured["body"] == {"requested_by": "discord:1"}
    assert result["job_type"] == "GIVE"


async def test_trigger_return_posts_mtgo_username():
    captured = {}

    def handler(request):
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)

        return httpx.Response(200, json={"id": 2, "job_type": "RETURN", "status": "PENDING"})

    client = make_client(handler)

    result = await client.trigger_return(7, "FruitDuChene", requested_by="discord:1")

    assert captured["path"] == "/mtgo/sessions/7/return"
    assert captured["body"] == {"mtgo_username": "FruitDuChene", "requested_by": "discord:1"}
    assert result["job_type"] == "RETURN"


async def test_trigger_integrity_check():
    def handler(request):
        assert request.url.path == "/mtgo/integrity-check"
        return httpx.Response(200, json={"id": 3, "job_type": "INTEGRITY_CHECK", "status": "PENDING"})

    client = make_client(handler)

    result = await client.trigger_integrity_check(requested_by="discord:1")

    assert result["job_type"] == "INTEGRITY_CHECK"


async def test_trigger_give_back_sends_cards():
    captured = {}

    def handler(request):
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": 4, "job_type": "GIVE_BACK", "status": "PENDING"})

    client = make_client(handler)

    result = await client.trigger_give_back(
        "FruitDuChene",
        {"Mulldrifter": 1},
        requested_by="discord:1",
        retry_of_job_id=2,
    )

    assert captured["body"] == {
        "mtgo_username": "FruitDuChene",
        "cards": {"Mulldrifter": 1},
        "requested_by": "discord:1",
        "retry_of_job_id": 2,
    }
    assert result["job_type"] == "GIVE_BACK"


async def test_retry_job():
    def handler(request):
        assert request.url.path == "/mtgo/jobs/2/retry"
        return httpx.Response(200, json={"id": 5, "job_type": "RETURN", "status": "PENDING", "retry_of_job_id": 2})

    client = make_client(handler)

    result = await client.retry_job(2)

    assert result["retry_of_job_id"] == 2


async def test_get_job():
    def handler(request):
        assert request.url.path == "/mtgo/jobs/5"
        return httpx.Response(200, json={"id": 5, "job_type": "RETURN", "status": "SUCCEEDED"})

    client = make_client(handler)

    result = await client.get_job(5)

    assert result["status"] == "SUCCEEDED"
