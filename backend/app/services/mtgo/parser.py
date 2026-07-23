from app.services.mtgo.models import MTGOCardEntry


class MTGOParser:

    def parse(
        self,
        content: str,
    ) -> list[MTGOCardEntry]:

        cards = []

        for line in content.splitlines():

            line = line.strip()

            if not line:
                continue

            parts = line.split(" ", 1)

            if len(parts) != 2:
                continue

            quantity, name = parts

            try:
                quantity = int(quantity)
            except ValueError:
                continue

            cards.append(
                MTGOCardEntry(
                    name=name.strip(),
                    quantity=quantity,
                )
            )

        return cards