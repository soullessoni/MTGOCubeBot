from pathlib import Path
from xml.etree import ElementTree


def parse_dek_quantities(dek_path: Path) -> dict[str, int]:
    """Parse a .dek file's `<Cards Name="..." Quantity="..." />` entries
    into a `{name: total_quantity}` mapping, summing across entries for
    the same name (a name can appear more than once if the account owns
    it under more than one CatID/printing).

    Duplicated from agent/mtgo/stock_check.py's function of the same
    name — the backend and the agent are separate Python projects with
    independent venvs, so this can't be a shared import. Keep both in
    sync if the .dek schema handling ever changes."""
    root = ElementTree.parse(dek_path).getroot()
    totals: dict[str, int] = {}

    for card in root.findall("Cards"):
        name = card.get("Name")
        quantity = card.get("Quantity")

        if not name or quantity is None:
            continue

        totals[name] = totals.get(name, 0) + int(quantity)

    return totals
