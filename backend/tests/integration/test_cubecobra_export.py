from pathlib import Path

import httpx
import pytest


@pytest.mark.integration
def test_download_mtgo_export():
    url = (
        "https://cubecobra.com/cube/download/mtgo/"
        "82f27ca5-58ff-4874-84da-7f8bc23e2073"
        "?primary=Color+Category"
        "&secondary=Types-Multicolor"
        "&tertiary=Mana+Value"
        "&quaternary=Alphabetical"
        "&boards=mainboard"
    )

    response = httpx.get(url)

    response.raise_for_status()

    Path(
        "cubecobra_mtgo_export.txt"
    ).write_text(
        response.text,
        encoding="utf-8",
    )

    assert response.text
