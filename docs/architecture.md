# Architecture

## One-line summary

A six-surface Shopify sandbox where every surface reads compatibility data
from the **same Shopify metaobjects + product metafields**. Nothing is
hardcoded, nothing is duplicated outside Shopify, and the embedded admin
app is the only place a merchant edits values that the theme, Storefront
API consumers, and Functions all see.

## Dataflow

```
                  ┌────────────────────────────────────┐
                  │  fixtures/ (JSON + CSV in repo)    │
                  └────────────────────────────────────┘
                                    │
                                    ▼
              ┌─────────────────────────────────────────┐
              │  admin-api/ Python CLI                  │
              │  • seed_consoles.py                     │
              │  • seed_products.py                     │
              │  • seed_rules.py                        │
              │  • sync_metafields.py                   │
              │  • bulk_tag_by_console.py               │
              │  • register_webhooks.py                 │
              │  • audit_compatibility.py               │
              │  • export_orders.py                     │
              └─────────────────────────────────────────┘
                                    │ Admin GraphQL
                                    ▼
              ╔═════════════════════════════════════════╗
              ║          SHOPIFY DEV STORE              ║
              ║                                         ║
              ║  Metaobjects: console, compatibility_rule║
              ║  Products w/ custom.* metafields        ║
              ║  Shop metafields: cc_functions.*        ║
              ╚═════════════════════════════════════════╝
                  │            │            │             │
   Storefront API │  Liquid    │  Functions │  Webhooks   │
                  ▼  drops     ▼  runtime   ▼  push       │
   ┌──────────────────┐  ┌─────────────┐  ┌──────────┐    │
   │ Next.js finder   │  │ Dawn theme  │  │ FastAPI  │    │
   │ (storefront-api/)│  │ overlay     │  │ webhook  │    │
   │ — read products  │  │ — render    │  │ service  │    │
   │ — cart mutations │  │   badges,   │  │ — verify │    │
   │ — checkoutUrl    │  │   matrix,   │  │ — dedupe │    │
   └──────────────────┘  │   warnings  │  │ — class- │    │
                         └─────────────┘  │   ify    │    │
                                          └──────────┘    │
                                                          │
                              embedded-app/  ◄────────────┘
                              (Remix + Polaris admin UI)
                              — only place merchants edit
                                compatibility rules and
                                Function configuration
```

## Source of truth

| Data | Where stored | Read by |
| --- | --- | --- |
| Consoles | `console` metaobject | theme, finder, functions, embedded app |
| Per-product compatibility | `product.metafields.custom.*` | theme, finder, functions |
| Exception rules | `compatibility_rule` metaobject | theme matrix, embedded app |
| Function thresholds and toggles | shop `cc_functions.*` metafields | each Function at runtime |
| Bundle → variant lookup | shop `cc_functions.bundle_component_variant_map` | cart-transform Function |

Putting everything in Shopify removes the consistency dance between an
external store and Shopify's view of the world. The trade-off is that the
embedded app must mediate edits — there's no SQL admin to fall back to.

## Why this shape

- **Metaobjects instead of tags.** The theme matrix and the Storefront API
  finder both walk metaobject references; tags can't carry the structured
  fields the Functions need.
- **Shop metafields for Function config.** Functions have no I/O —
  they can only read the input query. Putting config in shop metafields
  is the canonical pattern for runtime-tunable Functions.
- **Python for Admin scripts and webhook handlers.** Matches Jon's
  background; FastAPI is widely understood and easier for reviewers to
  read than the equivalent Node service.
- **Remix for the embedded app.** Shopify's official template; gives you
  App Bridge + session-token auth + Polaris with no boilerplate.
- **JS targets for Functions.** Rust is the more "Shopify Plus" answer
  but raises the toolchain bar. JS keeps the sandbox buildable. The Function
  surface is the same; the language is documented in `docs/decisions.md`.

## Trust boundaries

- The **embedded app** is the only thing with write access to compatibility
  data via OAuth. Admin scripts use a custom-app access token; treat
  `.env` as the secret store.
- The **headless finder** uses the public Storefront token and never
  sees a write token.
- The **Functions** are pure `(input) → output`. They never make
  outbound requests; all configuration arrives via input metafields.
- The **webhook service** verifies every request's HMAC against the app
  secret. Anything that fails verification is rejected with 401 before
  any handler runs.
