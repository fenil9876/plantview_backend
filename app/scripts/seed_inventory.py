"""Seed the initial inventory items.

Usage:
    python -m app.scripts.seed_inventory

Idempotent: existing items (by name) are left unchanged.
"""
from app.core.database import SessionLocal
from app.models.inventory import InventoryItem
from app.services import inventory_service

DEFAULT_ITEMS = [
    "Elastic",
    "Spun Yarn",
    "Cotton Yarn",
    "CTH Cotton",
    "Polyester Lycra",
    "Nylon Lycra",
]


def main() -> int:
    db = SessionLocal()
    created = 0
    try:
        for name in DEFAULT_ITEMS:
            if inventory_service.get_by_name(db, name):
                continue
            db.add(InventoryItem(name=name, quantity=0.0, unit="kg"))
            created += 1
        db.commit()
    finally:
        db.close()
    print(f"Seeded inventory: {created} new item(s), {len(DEFAULT_ITEMS) - created} already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
