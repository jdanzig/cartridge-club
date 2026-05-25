"""Order webhook handlers — classification and incompatibility flagging."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from models.db import connect

CONSOLE_TAG_RE = re.compile(r"console:([a-z0-9_]+)")


def classify_order(order: dict[str, Any]) -> tuple[str, bool, str | None]:
    """Return (setup_type, flagged, reason).

    setup_type: "<console>_setup" if exactly one console is referenced across
                line items, else "mixed_or_unknown".
    flagged: True when the order looks like it should have been blocked.
    reason: human-readable explanation for the flag (or None).
    """
    consoles_seen: Counter[str] = Counter()
    handles_in_order: set[str] = set()
    requires_handles: dict[str, list[str]] = {}

    for li in order.get("line_items", []):
        handles_in_order.add(li.get("handle") or li.get("product_handle") or "")
        tags = li.get("tags") or ""
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tags:
            m = CONSOLE_TAG_RE.match(tag)
            if m:
                consoles_seen[m.group(1)] += 1
        # `properties` may carry the requires_accessory metafield mirrored
        # client-side. Realistically Shopify won't send metafields with
        # orders/create — a real implementation would re-query Admin API.
        props = li.get("properties") or []
        for p in props:
            if p.get("name") == "requires_accessory":
                requires_handles[li.get("title") or li.get("name") or ""] = (
                    p.get("value", "").split(",")
                )

    setup_type = "mixed_or_unknown"
    if len(consoles_seen) == 1:
        setup_type = f"{next(iter(consoles_seen))}_setup"

    flagged = False
    reason = None
    for line_label, requires in requires_handles.items():
        unmet = [h for h in requires if h and h not in handles_in_order]
        if unmet:
            flagged = True
            reason = f"{line_label} requires {unmet} but they are not in this order"
            break

    return setup_type, flagged, reason


async def handle_orders_create(shop_domain: str, payload: dict[str, Any]) -> None:
    setup_type, flagged, reason = classify_order(payload)

    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO orders_normalized
              (order_id, shop_domain, setup_type, total, currency, customer, line_items, flagged, flag_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(payload.get("id") or payload.get("admin_graphql_api_id")),
                shop_domain,
                setup_type,
                str(payload.get("total_price")),
                payload.get("currency"),
                json.dumps(payload.get("customer") or {}),
                json.dumps(payload.get("line_items") or []),
                1 if flagged else 0,
                reason,
            ),
        )


async def handle_orders_paid(shop_domain: str, payload: dict[str, Any]) -> None:
    """Identical to orders/create for the sandbox; production would mark as paid
    and trigger fulfillment-side checks."""
    await handle_orders_create(shop_domain, payload)
