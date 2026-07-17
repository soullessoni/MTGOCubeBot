from app.services.mtgo.parser import MTGOParser


def test_parse_mtgo_export():

    content = """
    1 Black Lotus
    1 Ancestral Recall
    2 Island
    """

    parser = MTGOParser()

    cards = parser.parse(content)

    assert len(cards) == 3

    assert cards[0].name == "Black Lotus"
    assert cards[0].quantity == 1

    assert cards[2].name == "Island"
    assert cards[2].quantity == 2