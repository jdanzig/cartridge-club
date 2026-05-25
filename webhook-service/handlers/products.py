"""products/update — audit compatibility metadata and log status."""

from __future__ import annotations

import json
from typing import Any

from models.db import connect


def audit_payload(product: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Return (audit_status, detail).

    audit_status ∈ {verified, needs_review, broken}.

    For a real audit we would re-query the Admin API for metafield values;
    Shopify's products/update webhook does NOT include arbitrary metafields
    in the payload. The function here exercises the storage + dispatch path
    using whatever the payload does carry (handle, tags, product_type).
    """
    detail: dict[str, Any] = {
        "handle": product.get("handle"),
        "product_type": product.get("product_type"),
        "tags": product.get("tags"),
    }

    tags = product.get("tags") or ""
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    has_console_tag = any(t.startswith("console:") for t in tags)
    has_category_tag = any(t.startswith("category:") for t in tags)

    if has_console_tag and has_category_tag:
        return "verified", detail
    if has_console_tag or has_category_tag:
        return "needs_review", detail
    return "broken", detail


async def handle_products_update(shop_domain: str, payload: dict[str, Any]) -> None:
    audit_status, detail = audit_payload(payload)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO audit_log (product_id, shop_domain, audit_status, detail)
            VALUES (?, ?, ?, ?)
            """,
            (
                str(payload.get("id") or payload.get("admin_graphql_api_id")),
                shop_domain,
                audit_status,
                json.dumps(detail),
            ),
        )
