from app.services.cubecobra.client import CubeCobraClient


def test_extract_cube_id():
    client = CubeCobraClient(
        "https://cubecobra.com/cube/list/"
        "82f27ca5-58ff-4874-84da-7f8bc23e2073"
    )

    cube_id = client.extract_cube_id()

    assert cube_id == (
        "82f27ca5-58ff-4874-84da-7f8bc23e2073"
    )

def test_extract_deck_id():
    client = CubeCobraClient(
        "https://cubecobra.com/cube/deck/"
        "ce8aee4f-f480-4ae2-82ad-a385571aee90"
    )

    deck_id = client.extract_deck_id()

    assert deck_id == (
        "ce8aee4f-f480-4ae2-82ad-a385571aee90"
    )

import httpx
import pytest

from app.services.cubecobra.client import CubeCobraClient


def test_download_deck_mtgo_export(monkeypatch):

    called = {}

    class FakeResponse:

        text = (
            "1 Lightning Bolt\n"
            "1 Brainstorm\n"
        )

        def raise_for_status(self):
            pass

    def fake_get(url, timeout):

        called["url"] = url
        called["timeout"] = timeout

        return FakeResponse()

    monkeypatch.setattr(
        httpx,
        "get",
        fake_get,
    )

    client = CubeCobraClient(
        "https://cubecobra.com/cube/deck/"
        "ce8aee4f-f480-4ae2-82ad-a385571aee90"
    )

    export = client.download_deck_mtgo_export()

    assert export == (
        "1 Lightning Bolt\n"
        "1 Brainstorm\n"
    )

    assert called["url"] == (
        "https://cubecobra.com/cube/download/mtgo/"
        "ce8aee4f-f480-4ae2-82ad-a385571aee90"
        "?boards=mainboard"
    )

    assert called["timeout"] == 30