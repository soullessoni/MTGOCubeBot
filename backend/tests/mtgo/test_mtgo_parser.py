from app.services.mtgo.parser import (
    MTGOParser,
    MTGOCardEntry,
)


def test_parse_simple_deck():
    parser = MTGOParser()

    cards = parser.parse(
        """
        1 Lightning Bolt
        1 Brainstorm
        """
    )

    assert cards == [
        MTGOCardEntry(
            name="Lightning Bolt",
            quantity=1,
        ),
        MTGOCardEntry(
            name="Brainstorm",
            quantity=1,
        ),
    ]


def test_parse_quantity():
    parser = MTGOParser()

    cards = parser.parse(
        """
        4 Snow-Covered Island
        """
    )

    assert cards == [
        MTGOCardEntry(
            name="Snow-Covered Island",
            quantity=4,
        )
    ]


def test_ignore_empty_lines():
    parser = MTGOParser()

    cards = parser.parse(
        """
        1 Lightning Bolt


        1 Brainstorm
        """
    )

    assert cards == [
        MTGOCardEntry(
            name="Lightning Bolt",
            quantity=1,
        ),
        MTGOCardEntry(
            name="Brainstorm",
            quantity=1,
        ),
    ]


def test_parse_sideboard_together():
    parser = MTGOParser()

    cards = parser.parse(
        """
        1 Lightning Bolt

        1 Counterspell
        """
    )

    assert cards == [
        MTGOCardEntry(
            name="Lightning Bolt",
            quantity=1,
        ),
        MTGOCardEntry(
            name="Counterspell",
            quantity=1,
        ),
    ]


def test_invalid_line_without_quantity():
    parser = MTGOParser()

    cards = parser.parse(
        """
        Lightning Bolt
        1 Brainstorm
        """
    )

    assert cards == [
        MTGOCardEntry(
            name="Brainstorm",
            quantity=1,
        )
    ]