import pytest

from app.services.cubecobra.importer import CubeCobraImporter


@pytest.mark.integration
def test_fetch_cube():
    importer = CubeCobraImporter(
        "https://cubecobra.com/cube/list/legion-experience"
    )

    html = importer.fetch()

    assert html
