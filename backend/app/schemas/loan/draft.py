from pydantic import BaseModel


class DraftPlayerPool(BaseModel):
    player_name: str
    cards: list[str]


class CreateLoanSessionFromDraftRequest(BaseModel):
    players: list[DraftPlayerPool]

class CreateLoanSessionFromDraftUrlRequest(BaseModel):
    draft_url: str
    player_name: str