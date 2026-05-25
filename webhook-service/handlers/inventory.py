"""inventory_levels/update — log low-stock alerts."""

from __future__ import annotations

import logging
from typing import Any

LOW_STOCK_THRESHOLD = 5
log = logging.getLogger(__name__)


async def handle_inventory_update(shop_domain: str, payload: dict[str, Any]) -> None:
    available = payload.get("available")
    if available is None:
        return
    if available <= LOW_STOCK_THRESHOLD:
        log.warning(
            "low-stock alert shop=%s inventory_item_id=%s available=%s",
            shop_domain, payload.get("inventory_item_id"), available,
        )
