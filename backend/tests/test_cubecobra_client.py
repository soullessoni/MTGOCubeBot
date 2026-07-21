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
