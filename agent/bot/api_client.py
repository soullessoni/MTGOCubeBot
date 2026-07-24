import httpx


class CubeBotApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

        super().__init__(
            f"CubeBot API error {status_code}: {detail}"
        )


class CubeBotApiClient:
    """Async HTTP client for the backend, used from Discord.py callbacks.

    Must stay async (httpx.AsyncClient, not httpx.Client) — a blocking
    sync call here would freeze the bot's single-threaded event loop for
    the duration of the request, which can make Discord interactions miss
    their 3-second response deadline ("app didn't respond") if it lines
    up with another task (e.g. the cleanup loop) also mid-request.
    """

    def __init__(
            self,
            base_url: str,
            client: httpx.AsyncClient | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10.0,
        )

    async def get_session(self, session_id: int) -> dict:
        return await self._request(
            "GET",
            f"/loan/sessions/{session_id}",
        )

    async def list_sessions(self) -> list[dict]:
        return await self._request(
            "GET",
            "/loan/sessions/",
        )

    async def link_discord_identity(
            self,
            assignment_id: int,
            discord_user_id: str,
            mtgo_username: str,
    ) -> dict:
        return await self._request(
            "PATCH",
            f"/loan/sessions/assignments/{assignment_id}/discord",
            json={
                "discord_user_id": discord_user_id,
                "mtgo_username": mtgo_username,
            },
        )

    async def confirm_assignment(self, assignment_id: int) -> dict:
        return await self._request(
            "POST",
            f"/loan/sessions/assignments/{assignment_id}/confirm",
        )

    async def return_assignment(self, assignment_id: int) -> dict:
        return await self._request(
            "POST",
            f"/loan/sessions/assignments/{assignment_id}/return",
        )

    async def _request(
            self,
            method: str,
            path: str,
            **kwargs,
    ) -> dict | list:
        response = await self._client.request(method, path, **kwargs)

        if response.status_code >= 400:
            detail = response.text

            if response.content:
                try:
                    detail = response.json().get("detail", response.text)
                except ValueError:
                    pass

            raise CubeBotApiError(response.status_code, detail)

        return response.json()

    async def close(self):
        await self._client.aclose()
