from dataclasses import dataclass

from app.models import Card, Cube
from app.services.inventory.inventory_service import InventoryService


@dataclass(slots=True)
class MissingCard:
    card: Card
    required: int
    available: int

    @property
    def missing(self) -> int:
        return self.required - self.available


@dataclass(slots=True)
class CubeCheckResult:
    complete: bool
    missing_cards: list[MissingCard]


class CubeCompletenessService:

    def __init__(
        self,
        inventory_service: InventoryService,
    ):
        self.inventory = inventory_service

    def check(
        self,
        cube: Cube,
    ) -> CubeCheckResult:

        missing_cards = []

        for cube_card in cube.cards:
            available = self.inventory.get_quantity(
                cube_card.card
            )

            required = cube_card.quantity

            if available < required:
                missing_cards.append(
                    MissingCard(
                        card=cube_card.card,
                        required=required,
                        available=available,
                    )
                )

        return CubeCheckResult(
            complete=len(missing_cards) == 0,
            missing_cards=missing_cards,
        )
