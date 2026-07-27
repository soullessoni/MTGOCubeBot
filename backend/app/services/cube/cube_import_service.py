from sqlalchemy.orm import Session

from app.models import Card, Cube, CubeCard
from app.services.cubecobra.client import CubeCobraClient
from app.services.mtgo.parser import MTGOParser

class CubeImportService:

    def __init__(self, db: Session):
        self.db = db

    def import_cube(
            self,
            cube_url: str,
            name: str,
    ) -> Cube:

        client = CubeCobraClient(
            cube_url
        )

        export = client.download_mtgo_export()

        parser = MTGOParser()
        
        cards = parser.parse(
            export
        )

        cube = Cube(
            name=name,
            cubecobra_url=cube_url,
        )

        self.db.add(cube)
        self.db.flush()

        existing_cards = {
            existing.name: existing
            for existing in self.db.query(Card).all()
        }

        for entry in cards:

            card = existing_cards.get(entry.name)

            if not card:
                card = Card(
                    name=entry.name
                )

                self.db.add(card)
                self.db.flush()
                existing_cards[entry.name] = card

            cube_card = CubeCard(
                cube_id=cube.id,
                card_id=card.id,
                quantity=entry.quantity,
            )

            self.db.add(cube_card)

        self.db.commit()
        self.db.refresh(cube)

        return cube
