from dataclasses import dataclass


@dataclass
class CardEntry:
    name: str
    quantity: int


class MTGOParser:

    def parse(self, content: str) -> list[CardEntry]:

        cards = []

        for line in content.splitlines():

            line = line.strip()

            if not line:
                continue

            parts = line.split(" ", 1)

            if len(parts) != 2:
                continue

            quantity, name = parts

            cards.append(
                CardEntry(
                    name=name.strip(),
                    quantity=int(quantity),
                )
            )

        return cards