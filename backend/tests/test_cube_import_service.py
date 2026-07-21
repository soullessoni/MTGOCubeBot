from app.services.cube.cube_import_service import CubeImportService


def test_create_cube(db_session):

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
    assert cube.cubecobra_url.startswith(
        "https://cubecobra.com"
    )
