from dataclasses import dataclass

from app.models.card import Card


@dataclass
class RequestedCard:
    card: Card
    quantity: int


@dataclass
class PlayerPool:
    player_name: str
    cards: list[Card]


@dataclass
class LoanRequest:
    player_name: str
    requested_cards: list[RequestedCard]

    @property
    def card(self):
        return self.requested_cards[0].card


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
    def valid(self):
        return len(self.conflicts) == 0

    def __len__(self):
        return len(self.requests)

    def __getitem__(self, index):
        return self.requests[index]

    def __iter__(self):
        return iter(self.requests)

    def __eq__(self, other):
        if isinstance(other, list):
            return self.requests == other

        return super().__eq__(other)


class LoanPlanningService:

    def __init__(
        self,
        inventory_service,
    ):
        self.inventory_service = inventory_service

    def generate(
        self,
        pools,
    ) -> LoanPlanningResult:

        requests = []
        conflicts = []

        card_usage = {}
        cards_by_name = {}

        if isinstance(pools, dict):
            pools = [
                PlayerPool(
                    player_name=name,
                    cards=cards,
                )
                for name, cards in pools.items()
            ]

        for pool in pools:

            for card in pool.cards:

                requests.append(
                    LoanRequest(
                        player_name=pool.player_name,
                        requested_cards=[
                            RequestedCard(
                                card=card,
                                quantity=1,
                            )
                        ],
                    )
                )

                cards_by_name[card.name] = card

                card_usage.setdefault(
                    card.name,
                    [],
                )

                card_usage[card.name].append(
                    pool.player_name
                )

        for card_name, players in card_usage.items():

            if len(players) > 1:

                card = cards_by_name[card_name]

                if hasattr(
                        self.inventory_service,
                        "get_quantity",
                ):
                    available = self.inventory_service.get_quantity(card)

                else:
                    available = (
                        self.inventory_service.get_available_quantity(card)
                        if hasattr(
                            self.inventory_service,
                            "get_available_quantity",
                        )
                        else 0
                    )
                    
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