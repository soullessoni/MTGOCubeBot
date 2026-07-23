class MTGODeckParser:
    """
    Parser for MTGO formatted deck lists.

    Expected format:
    <quantity> <card name>

    Example:
    4 Lightning Bolt
    """

    def parse(
        self,
        text: str,
    ) -> list[str]:
        cards = []

        for line_number, line in enumerate(
            text.splitlines(),
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            parts = line.split(
                " ",
                maxsplit=1,
            )

            if len(parts) != 2:
                raise ValueError(
                    f"Invalid MTGO deck line {line_number}: {line}"
                )

            quantity_text, card_name = parts

            try:
                quantity = int(quantity_text)
            except ValueError:
                raise ValueError(
                    f"Invalid quantity on line {line_number}: {line}"
                )

            if quantity <= 0:
                raise ValueError(
                    f"Invalid quantity on line {line_number}: {line}"
                )

            for _ in range(quantity):
                cards.append(card_name)

        return cards