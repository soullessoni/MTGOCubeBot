from dataclasses import dataclass


@dataclass
class MTGOCardEntry:
    name: str
    quantity: int