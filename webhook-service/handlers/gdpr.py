"""GDPR / compliance webhook handlers.

These topics are MANDATORY for any app submitted to the Shopify App Store.
A real implementation would queue export/erase jobs and follow up via the
contact email; for the sandbox we persist the request and ack 200.
"""

from __future__ import annotations

import json
from typing import Any

from models.db import connect


async def handle_customers_data_request(shop_domain: str, payload: dict[str, Any]) -> None:
    _record(shop_domain, "customers/data_request", payload)


async def handle_customers_redact(shop_domain: str, payload: dict[str, Any]) -> None:
    _record(shop_domain, "customers/redact", payload)


async def handle_shop_redact(shop_domain: str, payload: dict[str, Any]) -> None:
    _record(shop_domain, "shop/redact", payload)


def _record(shop_domain: str, topic: str, payload: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO gdpr_requests (shop_domain, topic, payload) VALUES (?, ?, ?)",
            (shop_domain, topic, json.dumps(payload)),
        )
