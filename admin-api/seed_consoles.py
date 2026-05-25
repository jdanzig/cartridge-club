"""Create the `console` metaobject definition and seed entries from fixtures.

Idempotent: if the definition or any entry already exists, this script updates
fields in place rather than creating duplicates.
"""

from __future__ import annotations

from typing import Any

import click

from _client import ShopifyClient, console, load_fixture

# ── Metaobject definition ────────────────────────────────────────────────────

DEFINITION_TYPE = "console"

DEFINITION_FIELDS = [
    {"key": "name", "name": "Display name", "type": "single_line_text_field", "required": True},
    {"key": "manufacturer", "name": "Manufacturer", "type": "single_line_text_field"},
    {"key": "release_year", "name": "Release year", "type": "number_integer"},
    {"key": "region_codes", "name": "Region codes", "type": "list.single_line_text_field"},
    {"key": "controller_port_spec", "name": "Controller port spec", "type": "single_line_text_field"},
    {"key": "cartridge_format", "name": "Cartridge format", "type": "single_line_text_field"},
    {"key": "av_output_types", "name": "AV output types", "type": "list.single_line_text_field"},
    {"key": "generation", "name": "Console generation", "type": "single_line_text_field"},
]

DEFINITION_QUERY = """
query GetMetaobjectDefinition($type: String!) {
  metaobjectDefinitionByType(type: $type) {
    id
    type
    fieldDefinitions { key }
  }
}
"""

DEFINITION_CREATE = """
mutation CreateConsoleDefinition($definition: MetaobjectDefinitionCreateInput!) {
  metaobjectDefinitionCreate(definition: $definition) {
    metaobjectDefinition { id type }
    userErrors { field message }
  }
}
"""

ENTRY_BY_HANDLE = """
query GetMetaobjectByHandle($handle: MetaobjectHandleInput!) {
  metaobjectByHandle(handle: $handle) { id handle }
}
"""

ENTRY_CREATE = """
mutation CreateMetaobject($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject { id handle type }
    userErrors { field message code }
  }
}
"""

ENTRY_UPDATE = """
mutation UpdateMetaobject($id: ID!, $metaobject: MetaobjectUpdateInput!) {
  metaobjectUpdate(id: $id, metaobject: $metaobject) {
    metaobject { id handle }
    userErrors { field message code }
  }
}
"""


def ensure_definition(client: ShopifyClient) -> None:
    existing = client.graphql(DEFINITION_QUERY, {"type": DEFINITION_TYPE})
    if existing.get("metaobjectDefinitionByType"):
        console.print(f"[green]✓[/green] metaobject definition [bold]{DEFINITION_TYPE}[/bold] already exists")
        return

    data = client.graphql(
        DEFINITION_CREATE,
        {
            "definition": {
                "name": "Console",
                "type": DEFINITION_TYPE,
                "fieldDefinitions": DEFINITION_FIELDS,
                "access": {"admin": "MERCHANT_READ_WRITE", "storefront": "PUBLIC_READ"},
            }
        },
    )
    client.check_user_errors(data, "metaobjectDefinitionCreate.userErrors")
    console.print(f"[green]✓[/green] created metaobject definition [bold]{DEFINITION_TYPE}[/bold]")


def _fields_payload(entry: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"key": "name", "value": entry["name"]},
        {"key": "manufacturer", "value": entry["manufacturer"]},
        {"key": "release_year", "value": str(entry["release_year"])},
        {"key": "region_codes", "value": _json(entry["region_codes"])},
        {"key": "controller_port_spec", "value": entry["controller_port_spec"]},
        {"key": "cartridge_format", "value": entry["cartridge_format"]},
        {"key": "av_output_types", "value": _json(entry["av_output_types"])},
        {"key": "generation", "value": entry["generation"]},
    ]


def _json(value: Any) -> str:
    import json
    return json.dumps(value)


def upsert_entry(client: ShopifyClient, entry: dict[str, Any]) -> str:
    handle = entry["handle"]
    existing = client.graphql(
        ENTRY_BY_HANDLE,
        {"handle": {"type": DEFINITION_TYPE, "handle": handle}},
    )
    found = existing.get("metaobjectByHandle")
    fields = _fields_payload(entry)

    if found:
        data = client.graphql(
            ENTRY_UPDATE,
            {
                "id": found["id"],
                "metaobject": {"fields": fields},
            },
        )
        client.check_user_errors(data, "metaobjectUpdate.userErrors")
        console.print(f"  [yellow]↻[/yellow] updated [bold]{handle}[/bold]")
        return found["id"]

    data = client.graphql(
        ENTRY_CREATE,
        {
            "metaobject": {
                "type": DEFINITION_TYPE,
                "handle": handle,
                "fields": fields,
            }
        },
    )
    client.check_user_errors(data, "metaobjectCreate.userErrors")
    metaobject_id = data["metaobjectCreate"]["metaobject"]["id"]
    console.print(f"  [green]+[/green] created [bold]{handle}[/bold]")
    return metaobject_id


@click.command()
def main() -> None:
    """Seed `console` metaobjects from fixtures/consoles.json."""
    client = ShopifyClient.from_env()
    console.rule(f"[bold]seed_consoles[/bold] → {client.store_domain}")

    ensure_definition(client)

    entries = load_fixture("consoles.json")
    console.print(f"\nSeeding {len(entries)} consoles…")
    for entry in entries:
        upsert_entry(client, entry)

    console.print(f"\n[green]Done.[/green] {len(entries)} consoles in sync.")


if __name__ == "__main__":
    main()
