from app.models.cube_instance import CubeInstance


class CubeInstanceService:

    def __init__(
            self,
            db,
    ):
        self.db = db

    def create(
            self,
            cube_id: int,
            mtgo_account_id: int,
            label: str,
    ) -> CubeInstance:
        instance = CubeInstance(
            cube_id=cube_id,
            mtgo_account_id=mtgo_account_id,
            label=label,
        )

        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        return instance

    def get(
            self,
            instance_id: int,
    ) -> CubeInstance | None:
        return (
            self.db.query(CubeInstance)
            .filter(
                CubeInstance.id == instance_id
            )
            .first()
        )

    def list_for_account(
            self,
            mtgo_account_id: int,
    ) -> list[CubeInstance]:
        return (
            self.db.query(CubeInstance)
            .filter(
                CubeInstance.mtgo_account_id == mtgo_account_id
            )
            .all()
        )

    def list_for_cube(
            self,
            cube_id: int,
    ) -> list[CubeInstance]:
        return (
            self.db.query(CubeInstance)
            .filter(
                CubeInstance.cube_id == cube_id
            )
            .all()
        )

    def set_active(
            self,
            instance: CubeInstance,
            active: bool,
    ) -> CubeInstance:
        instance.active = active

        self.db.commit()
        self.db.refresh(instance)

        return instance
