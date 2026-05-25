"""Update product metafields from a CSV.

Demonstrates the "merchant data ingestion" pattern: an ops user drops a CSV
into the repo, runs this script, and the values land on the right products as
the right metafield types.

CSV columns: product_handle, namespace, key, type, value
Re-runnable; uses `metafieldsSet` which is upsert by (owner, namespace, key).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import click

from _client import ShopifyClient, ShopifyError, console

REPO_ROOT = Path(__file__).resolve().parent.parent

PRODUCT_BY_HANDLE = """
query ProductByHandle($handle: String!) { productByHandle(handle: $handle) { id handle } }
"""

METAFIELDS_SET = """
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id key namespace }
    userErrors { field message code }
  }
}
"""

# Types that expect JSON-shaped values.
JSON_TYPES = {
    "list.single_line_text_field",
    "list.number_integer",
    "list.metaobject_reference",
    "json",
}


def coerce_value(value: str, type_: str) -> str:
    """CSV values arrive as strings; JSON-typed fields need quoting."""
    if type_ in JSON_TYPES:
        # Allow comma-separated shorthand "a,b,c" → ["a","b","c"] for ergonomics.
        try:
            json.loads(value)
            return value
        except json.JSONDecodeError:
            items = [v.strip() for v in value.split(",") if v.strip()]
            return json.dumps(items)
    return value


def resolve_handle(client: ShopifyClient, handle: str) -> str:
    data = client.graphql(PRODUCT_BY_HANDLE, {"handle": handle})
    product = data.get("productByHandle")
    if not product:
        raise ShopifyError(f"Product {handle!r} not found in shop.")
    return product["id"]


@click.command()
@click.option(
    "--csv-path",
    type=click.Path(exists=True, path_type=Path),
    default=REPO_ROOT / "fixtures" / "metafield-sync.csv",
    show_default=True,
)
@click.option("--batch-size", type=int, default=25, show_default=True,
              help="metafieldsSet accepts up to 25 inputs per call.")
def main(csv_path: Path, batch_size: int) -> None:
    """Sync product metafields from a CSV."""
    client = ShopifyClient.from_env()
    console.rule(f"[bold]sync_metafields[/bold] → {client.store_domain}")
    console.print(f"Reading {csv_path}")

    # Cache handle → gid lookups so we don't re-query for the same product.
    gid_cache: dict[str, str] = {}
    pending: list[dict[str, str]] = []
    rows = 0

    with csv_path.open() as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            handle = row["product_handle"].strip()
            if handle not in gid_cache:
                gid_cache[handle] = resolve_handle(client, handle)
            pending.append({
                "ownerId": gid_cache[handle],
                "namespace": row["namespace"].strip(),
                "key": row["key"].strip(),
                "type": row["type"].strip(),
                "value": coerce_value(row["value"], row["type"].strip()),
            })
            rows += 1
            if len(pending) >= batch_size:
                _flush(client, pending)
                pending = []

    if pending:
        _flush(client, pending)

    console.print(f"\n[green]Done.[/green] Synced {rows} metafield rows across {len(gid_cache)} products.")


def _flush(client: ShopifyClient, batch: list[dict[str, str]]) -> None:
    data = client.graphql(METAFIELDS_SET, {"metafields": batch})
    client.check_user_errors(data, "metafieldsSet.userErrors")
    console.print(f"  [green]✓[/green] wrote batch of {len(batch)}")


if __name__ == "__main__":
    main()
