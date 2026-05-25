"""Shared Shopify Admin GraphQL client.

Single-tenant, server-side script auth via a custom-app access token.
Use a real HTTP client (`requests`) and surface response errors loudly:
swallowing a userError silently is the most common cause of "the script
ran but nothing happened" in Shopify scripting.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console

# Load .env from the repo root (one level above admin-api/).
_REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_REPO_ROOT / ".env")

console = Console()


class ShopifyError(RuntimeError):
    """Raised when the Admin API returns errors or userErrors."""


@dataclass
class ShopifyClient:
    store_domain: str
    access_token: str
    api_version: str = "2025-01"

    @classmethod
    def from_env(cls) -> "ShopifyClient":
        domain = os.environ.get("SHOPIFY_STORE_DOMAIN")
        token = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN")
        version = os.environ.get("SHOPIFY_API_VERSION", "2025-01")
        if not domain or not token:
            raise ShopifyError(
                "Missing SHOPIFY_STORE_DOMAIN or SHOPIFY_ADMIN_ACCESS_TOKEN. "
                "Copy .env.example to .env and fill them in."
            )
        return cls(store_domain=domain, access_token=token, api_version=version)

    @property
    def endpoint(self) -> str:
        return f"https://{self.store_domain}/admin/api/{self.api_version}/graphql.json"

    def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        *,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL request and return `data`. Retries on throttling."""
        body: dict[str, Any] = {"query": query, "variables": variables or {}}
        if operation_name:
            body["operationName"] = operation_name

        backoff = 1.0
        for attempt in range(6):
            response = requests.post(
                self.endpoint,
                headers={
                    "X-Shopify-Access-Token": self.access_token,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=body,
                timeout=30,
            )
            if response.status_code == 429:
                time.sleep(backoff)
                backoff *= 2
                continue
            if response.status_code >= 500:
                time.sleep(backoff)
                backoff *= 2
                continue
            payload = response.json()
            errors = payload.get("errors")
            if errors:
                # THROTTLED appears under errors[].extensions.code in some shops.
                if any(
                    (e.get("extensions") or {}).get("code") == "THROTTLED"
                    for e in errors
                ):
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                raise ShopifyError(_format_errors(errors))
            return payload.get("data") or {}

        raise ShopifyError("Exhausted retries against Shopify Admin API.")

    def check_user_errors(self, data: dict[str, Any], path: str) -> None:
        """Walk `data` along dotted `path` and raise on any userErrors."""
        cursor: Any = data
        for segment in path.split("."):
            if not isinstance(cursor, dict):
                return
            cursor = cursor.get(segment)
        if isinstance(cursor, list) and cursor:
            messages = [
                f"  - {err.get('field')}: {err.get('message')}"
                for err in cursor
                if isinstance(err, dict)
            ]
            raise ShopifyError("Shopify userErrors:\n" + "\n".join(messages))


def _format_errors(errors: list[dict[str, Any]]) -> str:
    return "Shopify GraphQL errors:\n" + json.dumps(errors, indent=2)


def load_fixture(name: str) -> Any:
    """Read a JSON fixture from /fixtures by filename."""
    path = _REPO_ROOT / "fixtures" / name
    with path.open() as fh:
        return json.load(fh)
