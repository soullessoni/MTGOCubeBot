"""Shared boilerplate for the admin-triggered mtgo/*.py CLI scripts:
loading .env, resolving BACKEND_API_URL, fetching a loan session, and
printing the final JSON result line the backend's MtgoJob runner parses
to record success/failure (see process_session_returns.py's docstring
for why that convention exists)."""

import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_API_URL = os.environ.get("BACKEND_API_URL", "http://localhost:8000")


def enable_utf8_stdout() -> None:
    sys.stdout.reconfigure(errors="replace")


def fetch_session(session_id: int) -> dict:
    response = httpx.get(f"{BACKEND_API_URL}/loan/sessions/{session_id}")
    response.raise_for_status()
    return response.json()


def print_result(result: dict) -> None:
    print(json.dumps(result))
