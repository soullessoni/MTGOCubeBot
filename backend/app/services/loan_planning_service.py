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


class LoanPlanningService:

    def generate(
        self,
        player_pools: list[PlayerPool],
    ) -> list[LoanRequest]:

        requests: list[LoanRequest] = []

        for pool in player_pools:
            requests.append(
                LoanRequest(
                    player_name=pool.player_name,
                    requested_cards=list(pool.cards),
                )
            )

        return requests