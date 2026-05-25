# admin-api/ — Cartridge Club Admin API CLI

Python scripts that build the Shopify dev store from local fixtures using the
**Admin GraphQL API**.

## Why these exist

The store schema (consoles as metaobjects, accessories as products with
compatibility metafields, compatibility rules as metaobjects) must be
reproducible from source. Clicking through the admin works once and never
again. Each script here is idempotent: re-running it updates existing records
instead of duplicating them.

## Setup

```bash
cd admin-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # fill in SHOPIFY_STORE_DOMAIN + SHOPIFY_ADMIN_ACCESS_TOKEN
```

Create a **custom app** in your dev store (Settings → Apps and sales channels
→ Develop apps → Create an app) and grant these Admin API scopes:

- `read_products`, `write_products`
- `read_inventory`, `write_inventory`
- `read_metaobjects`, `write_metaobjects`
- `read_orders`
- `write_webhooks`
- `read_files`, `write_files`
- `read_publications`, `write_publications`

Install the app to the dev store and copy the Admin API access token into `.env`.

## Build the store from scratch

```bash
# Run in order — later scripts reference IDs created by earlier ones.
python seed_consoles.py
python seed_products.py
python seed_rules.py
python sync_metafields.py
python bulk_tag_by_console.py
python register_webhooks.py --base-url https://your-tunnel.trycloudflare.com
python audit_compatibility.py
```

## Scripts

| Script | Purpose |
| --- | --- |
| `seed_consoles.py` | Creates the `console` metaobject definition and one entry per fixture console. |
| `seed_products.py` | Creates accessory products with variants and links compatibility metafields to console metaobjects. Uploads placeholder images via `stagedUploadsCreate`. |
| `seed_rules.py` | Creates the `compatibility_rule` metaobject definition and one entry per fixture rule. |
| `sync_metafields.py` | Reads `fixtures/metafield-sync.csv` and updates `custom.audit_status` per product. Demonstrates the merchant data ingestion pattern. |
| `bulk_tag_by_console.py` | Uses `bulkOperationRunMutation` to apply `console:*` and `category:*` tags at scale. |
| `register_webhooks.py` | Registers all webhook topics with the webhook service URL. |
| `audit_compatibility.py` | Paginates every product, validates that metafield references resolve to real console metaobjects, reports orphans. |
| `export_orders.py` | Fetches recent orders and groups normalized output by console setup type. |

All scripts share `_client.py` and `_fixtures.py`.

## Re-running safely

Every mutation in these scripts uses upsert semantics (look up by handle, then
update or create). Running the full bootstrap twice produces the same store
state. The audit script is read-only.
