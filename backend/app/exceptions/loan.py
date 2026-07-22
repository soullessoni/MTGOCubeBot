class CardNotFoundError(Exception):
    def __init__(self, card_name: str):
        self.card_name = card_name

        super().__init__(
            f"Card not found: {card_name}"
        )