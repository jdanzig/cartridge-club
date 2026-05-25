# theme/ — Cartridge Club Liquid theme overlay

Custom sections, snippets, and templates that overlay a Dawn fork. This
directory **does not contain a full theme** — it contains only the files
specific to this project. To get a runnable theme:

```bash
# 1. Initialize Dawn into a sibling working dir, OR use the existing one.
cd ..  # back to repo root
shopify theme init dawn-base --clone-url https://github.com/Shopify/dawn

# 2. Copy this overlay on top of Dawn.
cp -R theme/sections/*.liquid   dawn-base/sections/
cp -R theme/snippets/*.liquid   dawn-base/snippets/
cp -R theme/templates/*.json    dawn-base/templates/
cp -R theme/assets/*            dawn-base/assets/
cp    theme/config/settings_schema.json dawn-base/config/

# 3. Push to the dev store.
cd dawn-base
shopify theme dev --store=$SHOPIFY_STORE_DOMAIN
```

## What's here

| Path | Purpose |
| --- | --- |
| `sections/console-selector.liquid` | Sticky header dropdown that writes `console_id` cookie + URL param. |
| `sections/compatibility-matrix.liquid` | PDP section: consoles × this product status grid. |
| `sections/compatibility-warning.liquid` | Renders `custom.warning` prominently when present. |
| `sections/complete-your-setup.liquid` | PDP: related accessories filtered by selected console. |
| `snippets/compatibility-badge.liquid` | Reusable green/yellow/red/adapter badge. |
| `snippets/accessory-warning.liquid` | Inline warning chip for PLP cards. |
| `templates/product.retro-accessory.json` | Product template wiring the sections together. |
| `templates/collection.console-accessories.json` | Collection template with console-aware sidebar. |
| `assets/compatibility.css` | Badge + matrix styles. |
| `assets/console-selector.js` | Reads/writes the `console_id` cookie. |
| `config/settings_schema.json` | Theme settings: badge colors, default console, show-incompatible toggle. |

## Compatibility selection contract

Three sources of truth, in priority order:

1. `?console=<handle>` URL param.
2. `console_id` cookie (set by Console Selector).
3. `settings.default_console` from theme settings.

`snippets/compatibility-badge.liquid` reads these via a small Liquid helper
block and renders the appropriate status. The headless Storefront app uses
the same param shape so links survive the boundary.
