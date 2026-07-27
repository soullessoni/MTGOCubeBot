from unittest.mock import patch

from sqlalchemy import event

from app.models.card import Card
from app.models.cube_card import CubeCard
from app.services.cube.cube_import_service import (
    CubeImportService,
)
from app.services.mtgo.parser import MTGOCardEntry


def test_create_cube(db_session):
    parsed_cards = [
        MTGOCardEntry(
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


def test_import_reuses_existing_card_by_name(db_session):
    existing = Card(name="Black Lotus")
    db_session.add(existing)
    db_session.commit()

    parsed_cards = [
        MTGOCardEntry(name="Black Lotus", quantity=1),
        MTGOCardEntry(name="Ancestral Recall", quantity=1),
    ]

    with patch(
            "app.services.cube.cube_import_service.CubeCobraClient.download_mtgo_export",
            return_value="fake export",
    ), patch(
        "app.services.cube.cube_import_service.MTGOParser.parse",
        return_value=parsed_cards,
    ):
        service = CubeImportService(db_session)
        cube = service.import_cube(
            cube_url="https://cubecobra.com/cube/list/reuse",
            name="Reuse Test",
        )

    assert db_session.query(Card).filter(Card.name == "Black Lotus").count() == 1

    card_ids = {
        cube_card.card_id
        for cube_card in db_session.query(CubeCard).filter(CubeCard.cube_id == cube.id)
    }
    assert card_ids == {
        db_session.query(Card).filter(Card.name == "Black Lotus").one().id,
        db_session.query(Card).filter(Card.name == "Ancestral Recall").one().id,
    }


def test_import_does_not_query_card_table_once_per_entry(db_session):
    parsed_cards = [
        MTGOCardEntry(name=f"Card {i}", quantity=1)
        for i in range(20)
    ]

    with patch(
            "app.services.cube.cube_import_service.CubeCobraClient.download_mtgo_export",
            return_value="fake export",
    ), patch(
        "app.services.cube.cube_import_service.MTGOParser.parse",
        return_value=parsed_cards,
    ):
        service = CubeImportService(db_session)

        engine = db_session.get_bind()
        select_count = 0

        def _count_select(conn, cursor, statement, *args, **kwargs):
            nonlocal select_count
            if statement.strip().upper().startswith("SELECT"):
                select_count += 1

        event.listen(engine, "before_cursor_execute", _count_select)
        try:
            service.import_cube(
                cube_url="https://cubecobra.com/cube/list/bulk",
                name="Bulk Test",
            )
        finally:
            event.remove(engine, "before_cursor_execute", _count_select)

    # Previously: one SELECT on the cards table per parsed entry (20).
    # A single preload query up front must not scale with the card
    # count — inserts for the 20 new cards are a separate concern.
    assert select_count <= 2
