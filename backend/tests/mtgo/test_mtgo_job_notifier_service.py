import json

import httpx

from app.core.notification_config import NotificationConfig
from app.models.mtgo_job import MtgoJob
from app.services.mtgo.mtgo_job_notifier_service import (
    MtgoJobNotifierService,
    build_notification_message,
)

FAKE_WEBHOOK_URL = "https://discord.com/api/webhooks/test/test"


def _make_job(**overrides) -> MtgoJob:
    defaults = dict(
        id=1,
        job_type="GIVE",
        status="SUCCEEDED",
        session_id=1,
        mtgo_username="FruitDuChene",
        result=None,
        error_message=None,
    )
    defaults.update(overrides)
    return MtgoJob(**defaults)


def test_failed_job_message_contains_error():
    job = _make_job(
        job_type="GIVE",
        status="FAILED",
        error_message="MTGO window not found.",
    )

    message = build_notification_message(job)

    assert message is not None
    assert "MTGO window not found." in message
    assert f"#{job.id}" in message


def test_failed_job_without_error_message_uses_fallback():
    job = _make_job(
        status="FAILED",
        error_message=None,
    )

    message = build_notification_message(job)

    assert message is not None
    assert "erreur inconnue" in message


def test_succeeded_return_with_still_owed_describes_discrepancy():
    job = _make_job(
        job_type="RETURN",
        status="SUCCEEDED",
        result={
            "ok": False,
            "reconciliation": {
                "still_owed": {"Mulldrifter": 1},
                "to_give_back": {},
            },
        },
    )

    message = build_notification_message(job)

    assert message is not None
    assert "Mulldrifter" in message
    assert "RETURN" in message


def test_succeeded_return_with_to_give_back_describes_discrepancy():
    job = _make_job(
        job_type="RETURN",
        status="SUCCEEDED",
        result={
            "ok": False,
            "reconciliation": {
                "still_owed": {},
                "to_give_back": {"Brainstorm": 2},
            },
        },
    )

    message = build_notification_message(job)

    assert message is not None
    assert "Brainstorm" in message


def test_succeeded_return_with_no_discrepancy_returns_none():
    job = _make_job(
        job_type="RETURN",
        status="SUCCEEDED",
        result={
            "ok": True,
            "reconciliation": {"still_owed": {}, "to_give_back": {}},
        },
    )

    message = build_notification_message(job)

    assert message is None


def test_succeeded_integrity_check_with_discrepancy_describes_it():
    job = _make_job(
        job_type="INTEGRITY_CHECK",
        status="SUCCEEDED",
        session_id=None,
        result={
            "ok": False,
            "missing": {"Lightning Bolt": 1},
            "extra": {"Counterspell": 1},
        },
    )

    message = build_notification_message(job)

    assert message is not None
    assert "Lightning Bolt" in message
    assert "Counterspell" in message


def test_succeeded_integrity_check_clean_returns_none():
    job = _make_job(
        job_type="INTEGRITY_CHECK",
        status="SUCCEEDED",
        session_id=None,
        result={"ok": True, "missing": {}, "extra": {}},
    )

    message = build_notification_message(job)

    assert message is None


def test_succeeded_give_returns_none():
    job = _make_job(
        job_type="GIVE",
        status="SUCCEEDED",
        result={"ok": True},
    )

    message = build_notification_message(job)

    assert message is None


def test_succeeded_give_with_not_taken_describes_it():
    job = _make_job(
        job_type="GIVE",
        status="SUCCEEDED",
        result={
            "ok": False,
            "given": {"FruitDuChene": {}},
            "not_taken": {"FruitDuChene": {"Wingcrafter": 1}},
            "deposits_collected": {},
            "failed": {},
            "skipped_no_username": [],
        },
    )

    message = build_notification_message(job)

    assert message is not None
    assert "FruitDuChene" in message
    assert "Wingcrafter" in message


def test_succeeded_give_all_taken_returns_none():
    job = _make_job(
        job_type="GIVE",
        status="SUCCEEDED",
        result={
            "ok": True,
            "given": {"FruitDuChene": {"Wingcrafter": 1}},
            "not_taken": {},
            "deposits_collected": {"FruitDuChene": 5},
            "failed": {},
            "skipped_no_username": [],
        },
    )

    message = build_notification_message(job)

    assert message is None


def test_succeeded_give_back_returns_none():
    job = _make_job(
        job_type="GIVE_BACK",
        status="SUCCEEDED",
        result={"ok": True},
    )

    message = build_notification_message(job)

    assert message is None


def make_notifier(handler, webhook_url=FAKE_WEBHOOK_URL) -> MtgoJobNotifierService:
    transport = httpx.MockTransport(handler)
    notifier = MtgoJobNotifierService(
        NotificationConfig(webhook_url=webhook_url),
    )
    notifier.client = httpx.Client(transport=transport)
    return notifier


def test_notify_posts_message_when_job_needs_notification():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(204)

    notifier = make_notifier(handler)
    job = _make_job(status="FAILED", error_message="boom")

    notifier.notify(job)

    assert captured["url"] == FAKE_WEBHOOK_URL
    assert "boom" in captured["body"]["content"]


def test_notify_does_not_post_for_clean_job():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(204)

    notifier = make_notifier(handler)
    job = _make_job(job_type="GIVE", status="SUCCEEDED", result={"ok": True})

    notifier.notify(job)

    assert calls == []


def test_notify_skips_when_webhook_not_configured():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(204)

    notifier = make_notifier(handler, webhook_url=None)
    job = _make_job(status="FAILED", error_message="boom")

    notifier.notify(job)

    assert calls == []


def test_notify_swallows_transport_errors():
    def handler(request):
        raise httpx.ConnectError("connection refused", request=request)

    notifier = make_notifier(handler)
    job = _make_job(status="FAILED", error_message="boom")

    notifier.notify(job)


def test_notify_swallows_error_status_responses():
    def handler(request):
        return httpx.Response(500, text="internal error")

    notifier = make_notifier(handler)
    job = _make_job(status="FAILED", error_message="boom")

    notifier.notify(job)
