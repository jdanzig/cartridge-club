# webhook-service/ — Shopify webhook handler (FastAPI)

Receives webhook deliveries from Shopify, verifies HMAC signatures, dedupes
by event ID, and dispatches per-topic handlers.

## Why this exists

- `orders/create` / `orders/paid` — classify the order by console setup and
  flag any incompatibilities that should have been caught by the
  `cart-checkout-validation` Function (catches API order paths that bypass
  Functions).
- `products/update` — re-run a compatibility audit and write the result to
  `custom.audit_status`.
- `inventory_levels/update` — low-stock log line for downstream alerting.
- `app/uninstalled` — mark the shop record inactive, stop processing.
- GDPR — `customers/data_request`, `customers/redact`, `shop/redact`.
  Required for App Store eligibility; included here because forgetting them
  is a tell.

## Setup

```bash
cd webhook-service
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env  # set SHOPIFY_WEBHOOK_SECRET (== app API secret)
uvicorn app:app --reload --port 8000
```

Expose with a tunnel (Cloudflare or ngrok) and register topics:

```bash
cd ../admin-api
python register_webhooks.py --base-url https://your-tunnel.trycloudflare.com
```

## Tests

```bash
cd webhook-service
python -m pytest -q
```

The included smoke tests cover HMAC verification (good and tampered) and
idempotent replay handling.

## Storage

SQLite database at `./data/webhooks.sqlite`:

- `processed_events` — `(event_id, topic, received_at)` for dedup.
- `orders_normalized` — per-order classification output.
- `audit_log` — `products/update` audit results.
- `shops` — install / uninstall state.

The schema is created on startup. For production you'd swap for Postgres and
real migrations; for the sandbox SQLite keeps everything self-contained.
