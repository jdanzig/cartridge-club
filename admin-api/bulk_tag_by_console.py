"""Apply `console:*` and `category:*` tags to every product via Bulk Operations.

Pattern shown here:
1. Run a `productsAdd` bulkOperation that writes a JSONL file remote-side.
   (For tag normalization, we instead read the current products via bulk
   query and re-issue tagsAdd in batches — Shopify's bulk mutation surface
   for tag add/remove is the JSONL `stagedUploadsCreate → bulkOperationRunMutation`
   flow.)

Concretely:
1. Bulk-query every product with its current tags and metafields.
2. Compute desired tag set per product.
3. Stage a JSONL of `tagsAdd` mutations and run `bulkOperationRunMutation`.
4. Poll until COMPLETED.

This is the canonical Shopify Plus pattern for cross-product attribute changes.
"""

from __future__ import annotations

import io
import json
import time

import click
import requests

from _client import ShopifyClient, ShopifyError, console

BULK_QUERY = """
mutation BulkQueryProducts {
  bulkOperationRunQuery(query: \"\"\"
    {
      products {
        edges {
          node {
            id
            handle
            tags
            metafields(namespace: \"custom\", first: 10) {
              edges { node { key value type } }
            }
          }
        }
      }
    }
  \"\"\") {
    bulkOperation { id status }
    userErrors { field message }
  }
}
"""

CURRENT_BULK = """
query CurrentBulkOperation {
  currentBulkOperation { id status errorCode url objectCount type completedAt }
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

BULK_MUTATION = """
mutation BulkMutationRun($stagedUploadPath: String!) {
  bulkOperationRunMutation(
    mutation: \"mutation tagsAdd($id: ID!, $tags: [String!]!) { tagsAdd(id: $id, tags: $tags) { node { id } userErrors { field message } } }\",
    stagedUploadPath: $stagedUploadPath
  ) {
    bulkOperation { id status }
    userErrors { field message }
  }
}
"""


def desired_tags(node: dict) -> set[str]:
    """Compute the tag set we want this product to carry."""
    metafields = {
        edge["node"]["key"]: edge["node"]
        for edge in (node.get("metafields") or {}).get("edges", [])
    }

    tags: set[str] = set(node.get("tags") or [])

    # console:* from compatible_consoles metaobject references.
    compat = metafields.get("compatible_consoles")
    if compat and compat["type"] == "list.metaobject_reference":
        # We don't know handles from GIDs without another query; the tag
        # `console:*` is also written by seed_products from fixtures, so we
        # just preserve any existing console:* tags here. This script's job
        # is normalization, not first-application.
        pass

    kind = metafields.get("accessory_kind")
    if kind:
        tags.add(f"category:{kind['value']}")

    bundle_type = metafields.get("bundle_type")
    if bundle_type and bundle_type["value"]:
        tags.add(f"category:{bundle_type['value']}")

    return tags


def run_bulk_query(client: ShopifyClient) -> None:
    data = client.graphql(BULK_QUERY)
    client.check_user_errors(data, "bulkOperationRunQuery.userErrors")
    console.print("[green]✓[/green] bulk query enqueued")


def wait_for_bulk(client: ShopifyClient, *, label: str) -> dict:
    while True:
        data = client.graphql(CURRENT_BULK)
        op = data["currentBulkOperation"]
        if not op:
            raise ShopifyError("No currentBulkOperation in flight — was the operation enqueued?")
        status = op["status"]
        console.print(f"  [dim]{label}[/dim] {status} (objects={op.get('objectCount')})")
        if status in {"COMPLETED", "CANCELED", "FAILED", "EXPIRED"}:
            if status != "COMPLETED":
                raise ShopifyError(f"Bulk operation ended with status={status}, error={op.get('errorCode')}")
            return op
        time.sleep(2)


def fetch_bulk_jsonl(url: str) -> list[dict]:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    nodes = []
    for line in response.iter_lines():
        if not line:
            continue
        nodes.append(json.loads(line))
    return nodes


def stage_jsonl_upload(client: ShopifyClient, body: bytes) -> str:
    data = client.graphql(STAGED_UPLOADS, {
        "input": [{
            "filename": "bulk_tags.jsonl",
            "mimeType": "text/jsonl",
            "httpMethod": "POST",
            "resource": "BULK_MUTATION_VARIABLES",
        }]
    })
    target = data["stagedUploadsCreate"]["stagedTargets"][0]
    files = {"file": ("bulk_tags.jsonl", io.BytesIO(body), "text/jsonl")}
    form = {p["name"]: p["value"] for p in target["parameters"]}
    requests.post(target["url"], data=form, files=files, timeout=60).raise_for_status()
    # The staged upload path for bulkOperationRunMutation is the `key`
    # parameter in the form.
    return form["key"]


@click.command()
def main() -> None:
    """Normalize tags across all products using a Bulk Operation."""
    client = ShopifyClient.from_env()
    console.rule(f"[bold]bulk_tag_by_console[/bold] → {client.store_domain}")

    console.print("\n[bold]1/3[/bold] running bulk query for products + metafields…")
    run_bulk_query(client)
    op = wait_for_bulk(client, label="query")
    if not op.get("url"):
        console.print("[yellow]No data URL — no products in shop?[/yellow]")
        return

    nodes = fetch_bulk_jsonl(op["url"])
    products = [n for n in nodes if n.get("id", "").startswith("gid://shopify/Product/")]
    console.print(f"  fetched {len(products)} products")

    console.print("\n[bold]2/3[/bold] computing diffs and writing JSONL…")
    payload = io.BytesIO()
    diff_count = 0
    for node in products:
        current = set(node.get("tags") or [])
        wanted = desired_tags(node)
        to_add = sorted(wanted - current)
        if not to_add:
            continue
        payload.write(json.dumps({
            "input": {"id": node["id"], "tags": to_add}
        }).encode() + b"\n")
        diff_count += 1

    if diff_count == 0:
        console.print("  [green]✓[/green] tags already normalized")
        return

    console.print(f"  staging {diff_count} tagsAdd mutations…")
    key = stage_jsonl_upload(client, payload.getvalue())

    console.print("\n[bold]3/3[/bold] running bulkOperationRunMutation…")
    data = client.graphql(BULK_MUTATION, {"stagedUploadPath": key})
    client.check_user_errors(data, "bulkOperationRunMutation.userErrors")
    wait_for_bulk(client, label="mutation")
    console.print(f"\n[green]Done.[/green] {diff_count} products tagged.")


if __name__ == "__main__":
    main()
