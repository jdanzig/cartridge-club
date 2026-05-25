# functions/ — Shopify Functions for checkout logic

Three Functions, all targeting the JavaScript runtime via the Function API.
Rust would be the more "Shopify Plus" choice; JS was picked here so the
sandbox stays buildable without a Rust toolchain. See `../docs/decisions.md`.

| Directory | Target API | What it does |
| --- | --- | --- |
| `cart-checkout-validation/` | `cart.validations.generate.run` | Blocks checkout when the cart has incompatible items (`requires_accessory` missing, conflicting output standards, etc.). |
| `cart-transform/` | `cart.transform.run` | Expands a starter-kit "parent" line into its component accessories at checkout. |
| `product-discount/` | `cart.lines.discounts.generate.run` | Applies a "Complete Your Setup" discount when a controller + cable + cleaning kit for the same console are present. |

Each Function reads runtime configuration from shop metafields written by the
embedded app (`embedded-app/`), so merchants can toggle thresholds without
redeploying code.

## Local dev

```bash
cd functions/cart-checkout-validation
shopify app function dev
# In a separate terminal, run the embedded app to host the OAuth + admin UI:
cd ../../embedded-app
shopify app dev
```

The functions are wired to the same Partner app as the embedded app (see
`../shopify.app.toml`); `shopify app deploy` from the repo root deploys all
three together.

## File layout per Function

```
cart-checkout-validation/
├── shopify.function.extension.toml   # extension config + target
├── package.json                      # ESBuild bundle setup
├── input.graphql                     # query for everything the Function reads
└── src/
    └── run.js                        # exports `run(input): Output`
```

Each `run.js` is a pure function: `(input) → output`. No I/O, no Date.now()
non-determinism. Tests (TODO) would feed handcrafted input JSON and assert
on output JSON.
