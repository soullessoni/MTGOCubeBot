from unittest.mock import patch

from app.services.mtgo.parser import MTGOCardEntry


def test_create_cube_imports_from_cubecobra(client):
    parsed_cards = [MTGOCardEntry(name="Black Lotus", quantity=1)]

    with patch(
            "app.services.cube.cube_import_service.CubeCobraClient.download_mtgo_export",
            return_value="fake export",
    ), patch(
        "app.services.cube.cube_import_service.MTGOParser.parse",
        return_value=parsed_cards,
    ):
        response = client.post(
            "/cubes/",
            json={
                "name": "Legion Experience",
                "cube_url": "https://cubecobra.com/cube/list/82f27ca5-58ff-4874-84da-7f8bc23e2073",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Legion Experience"
    assert data["active"] is True


def test_create_cube_rejects_bad_url(client):
    response = client.post(
        "/cubes/",
        json={"name": "Bad", "cube_url": "not-a-cubecobra-url"},
    )

    assert response.status_code == 400


def test_list_cubes(client):
    parsed_cards = [MTGOCardEntry(name="Black Lotus", quantity=1)]

    with patch(
            "app.services.cube.cube_import_service.CubeCobraClient.download_mtgo_export",
            return_value="fake export",
    ), patch(
        "app.services.cube.cube_import_service.MTGOParser.parse",
        return_value=parsed_cards,
    ):
        client.post(
            "/cubes/",
            json={
                "name": "Legion Experience",
                "cube_url": "https://cubecobra.com/cube/list/82f27ca5-58ff-4874-84da-7f8bc23e2073",
            },
        )

    response = client.get("/cubes/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Legion Experience"
