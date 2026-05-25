"""Create the `compatibility_rule` metaobject definition and seed entries.

Compatibility rules capture non-obvious cases that don't fit cleanly into
per-product metafields — for example, "GameCube memory cards work in the Wii
but transferring saves requires the official tool."

Each rule references two console metaobjects (source / target). The embedded
app CRUDs these; Functions and the theme read them.
"""

from __future__ import annotations

from typing import Any

import click

from _client import ShopifyClient, ShopifyError, console, load_fixture

DEFINITION_TYPE = "compatibility_rule"

DEFINITION_FIELDS = [
    {"key": "source_console", "name": "Source console", "type": "metaobject_reference",
     "validations": [{"name": "metaobject_definition", "value": "console"}], "required": True},
    {"key": "target_console", "name": "Target console", "type": "metaobject_reference",
     "validations": [{"name": "metaobject_definition", "value": "console"}], "required": True},
    {"key": "accessory_kind", "name": "Accessory kind", "type": "single_line_text_field"},
    {"key": "status", "name": "Status", "type": "single_line_text_field",
     "validations": [{"name": "choices",
                       "value": '["works","works_with_caveats","requires_adapter","incompatible"]'}],
     "required": True},
    {"key": "note", "name": "Note", "type": "multi_line_text_field"},
]

DEFINITION_QUERY = """
query GetMetaobjectDefinition($type: String!) {
  metaobjectDefinitionByType(type: $type) { id type fieldDefinitions { key } }
}
"""

DEFINITION_CREATE = """
mutation CreateRuleDefinition($definition: MetaobjectDefinitionCreateInput!) {
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
    metaobject { id handle }
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

CONSOLE_GIDS_QUERY = """
query ConsoleGids($first: Int!, $after: String) {
  metaobjects(type: "console", first: $first, after: $after) {
    nodes { id handle }
    pageInfo { hasNextPage endCursor }
  }
}
"""


def ensure_definition(client: ShopifyClient) -> None:
    existing = client.graphql(DEFINITION_QUERY, {"type": DEFINITION_TYPE})
    if existing.get("metaobjectDefinitionByType"):
        console.print(f"[green]✓[/green] metaobject definition [bold]{DEFINITION_TYPE}[/bold] already exists")
        return

    data = client.graphql(DEFINITION_CREATE, {
        "definition": {
            "name": "Compatibility Rule",
            "type": DEFINITION_TYPE,
            "fieldDefinitions": DEFINITION_FIELDS,
            "access": {"admin": "MERCHANT_READ_WRITE", "storefront": "PUBLIC_READ"},
        }
    })
    client.check_user_errors(data, "metaobjectDefinitionCreate.userErrors")
    console.print(f"[green]✓[/green] created metaobject definition [bold]{DEFINITION_TYPE}[/bold]")


def load_console_gid_map(client: ShopifyClient) -> dict[str, str]:
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


def _fields_payload(rule: dict[str, Any], consoles_map: dict[str, str]) -> list[dict[str, str]]:
    src = consoles_map.get(rule["source_console"])
    tgt = consoles_map.get(rule["target_console"])
    if not src or not tgt:
        raise ShopifyError(
            f"Rule {rule['handle']} references unknown console handles "
            f"({rule['source_console']} / {rule['target_console']})."
        )
    return [
        {"key": "source_console", "value": src},
        {"key": "target_console", "value": tgt},
        {"key": "accessory_kind", "value": rule.get("accessory_kind", "")},
        {"key": "status", "value": rule["status"]},
        {"key": "note", "value": rule.get("note", "")},
    ]


def upsert_rule(client: ShopifyClient, rule: dict[str, Any], consoles_map: dict[str, str]) -> None:
    handle = rule["handle"]
    fields = _fields_payload(rule, consoles_map)

    existing = client.graphql(ENTRY_BY_HANDLE, {
        "handle": {"type": DEFINITION_TYPE, "handle": handle},
    })
    found = existing.get("metaobjectByHandle")
    if found:
        data = client.graphql(ENTRY_UPDATE, {
            "id": found["id"],
            "metaobject": {"fields": fields},
        })
        client.check_user_errors(data, "metaobjectUpdate.userErrors")
        console.print(f"  [yellow]↻[/yellow] updated rule [bold]{handle}[/bold]")
        return

    data = client.graphql(ENTRY_CREATE, {
        "metaobject": {"type": DEFINITION_TYPE, "handle": handle, "fields": fields},
    })
    client.check_user_errors(data, "metaobjectCreate.userErrors")
    console.print(f"  [green]+[/green] created rule [bold]{handle}[/bold]")


@click.command()
def main() -> None:
    client = ShopifyClient.from_env()
    console.rule(f"[bold]seed_rules[/bold] → {client.store_domain}")

    ensure_definition(client)
    consoles_map = load_console_gid_map(client)
    rules = load_fixture("compatibility-rules.json")

    console.print(f"\nSeeding {len(rules)} compatibility rules…")
    for rule in rules:
        upsert_rule(client, rule, consoles_map)

    console.print(f"\n[green]Done.[/green] {len(rules)} compatibility rules in sync.")


if __name__ == "__main__":
    main()
