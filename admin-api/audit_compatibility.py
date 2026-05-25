"""Paginate every product and validate compatibility metafields.

Read-only. Reports:
- Products missing `custom.compatible_consoles` entirely.
- Products whose `compatible_consoles` list references a metaobject GID that
  doesn't resolve to a real `console` metaobject (orphans).
- Products whose `requires_accessory` references a handle that isn't a real
  product.
- Bundle products whose `bundle_components` list contains an unknown handle.

Exits non-zero if any failures are found — suitable for CI.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import click

from _client import ShopifyClient, console

PRODUCTS_QUERY = """
query AuditProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      handle
      title
      compatible: metafield(namespace: "custom", key: "compatible_consoles") { type value }
      requires: metafield(namespace: "custom", key: "requires_accessory") { type value }
      components: metafield(namespace: "custom", key: "bundle_components") { type value }
      bundleType: metafield(namespace: "custom", key: "bundle_type") { value }
    }
  }
}
"""

CONSOLES_QUERY = """
query AuditConsoles($first: Int!, $after: String) {
  metaobjects(type: "console", first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle }
  }
}
"""


def paginate(client: ShopifyClient, query: str, key: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        data = client.graphql(query, {"first": 50, "after": cursor})
        bucket = data[key]
        out.extend(bucket["nodes"])
        if not bucket["pageInfo"]["hasNextPage"]:
            break
        cursor = bucket["pageInfo"]["endCursor"]
    return out


@click.command()
@click.option("--strict", is_flag=True, help="Exit non-zero on any warning, not just errors.")
def main(strict: bool) -> None:
    client = ShopifyClient.from_env()
    console.rule(f"[bold]audit_compatibility[/bold] → {client.store_domain}")

    products = paginate(client, PRODUCTS_QUERY, "products")
    consoles = paginate(client, CONSOLES_QUERY, "metaobjects")
    console_gids = {c["id"] for c in consoles}
    product_handles = {p["handle"] for p in products}

    errors: list[str] = []
    warnings: list[str] = []

    for p in products:
        handle = p["handle"]
        compatible = p.get("compatible")
        if not compatible:
            warnings.append(f"{handle}: missing custom.compatible_consoles")
        else:
            try:
                gids = json.loads(compatible["value"])
            except json.JSONDecodeError:
                errors.append(f"{handle}: compatible_consoles is not valid JSON")
                gids = []
            orphans = [g for g in gids if g not in console_gids]
            if orphans:
                errors.append(f"{handle}: compatible_consoles references unknown metaobject(s): {orphans}")

        requires = p.get("requires")
        if requires:
            try:
                refs = json.loads(requires["value"])
            except json.JSONDecodeError:
                errors.append(f"{handle}: requires_accessory is not valid JSON")
                refs = []
            missing = [r for r in refs if r not in product_handles]
            if missing:
                errors.append(f"{handle}: requires_accessory references unknown product(s): {missing}")

        components = p.get("components")
        bundle_type = (p.get("bundleType") or {}).get("value")
        if bundle_type == "starter_kit":
            if not components:
                errors.append(f"{handle}: starter-kit bundle has no bundle_components")
            else:
                try:
                    refs = json.loads(components["value"])
                except json.JSONDecodeError:
                    errors.append(f"{handle}: bundle_components is not valid JSON")
                    refs = []
                missing = [r for r in refs if r not in product_handles]
                if missing:
                    errors.append(f"{handle}: bundle_components references unknown product(s): {missing}")

    console.print(f"\nAudited {len(products)} products against {len(consoles)} consoles.")
    if warnings:
        console.print("\n[yellow]Warnings[/yellow]")
        for w in warnings:
            console.print(f"  · {w}")
    if errors:
        console.print("\n[red]Errors[/red]")
        for e in errors:
            console.print(f"  ✗ {e}")

    if errors or (strict and warnings):
        sys.exit(1)
    console.print("\n[green]Done.[/green] No errors.")


if __name__ == "__main__":
    main()
