# Architecture Decision Records

ADRs are short, dated, and load-bearing. They explain choices that aren't
obvious from reading the code and would otherwise need to be re-argued in
every review.

---

## ADR-001 — Functions target the JS runtime, not Rust

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** Shopify Functions can be written in Rust (compiled to Wasm) or
JS (bundled via esbuild and run in the V8-derived Function runtime). Rust
is the "Shopify Plus" answer in interviews; JS is faster to iterate and has
zero toolchain setup.

**Decision.** Use JS targets for all three Functions in this sandbox.

**Consequences.**
- Anyone with Node 20 can build and run the Functions; no `rustup` or
  `cargo` required.
- The Function code is plain ESM; the test suite uses `node --test` with
  no test runner dependency.
- We lose the ability to claim Rust + Wasm experience from this repo.
  Easy to revisit per Function if the resume/interview value justifies it
  — the input GraphQL and `[[targeting]]` config stay identical.

---

## ADR-002 — Embedded app stores all merchant config in metaobjects + shop metafields, not an app DB

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** A Remix app comes with Prisma + a session DB by default. It
would be straightforward to also store compatibility rules and Function
config in that DB.

**Decision.** Store every merchant-edited value in Shopify itself:
`compatibility_rule` metaobjects, product `custom.*` metafields, and shop
`cc_functions.*` metafields.

**Consequences.**
- Single source of truth: theme, headless app, and Functions all read the
  same data the embedded app writes. No "your app says X but Shopify says
  Y" support tickets.
- The embedded app needs `write_metaobjects` and `write_metafields` scopes.
- Bulk operations on large rule sets are slower than a `pg` write would be.
  For a sandbox: fine. For a production app shipping to App Store: probably
  also fine, since most stores will have hundreds of rules at most.

---

## ADR-003 — Headless finder is its own Next.js app, not a route inside the embedded app

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** We could fold the compatibility finder into the embedded Remix
app and serve both surfaces from one codebase.

**Decision.** Keep them physically separate — Remix in `embedded-app/`,
Next.js App Router in `storefront-api/compatibility-finder/`.

**Consequences.**
- The plan's intent is to show "both buyer-side surfaces side by side";
  bundling them into one repo dir defeats that.
- The two apps share no code, but they read the same Shopify data, which
  is the point. Drift between them would be a real bug, not a refactor cost.
- Two `npm install`s and two dev ports. Acceptable.

---

## ADR-004 — Webhook service uses SQLite, not Postgres

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** Idempotent webhook handling needs persistent storage.

**Decision.** SQLite, with the schema applied on import and on app startup.
The database lives at `webhook-service/data/webhooks.sqlite`.

**Consequences.**
- Zero external infrastructure for the sandbox; `pytest` and `uvicorn` work
  on a fresh checkout.
- Schema changes happen by editing `models/db.py` and dropping the file;
  there's no Alembic. Acceptable for a project that will never go to prod.
- Single-writer model. Not relevant for a demo, would be for production.

---

## ADR-005 — Admin scripts authenticate as a custom app, not via OAuth

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** OAuth + session tokens are the right answer for installable
apps. They are heavy machinery for one-off operator scripts run from a
local terminal.

**Decision.** The admin-api/ CLI uses an Admin API access token issued by
a custom app installed on the dev store. The embedded app's OAuth is
unrelated.

**Consequences.**
- The CLI is a `python` away from working. No tunnel, no OAuth dance.
- The token is in `.env`. Don't commit it, don't share screenshots.
- Production ops would normally still go through OAuth + permission scopes
  audited by Shopify. The trade-off is documented here, not hidden.

---

## ADR-006 — Tags are duplicated alongside metafields

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** The Storefront API's `productFilters` interface and the
`query` argument both filter cleanly on tags but require setup to filter
on arbitrary metafields. We could either rely entirely on metafields and
push filter setup into the dev store, or duplicate the structured data
into `console:<handle>` and `category:<kind>` tags.

**Decision.** Duplicate. `bulk_tag_by_console.py` keeps tags in sync with
metafield values.

**Consequences.**
- Storefront queries are dead simple (`tag:'console:n64' AND tag:'category:cable'`).
- A second write path means tags can drift if a merchant edits a metafield
  directly in the admin without re-running the script.
- We document the audit script (`audit_compatibility.py`) as the canonical
  way to catch drift.

---

## ADR-007 — GDPR webhooks are implemented even though we won't submit to the App Store

**Status:** Accepted.
**Date:** 2026-05-25.

**Context.** `customers/data_request`, `customers/redact`, and `shop/redact`
are mandatory for Shopify App Store eligibility. They're easy to forget
when not actively going through review.

**Decision.** Implement and test them anyway.

**Consequences.**
- Forgetting them is a tell in interviews — including them signals an
  awareness of App Store review requirements.
- The implementations are intentionally minimal (record + 200). A real
  app would queue export / erase jobs and follow up via contact email.
