import re

import httpx


class CubeCobraClient:

    def __init__(self, cube_url: str):
        self.cube_url = cube_url

    def extract_cube_id(self) -> str:
        match = re.search(
            r"/cube/list/([a-f0-9-]{36})",
            self.cube_url,
        )

        if not match:
            raise ValueError(
                "CubeCobra URL must contain a UUID"
            )

        return match.group(1)

    def download_mtgo_export(self) -> str:

        cube_id = self.extract_cube_id()

        export_url = (
            "https://cubecobra.com/cube/download/mtgo/"
            f"{cube_id}"
            "?boards=mainboard"
        )

        response = httpx.get(
            export_url,
            timeout=30,
        )

        response.raise_for_status()

        return response.text
