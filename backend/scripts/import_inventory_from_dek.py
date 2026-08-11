"""One-off bootstrap: sync the inventory table to a real MTGO Full Trade
List export — the authoritative record of what the bot actually owns.
Cards in the export are created/updated to their real quantity; any
card currently in inventory but absent from the export is zeroed out
(stale/test data, e.g. leftover placeholder cards from development).

Usage:
  .venv/Scripts/python.exe scripts/import_inventory_from_dek.py <cube_instance_id> <path-to-dek>

Typically run against agent/mtgo/lists/full_trade_list.dek (gitignored
real collection data, not checked in). `cube_instance_id` identifies
which account/cube-copy pool this export belongs to (see
`GET /cube-instances/` — or the mtgo_accounts/cube_instances tables
directly until that endpoint exists).
"""

import sys
from pathlib import Path

from app.db.database import SessionLocal
from app.services.inventory.dek_parser import parse_dek_quantities
from app.services.inventory.inventory_import_service import InventoryImportService


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/import_inventory_from_dek.py <cube_instance_id> <path-to-dek>")
        return 1

    cube_instance_id = int(sys.argv[1])
    dek_path = Path(sys.argv[2])

    if not dek_path.exists():
        print(f"File not found: {dek_path}")
        return 1

    quantities = parse_dek_quantities(dek_path)
    print(f"Parsed {len(quantities)} distinct card(s) from {dek_path}, "
          f"{sum(quantities.values())} total copies.")

    db = SessionLocal()

    try:
        service = InventoryImportService(db)
        result = service.import_quantities(cube_instance_id, quantities)
    finally:
        db.close()

    print(f"Created {len(result['created_cards'])} new card(s).")
    if result["created_cards"]:
        for name in sorted(result["created_cards"])[:20]:
            print(f"  + {name}")
        if len(result["created_cards"]) > 20:
            print(f"  ... and {len(result['created_cards']) - 20} more")

    print(f"Updated {result['updated_count']} card(s) to their real quantity.")

    print(f"Zeroed out {len(result['zeroed_names'])} stale card(s) not in the export.")
    if result["zeroed_names"]:
        for name in sorted(result["zeroed_names"]):
            print(f"  - {name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
