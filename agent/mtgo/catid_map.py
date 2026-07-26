"""Name -> CatID lookup built from a real MTGO .dek export (e.g. the
bot account's own "Full Trade List"), so binder imports can reference
the exact edition/printing the account actually owns.

Why this matters: importing a binder .dek with `CatID="0"` makes MTGO
resolve each card by name alone, and it picks the *most recent*
printing of that name — even when the account's actual copy is a
different edition. The binder then reports the full requested count
(since that's just the number of XML lines) but only actually exposes
whichever cards happened to resolve to an edition the account owns
zero-or-more of. Confirmed live 2026-07-25: a 58-card binder imported
this way only offered 27 cards in a real trade, and every "missing"
card was independently confirmed present in the account's real
Full Trade List — just under a different CatID/edition than the one
CatID="0" resolution picked.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

DEFAULT_CATID_MAP_PATH = Path(__file__).parent / "lists" / "full_trade_list.dek"


def parse_catid_map(dek_path: Path) -> dict[str, str]:
    """Parse a .dek file's `<Cards CatID="..." Name="..." />` entries
    into a `{name: catid}` mapping."""
    root = ElementTree.parse(dek_path).getroot()
    return {
        card.get("Name"): card.get("CatID")
        for card in root.findall("Cards")
        if card.get("Name") and card.get("CatID")
    }


def load_default_catid_map() -> dict[str, str]:
    """Load the mapping from `DEFAULT_CATID_MAP_PATH`, or return an
    empty mapping if that file hasn't been provided yet (callers then
    fall back to `CatID="0"` name-only resolution, the old behavior)."""
    if not DEFAULT_CATID_MAP_PATH.exists():
        return {}
    return parse_catid_map(DEFAULT_CATID_MAP_PATH)
