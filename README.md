# Cartridge Club Supply — Shopify Platform Sandbox

[![test](https://github.com/jdanzig/cartridge-club/actions/workflows/test.yml/badge.svg)](https://github.com/jdanzig/cartridge-club/actions/workflows/test.yml)

A hands-on Shopify Plus-style technical sandbox built around a fictional
retro gaming accessories store, **Cartridge Club Supply**. The project
exists to demonstrate platform mechanics across every major Shopify surface
area: Liquid theme customization, Admin API automation, Storefront API
discovery and cart flows, Shopify Functions for checkout logic, an embedded
Remix admin app, and a webhook-driven backend.

> **Honest framing.** This is a sandbox repo, not a live merchant store.
> It supports a credible claim of hands-on Shopify platform experience
> across the surfaces below. It does **not** claim production Shopify Plus
> experience.

## Why retro accessories

A Shopify demo is only as interesting as its commerce problem. Generic
fake clothing stores don't force you to use the platform — there are no
metafields to model, no Functions to write, no merchant rules worth
configuring. Retro accessories give every Shopify surface a non-trivial
reason to exist:

- **Compatibility is non-obvious.** Memory cards, controllers, cables,
  and adapters only work with certain consoles. The compatibility model
  is rich enough that the engine has real work to do — it isn't a SKU
  lookup.
- **Bundles matter.** Starter kits expand into component accessories at
  checkout; per-console setups earn "Complete Your Setup" discounts.
- **Edge cases everywhere.** S-Video on a PAL N64 doesn't work. GameCube
  component cables need an early-launch unit. The Functions, the
  embedded app's rule editor, and the theme's warning section all earn
  their place.

## Shopify surfaces covered

| Surface | Where |
| --- | --- |
| Liquid theme (Dawn overlay) | [`theme/`](theme/) |
| Admin GraphQL API (Python CLI) | [`admin-api/`](admin-api/) |
| Storefront API (Next.js headless) | [`storefront-api/compatibility-finder/`](storefront-api/compatibility-finder/) |
| Shopify Functions (JS targets) | [`functions/`](functions/) |
| Embedded admin app (Remix + Polaris) | [`embedded-app/`](embedded-app/) |
| Webhook handlers (FastAPI) | [`webhook-service/`](webhook-service/) |
| Metaobjects + metafields | seeders in `admin-api/`; consumed everywhere |

## Architecture

```
        Merchant Admin
              │
              ▼
   Embedded Compatibility Manager  ──┐
              │                       │
              ▼                       │
       Shopify Admin API ──────► Metaobjects / Metafields
              ▲                       │
              │                       ▼
        admin-api/ CLI         ┌──────────────┐
                               │ Source of    │
                               │ truth for    │
                               │ compatibility│
                               └──────────────┘
                                      │
              ┌───────────────────────┼─────────────────────┐
              ▼                       ▼                     ▼
       Liquid Theme           Storefront API         Shopify Functions
   (badges, matrix,         (compatibility            (validation,
    warnings, setup)         finder, cart)             transform, discount)
              │                       │                     │
              └─────────────┬─────────┘                     │
                            ▼                               │
                       Shopify Cart ─────────────────────► Checkout
                                                            │
                                                            ▼
                                                      Shopify Webhooks
                                                            │
                                                            ▼
                                                  FastAPI Webhook Service
                                                            │
                                                            ▼
                                          Order classification, audit,
                                          GDPR, idempotent event log
```

See [`docs/architecture.md`](docs/architecture.md) for the full breakdown.

## Setup

You'll need:
- A Shopify Partner account and a development store
  (<https://partners.shopify.com>).
- A custom app installed on the dev store with Admin + Storefront API
  scopes (see [`admin-api/README.md`](admin-api/README.md)).
- Node 20+, Python 3.10+, and the Shopify CLI (`brew install shopify-cli`).
- A tunnel for the embedded app and webhook handler (`cloudflared`,
  `ngrok`, or `shopify app dev`'s built-in tunnel).

```bash
git clone <this-repo>
cd cartridge-club
cp .env.example .env       # fill in store domain + tokens + secrets
```

### Bootstrap order

```bash
# 1. Seed metaobjects + products + rules from fixtures.
cd admin-api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed_consoles.py
python seed_products.py
python seed_rules.py
python sync_metafields.py
python bulk_tag_by_console.py

# 2. Theme. (Dawn fork lives separately — see theme/README.md.)
cd ../theme
shopify theme push --store=$SHOPIFY_STORE_DOMAIN --unpublished

# 3. Headless compatibility finder.
cd ../storefront-api/compatibility-finder
npm install && npm run dev   # http://localhost:3001

# 4. Embedded app + Functions (Partner app required).
cd ../../embedded-app
npm install
shopify app dev              # opens tunnel, installs to dev store

# 5. Webhook service.
cd ../webhook-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
# In another shell, point Shopify at this service via your tunnel:
cd ../admin-api
python register_webhooks.py --base-url https://your-tunnel.trycloudflare.com
```

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — system overview and dataflows.
- [`docs/product-model.md`](docs/product-model.md) — consoles, accessories, and rules in detail.
- [`docs/decisions.md`](docs/decisions.md) — ADRs explaining the load-bearing choices.

## Smoke testing

| Component | Command |
| --- | --- |
| Shopify Functions | `cd functions/<dir> && node --test src/run.test.js` |
| Webhook service | `cd webhook-service && pytest -q` |
| Admin CLI scripts | `python3 -c "import ast, pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('admin-api').glob('*.py')]"` |
| Theme JSON | `python3 -c "import json, pathlib; [json.loads(p.read_text()) for p in pathlib.Path('theme').rglob('*.json')]"` |

## Non-goals

Real customer accounts, payments, fulfillment, mobile/POS, Markets,
B2B, Hydrogen, retry queues, visual polish, marketing copy, multi-region
tax, accessibility audits, or anything else not in service of demonstrating
platform mechanics.
