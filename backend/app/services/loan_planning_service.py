from dataclasses import dataclass

from app.models.card import Card


@dataclass
class PlayerPool:
    player_name: str
    cards: list[Card]


@dataclass
class LoanRequest:
    player_name: str
    requested_cards: list[Card]


@dataclass
class LoanConflict:
    card: Card
    players: list[str]
    required: int
    available: int


@dataclass
class LoanPlanningResult:
    requests: list[LoanRequest]
    conflicts: list[LoanConflict]

    @property
    def valid(self) -> bool:
        return len(self.conflicts) == 0


class LoanPlanningService:

    def __init__(self, inventory_service):
        self.inventory = inventory_service

    def generate(
        self,
        pools: list[PlayerPool],
    ) -> LoanPlanningResult:

        requests = []
        conflicts = []

        card_usage: dict[str, list[str]] = {}
        cards_by_name: dict[str, Card] = {}

        # Génération des demandes et index des cartes
        for pool in pools:
            requests.append(
                LoanRequest(
                    player_name=pool.player_name,
                    requested_cards=pool.cards,
                )
            )

            for card in pool.cards:
                cards_by_name[card.name] = card

                card_usage.setdefault(
                    card.name,
                    [],
                ).append(
                    pool.player_name
                )

        # Détection des conflits d'inventaire
        for card_name, players in card_usage.items():

            card = cards_by_name[card_name]

            available = self.inventory.get_quantity(card)

            if len(players) > available:
                conflicts.append(
                    LoanConflict(
                        card=card,
                        players=players,
                        required=len(players),
                        available=available,
                    )
                )

        return LoanPlanningResult(
            requests=requests,
            conflicts=conflicts,
        )