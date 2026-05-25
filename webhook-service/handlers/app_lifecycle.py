"""app/uninstalled — mark the shop record inactive."""

from __future__ import annotations

from typing import Any

from models.db import connect


async def handle_app_uninstalled(shop_domain: str, _payload: dict[str, Any]) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO shops (shop_domain, state) VALUES (?, 'uninstalled')
            ON CONFLICT(shop_domain) DO UPDATE SET state = 'uninstalled', last_seen = datetime('now')
            """,
            (shop_domain,),
        )
