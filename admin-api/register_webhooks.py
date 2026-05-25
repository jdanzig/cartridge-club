"""Register webhook subscriptions with the FastAPI webhook service.

Idempotent: if a subscription already exists for (topic, callbackUrl) we leave
it in place. Otherwise we create one. We never delete via this script — use
`unregister_webhooks.py` (left as an exercise) or delete from the admin.
"""

from __future__ import annotations

import click

from _client import ShopifyClient, console

TOPICS = [
    ("ORDERS_CREATE", "/webhooks/orders/create"),
    ("ORDERS_PAID", "/webhooks/orders/paid"),
    ("PRODUCTS_UPDATE", "/webhooks/products/update"),
    ("INVENTORY_LEVELS_UPDATE", "/webhooks/inventory_levels/update"),
    ("APP_UNINSTALLED", "/webhooks/app/uninstalled"),
    # GDPR / compliance
    ("CUSTOMERS_DATA_REQUEST", "/webhooks/customers/data_request"),
    ("CUSTOMERS_REDACT", "/webhooks/customers/redact"),
    ("SHOP_REDACT", "/webhooks/shop/redact"),
]

LIST_SUBSCRIPTIONS = """
query ListWebhooks($first: Int!) {
  webhookSubscriptions(first: $first) {
    nodes {
      id
      topic
      endpoint {
        __typename
        ... on WebhookHttpEndpoint { callbackUrl }
      }
    }
  }
}
"""

CREATE_SUBSCRIPTION = """
mutation WebhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
  webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
    webhookSubscription { id }
    userErrors { field message }
  }
}
"""


@click.command()
@click.option("--base-url", required=True,
              help="Public URL of the webhook service, e.g. https://your-tunnel.trycloudflare.com")
def main(base_url: str) -> None:
    client = ShopifyClient.from_env()
    console.rule(f"[bold]register_webhooks[/bold] → {client.store_domain}")
    base_url = base_url.rstrip("/")

    existing = client.graphql(LIST_SUBSCRIPTIONS, {"first": 100})
    existing_pairs: set[tuple[str, str]] = set()
    for node in existing["webhookSubscriptions"]["nodes"]:
        ep = node.get("endpoint") or {}
        if ep.get("__typename") == "WebhookHttpEndpoint":
            existing_pairs.add((node["topic"], ep["callbackUrl"]))

    created = 0
    skipped = 0
    for topic, path in TOPICS:
        callback = f"{base_url}{path}"
        if (topic, callback) in existing_pairs:
            console.print(f"  [dim]·[/dim] {topic} → {callback} (exists)")
            skipped += 1
            continue
        data = client.graphql(CREATE_SUBSCRIPTION, {
            "topic": topic,
            "webhookSubscription": {
                "callbackUrl": callback,
                "format": "JSON",
            },
        })
        client.check_user_errors(data, "webhookSubscriptionCreate.userErrors")
        console.print(f"  [green]+[/green] {topic} → {callback}")
        created += 1

    console.print(f"\n[green]Done.[/green] created={created}, already-present={skipped}")


if __name__ == "__main__":
    main()
