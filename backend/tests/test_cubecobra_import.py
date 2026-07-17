from pathlib import Path

from app.services.cubecobra.importer import CubeCobraImporter


def test_fetch_cube():
    importer = CubeCobraImporter(
        "https://cubecobra.com/cube/list/legion-experience"
    )

    html = importer.fetch()

    Path("cubecobra_debug.html").write_text(
        html,
        encoding="utf-8",
    )

    assert html