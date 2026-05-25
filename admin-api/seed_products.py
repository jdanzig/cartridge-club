"""Create accessory products and link compatibility metafields to console metaobjects.

Idempotent: looks up products by handle and updates in place. After creating a
product, this script attaches metafields whose values reference the `console`
metaobjects seeded by `seed_consoles.py` — so run that first.

NOTE: image upload via `stagedUploadsCreate` is implemented but skipped by
default because the fixtures don't carry image bytes. Pass --with-placeholder
to upload a generated PNG placeholder per product.
"""

from __future__ import annotations

import io
import json
from typing import Any

import click

from _client import ShopifyClient, ShopifyError, console, load_fixture

# ── GraphQL fragments ────────────────────────────────────────────────────────

PRODUCT_BY_HANDLE = """
query ProductByHandle($handle: String!) {
  productByHandle(handle: $handle) {
    id
    handle
    variants(first: 5) { nodes { id sku } }
  }
}
"""

PRODUCT_CREATE = """
mutation ProductCreate($input: ProductInput!) {
  productCreate(input: $input) {
    product { id handle title }
    userErrors { field message }
  }
}
"""

PRODUCT_UPDATE = """
mutation ProductUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id handle }
    userErrors { field message }
  }
}
"""

METAFIELDS_SET = """
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id key namespace }
    userErrors { field message code }
  }
}
"""

CONSOLE_GIDS_QUERY = """
query ConsoleGids($first: Int!, $after: String) {
  metaobjects(type: "console", first: $first, after: $after) {
    nodes { id handle }
    pageInfo { hasNextPage endCursor }
  }
}
"""

STAGED_UPLOADS = """
mutation StagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets {
      url
      resourceUrl
      parameters { name value }
    }
    userErrors { field message }
  }
}
"""

FILE_CREATE = """
mutation FileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id alt fileStatus }
    userErrors { field message }
  }
}
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_console_gid_map(client: ShopifyClient) -> dict[str, str]:
    """handle → metaobject GID for all `console` metaobjects in the shop."""
    handles: dict[str, str] = {}
    cursor = None
    while True:
        data = client.graphql(CONSOLE_GIDS_QUERY, {"first": 50, "after": cursor})
        bucket = data["metaobjects"]
        for node in bucket["nodes"]:
            handles[node["handle"]] = node["id"]
        if not bucket["pageInfo"]["hasNextPage"]:
            break
        cursor = bucket["pageInfo"]["endCursor"]
    return handles


def metafield_inputs(
    product_gid: str,
    fields: dict[str, Any],
    console_gid_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Build MetafieldsSet inputs for one product. Skips null/empty fields."""
    out: list[dict[str, Any]] = []

    def add(key: str, value: Any, type_: str) -> None:
        if value is None or value == [] or value == "":
            return
        out.append({
            "ownerId": product_gid,
            "namespace": "custom",
            "key": key,
            "type": type_,
            "value": json.dumps(value) if isinstance(value, (list, dict)) else str(value),
        })

    # Convert console handles to metaobject GIDs for the metaobject_reference list.
    compat = fields.get("compatible_consoles") or []
    missing = [h for h in compat if h not in console_gid_map]
    if missing:
        raise ShopifyError(
            f"compatible_consoles references unknown console handles: {missing}. "
            "Run seed_consoles.py first."
        )
    if compat:
        out.append({
            "ownerId": product_gid,
            "namespace": "custom",
            "key": "compatible_consoles",
            "type": "list.metaobject_reference",
            "value": json.dumps([console_gid_map[h] for h in compat]),
        })

    add("connector_type", fields.get("connector_type"), "single_line_text_field")
    add("input_connector", fields.get("input_connector"), "single_line_text_field")
    add("output_connector", fields.get("output_connector"), "single_line_text_field")
    add("video_output", fields.get("output_connector"), "single_line_text_field")
    add("supported_resolutions", fields.get("supported_resolutions"), "list.single_line_text_field")
    add("requires_accessory", fields.get("requires_accessory"), "list.single_line_text_field")
    add("incompatible_with", fields.get("incompatible_with"), "list.single_line_text_field")
    add("region", fields.get("region"), "single_line_text_field")
    add("console_generation", fields.get("console_generation"), "single_line_text_field")
    add("bundle_type", fields.get("bundle_type"), "single_line_text_field")
    add("bundle_components", fields.get("bundle_components"), "list.single_line_text_field")
    add("accessory_kind", fields.get("accessory_kind"), "single_line_text_field")
    add("warning", fields.get("warning"), "multi_line_text_field")

    return out


