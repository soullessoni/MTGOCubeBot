import httpx


class CubeBotApiError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

        super().__init__(
            f"CubeBot API error {status_code}: {detail}"
        )


class CubeBotApiClient:

    def __init__(
            self,
            base_url: str,
            client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(
            base_url=self.base_url,
            timeout=10.0,
        )

    def get_session(self, session_id: int) -> dict:
        return self._request(
            "GET",
            f"/loan/sessions/{session_id}",
        )

    def list_sessions(self) -> list[dict]:
        return self._request(
            "GET",
            "/loan/sessions/",
        )

    def link_discord_identity(
            self,
            assignment_id: int,
            discord_user_id: str,
            mtgo_username: str,
    ) -> dict:
        return self._request(
            "PATCH",
            f"/loan/sessions/assignments/{assignment_id}/discord",
            json={
                "discord_user_id": discord_user_id,
                "mtgo_username": mtgo_username,
            },
        )

    def confirm_assignment(self, assignment_id: int) -> dict:
        return self._request(
            "POST",
            f"/loan/sessions/assignments/{assignment_id}/confirm",
        )

    def return_assignment(self, assignment_id: int) -> dict:
        return self._request(
            "POST",
            f"/loan/sessions/assignments/{assignment_id}/return",
        )

    def _request(
            self,
            method: str,
            path: str,
            **kwargs,
    ) -> dict | list:
        response = self._client.request(method, path, **kwargs)

        if response.status_code >= 400:
            detail = response.text

            if response.content:
                try:
                    detail = response.json().get("detail", response.text)
                except ValueError:
                    pass

            raise CubeBotApiError(response.status_code, detail)

        return response.json()

    def close(self):
        self._client.close()
