"""One client per external provider (blueprint ch. 8). Example stub: copy and adapt.

Rules: explicit timeout, parse the response into a Pydantic model (external data is untrusted),
never log secrets, and never call it while holding a DB lock.
"""

import httpx
from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExampleQuote(BaseModel):
    text: str


class ExampleClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 5.0) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=timeout, headers={"Authorization": f"Bearer {api_key}"})

    def get_quote(self) -> ExampleQuote:
        try:
            resp = self._http.get("/quote")
            resp.raise_for_status()
            return ExampleQuote.model_validate(resp.json())
        except (httpx.HTTPError, ValidationError) as exc:
            logger.warning("example provider failed: %s", type(exc).__name__)  # no URL/headers/body
            raise
