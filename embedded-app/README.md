# embedded-app/ — Compatibility Manager (Remix + Polaris)

Embedded Shopify admin app for editing the configuration that drives every
other surface (theme, Functions, headless app).

## What it does

| Route | Purpose |
| --- | --- |
| `app._index.tsx`   | Dashboard: scope summary, links to other pages. |
| `app.consoles.tsx` | List + create `console` metaobjects, edit per-console default settings. |
| `app.rules.tsx`    | CRUD `compatibility_rule` metaobjects in a matrix view. |
| `app.functions.tsx`| Toggle Functions on/off and tune thresholds — writes shop metafields under namespace `cc_functions`. |

## Storage

All merchant-edited state goes into Shopify metaobjects + shop metafields,
**not** an app DB. The Functions and theme read the same metafields directly,
so there's a single source of truth and no consistency dance between an
external store and Shopify.

## Setup

```bash
cd embedded-app
npm install
npm run dev   # uses shopify.app.toml from the repo root via SHOPIFY_APP_TOML_PATH
```

The app needs a Partner app + dev store. Configure `shopify.app.toml` in the
repo root with your `client_id` from <https://partners.shopify.com>.

## Notes

- Auth is handled by `@shopify/shopify-app-remix` (session tokens, App Bridge).
- All admin GraphQL mutations go through `admin.graphql()` from the
  authenticated context — no direct token usage in route handlers.
- The Functions config writes a small JSON document into the shop's
  `cc_functions.*` metafields; the Functions read it back at runtime.
