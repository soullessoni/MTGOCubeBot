from unittest.mock import patch

from app.services.cube.cube_import_service import (
    CubeImportService,
)
from app.services.mtgo.parser import CardEntry


def test_create_cube(db_session):

    parsed_cards = [
        CardEntry(
            name="Black Lotus",
            quantity=1,
        ),
    ]

    with patch(
        "app.services.cube.cube_import_service.CubeCobraClient.download_mtgo_export",
        return_value="fake export",
    ), patch(
        "app.services.cube.cube_import_service.MTGOParser.parse",
        return_value=parsed_cards,
    ):

        service = CubeImportService(
            db_session
        )

        cube = service.import_cube(
            cube_url=(
                "https://cubecobra.com/cube/list/"
                "82f27ca5-58ff-4874-84da-7f8bc23e2073"
            ),
            name="Legion Experience",
        )

    assert cube.id is not None
    assert cube.name == "Legion Experience"

    assert cube.cubecobra_url == (
        "https://cubecobra.com/cube/list/"
        "82f27ca5-58ff-4874-84da-7f8bc23e2073"
    )