def upsert_product(client: ShopifyClient, fixture: dict[str, Any]) -> str:
    handle = fixture["handle"]
    existing = client.graphql(PRODUCT_BY_HANDLE, {"handle": handle})
    product = existing.get("productByHandle")

    base_input = {
        "handle": handle,
        "title": fixture["title"],
        "descriptionHtml": fixture["description"],
        "vendor": fixture["vendor"],
        "productType": fixture["product_type"],
        "tags": fixture.get("tags", []),
        "status": "ACTIVE",
    }

    if product:
        update_payload = {**base_input, "id": product["id"]}
        data = client.graphql(PRODUCT_UPDATE, {"input": update_payload})
        client.check_user_errors(data, "productUpdate.userErrors")
        console.print(f"  [yellow]↻[/yellow] updated product [bold]{handle}[/bold]")
        return product["id"]

    # New product: include a single default variant carrying SKU + price.
    create_input = {
        **base_input,
        "variants": [{
            "price": fixture["price"],
            "sku": fixture["sku"],
            "inventoryItem": {"tracked": True},
        }],
    }
    data = client.graphql(PRODUCT_CREATE, {"input": create_input})
    client.check_user_errors(data, "productCreate.userErrors")
    product_id = data["productCreate"]["product"]["id"]
    console.print(f"  [green]+[/green] created product [bold]{handle}[/bold]")
    return product_id


def attach_metafields(
    client: ShopifyClient,
    product_gid: str,
    fields: dict[str, Any],
    console_gid_map: dict[str, str],
) -> int:
    inputs = metafield_inputs(product_gid, fields, console_gid_map)
    if not inputs:
        return 0
    data = client.graphql(METAFIELDS_SET, {"metafields": inputs})
    client.check_user_errors(data, "metafieldsSet.userErrors")
    return len(inputs)


# ── CLI ──────────────────────────────────────────────────────────────────────

@click.command()
@click.option("--limit", type=int, default=None, help="Process only N products (for smoke tests).")
@click.option("--with-placeholder", is_flag=True, help="Upload a placeholder image per product.")
def main(limit: int | None, with_placeholder: bool) -> None:
    """Seed accessory products and compatibility metafields."""
    client = ShopifyClient.from_env()
    console.rule(f"[bold]seed_products[/bold] → {client.store_domain}")

    console_gid_map = load_console_gid_map(client)
    if not console_gid_map:
        raise ShopifyError(
            "No `console` metaobjects found. Run `python seed_consoles.py` first."
        )
    console.print(f"Resolved {len(console_gid_map)} consoles for metaobject references.")

    fixtures = load_fixture("accessories.json")
    if limit:
        fixtures = fixtures[:limit]

    console.print(f"\nSeeding {len(fixtures)} products…")
    total_metafields = 0
    for fixture in fixtures:
        product_gid = upsert_product(client, fixture)
        n = attach_metafields(client, product_gid, fixture["metafields"], console_gid_map)
        total_metafields += n
        if with_placeholder:
            _upload_placeholder(client, product_gid, fixture["title"])

    console.print(
        f"\n[green]Done.[/green] {len(fixtures)} products, {total_metafields} metafields written."
    )


def _upload_placeholder(client: ShopifyClient, product_gid: str, title: str) -> None:
    """Upload a 1x1 PNG placeholder and attach it to a product as the file alt-text only.

    This demonstrates the stagedUploadsCreate → fileCreate pattern without
    requiring real image bytes in the fixtures. For a real seed, point at
    actual files on disk.
    """
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc"
        b"\xff\xff?\x03\x00\x05\xfe\x02\xfe\xa3\x35\x81\x84\x00\x00\x00\x00"
        b"IEND\xaeB`\x82"
    )
    staged = client.graphql(STAGED_UPLOADS, {
        "input": [{
            "filename": "placeholder.png",
            "mimeType": "image/png",
            "httpMethod": "POST",
            "resource": "IMAGE",
        }]
    })
    targets = staged["stagedUploadsCreate"]["stagedTargets"]
    if not targets:
        return
    target = targets[0]
    files = {"file": ("placeholder.png", io.BytesIO(png), "image/png")}
    data = {p["name"]: p["value"] for p in target["parameters"]}
    import requests
    requests.post(target["url"], data=data, files=files, timeout=30)

    file_data = client.graphql(FILE_CREATE, {
        "files": [{
            "alt": title,
            "contentType": "IMAGE",
            "originalSource": target["resourceUrl"],
        }]
    })
    client.check_user_errors(file_data, "fileCreate.userErrors")


if __name__ == "__main__":
    main()
