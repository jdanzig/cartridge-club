"""Fetch recent orders and group normalized output by console setup type.

Outputs JSON to stdout (or --output) grouped by inferred console setup:
{
  "n64_setup": [ {order_id, customer, line_items, total} , ... ],
  "gamecube_setup": [...],
  "mixed_or_unknown": [...]
}

A "console setup" is inferred by looking at line item tags / SKU prefixes —
the same `console:*` tags applied by `bulk_tag_by_console.py`. This is a
deliberately simple heuristic; production-grade classification would consult
the Function output written to order attributes / metafields.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from _client import ShopifyClient, console

ORDERS_QUERY = """
query RecentOrders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query, sortKey: CREATED_AT, reverse: true) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      name
      createdAt
      displayFinancialStatus
      totalPriceSet { shopMoney { amount currencyCode } }
      customer { displayName email }
      lineItems(first: 50) {
        nodes {
          title
          quantity
          sku
          product { handle tags }
        }
      }
    }
  }
}
"""

CONSOLE_TAG_RE = re.compile(r"console:([a-z0-9_]+)")


def classify(order: dict) -> str:
    consoles_seen: set[str] = set()
    for li in (order.get("lineItems") or {}).get("nodes", []):
        product = li.get("product") or {}
        for tag in product.get("tags") or []:
            m = CONSOLE_TAG_RE.match(tag)
            if m:
                consoles_seen.add(m.group(1))
    if not consoles_seen:
        return "mixed_or_unknown"
    if len(consoles_seen) == 1:
        return f"{next(iter(consoles_seen))}_setup"
    return "mixed_or_unknown"


@click.command()
@click.option("--days", type=int, default=30, show_default=True,
              help="Look back this many days.")
@click.option("--output", type=click.Path(path_type=Path),
              help="Write JSON to this file instead of stdout.")
@click.option("--limit", type=int, default=250, show_default=True,
              help="Cap total orders fetched.")
def main(days: int, output: Path | None, limit: int) -> None:
    client = ShopifyClient.from_env()
    console.rule(f"[bold]export_orders[/bold] → {client.store_domain}")

    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    query_filter = f"created_at:>={since}"
    console.print(f"Fetching orders since {since}…")

    grouped: dict[str, list[dict]] = defaultdict(list)
    fetched = 0
    cursor: str | None = None
    while fetched < limit:
        page_size = min(50, limit - fetched)
        data = client.graphql(ORDERS_QUERY, {
            "first": page_size,
            "after": cursor,
            "query": query_filter,
        })
        bucket = data["orders"]
        for order in bucket["nodes"]:
            normalized = {
                "id": order["id"],
                "name": order["name"],
                "created_at": order["createdAt"],
                "financial_status": order["displayFinancialStatus"],
                "total": order["totalPriceSet"]["shopMoney"],
                "customer": order.get("customer"),
                "line_items": [
                    {
                        "title": li["title"],
                        "quantity": li["quantity"],
                        "sku": li.get("sku"),
                        "product_handle": (li.get("product") or {}).get("handle"),
                    }
                    for li in (order.get("lineItems") or {}).get("nodes", [])
                ],
            }
            grouped[classify(order)].append(normalized)
            fetched += 1
            if fetched >= limit:
                break
        if not bucket["pageInfo"]["hasNextPage"]:
            break
        cursor = bucket["pageInfo"]["endCursor"]

    payload = {bucket: items for bucket, items in sorted(grouped.items())}
    console.print(f"\nGrouped {fetched} orders into {len(payload)} buckets:")
    for bucket, items in payload.items():
        console.print(f"  · {bucket}: {len(items)}")

    body = json.dumps(payload, indent=2)
    if output:
        output.write_text(body)
        console.print(f"\nWrote {output}")
    else:
        sys.stdout.write(body + "\n")


if __name__ == "__main__":
    main()
