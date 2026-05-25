# compatibility-finder — headless Storefront API demo

A standalone Next.js app that walks a customer through:

1. **Console picker** — choose your console (loaded from `console` metaobjects).
2. **Goal picker** — controllers / video / maintenance / storage / starter bundle.
3. **Compatible products** — filtered by the `compatible_consoles` metafield.
4. **Cart** — `cartCreate` + `cartLinesAdd` against the Storefront API.
5. **Checkout** — handoff via `cart.checkoutUrl`.

Plus a "search" page demonstrating `predictiveSearch` and faceted `productFilters`.

## Setup

```bash
cd storefront-api/compatibility-finder
cp ../../.env.example .env.local   # we only need NEXT_PUBLIC_* values
npm install
npm run dev
```

Open <http://localhost:3001>.

## Why a separate app

The plan calls out both buyer-side surfaces. Running headless next to the
Liquid theme makes the comparison legible — both render compatibility from
the same metafields and metaobjects without sharing code.

## Notable files

| Path | Purpose |
| --- | --- |
| `lib/shopify.ts` | Storefront GraphQL client. |
| `queries/*.graphql.ts` | Hand-rolled queries (kept as TS templates, no codegen). |
| `app/page.tsx` | Console picker (step 1). |
| `app/[console]/page.tsx` | Goal picker (step 2). |
| `app/[console]/[goal]/page.tsx` | Compatible products (steps 3 + 4). |
| `app/cart/page.tsx` | Cart review + checkout handoff (step 5). |
| `app/search/page.tsx` | Predictive search demo. |
| `app/api/cart/route.ts` | Server route for cart create/add/remove. |
