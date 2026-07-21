from app.services.cube.cube_import_service import CubeImportService


def test_full_cube_import(db_session):

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

    assert len(cube.cards) > 0
