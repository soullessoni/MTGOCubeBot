import httpx


class CubeCobraImporter:

    def __init__(self, url: str):
        self.url = url

    def fetch(self) -> str:
        response = httpx.get(
            self.url,
            timeout=30,
        )

        response.raise_for_status()

        return response.text
