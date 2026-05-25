"""FastAPI entrypoint for the Shopify webhook service.

Pipeline for every request:
  1. Read raw body — required for HMAC verification.
  2. Verify HMAC. Reject with 401 on failure.
  3. Read X-Shopify-Event-Id, X-Shopify-Topic, X-Shopify-Shop-Domain.
  4. Dedup by event id (SQLite UNIQUE constraint). Return 200 on replay.
  5. Dispatch to per-topic handler. Errors → 500 so Shopify retries.
  6. Return 200 on success.

Why this shape: a Shopify webhook handler is a few specific obligations
(verify, dedupe, ack quickly) wrapped around small per-topic business logic.
A flat module with one route per topic group keeps the obligations visible.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Awaitable, Callable

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

# Load .env from the repo root, one level above webhook-service/.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from handlers.app_lifecycle import handle_app_uninstalled  # noqa: E402
from handlers.gdpr import (  # noqa: E402
    handle_customers_data_request,
    handle_customers_redact,
    handle_shop_redact,
)
from handlers.inventory import handle_inventory_update  # noqa: E402
from handlers.orders import handle_orders_create, handle_orders_paid  # noqa: E402
from handlers.products import handle_products_update  # noqa: E402
from models.db import init_db, record_event  # noqa: E402
from security import HmacInvalidError, require_hmac  # noqa: E402

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger("cc.webhooks")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    log.info("webhook service started")
    yield


app = FastAPI(title="Cartridge Club Webhook Service", lifespan=lifespan)

# Also init on import so test runners that don't trigger the lifespan
# (e.g. plain `TestClient(app)`) still get the schema applied.
init_db()


Handler = Callable[[str, dict], Awaitable[None]]


async def _dispatch(
    request: Request,
    topic: str,
    handler: Handler,
    *,
    x_shopify_hmac_sha256: str | None,
    x_shopify_shop_domain: str | None,
    x_shopify_event_id: str | None,
) -> JSONResponse:
    body = await request.body()
    try:
        require_hmac(body, x_shopify_hmac_sha256 or "")
    except HmacInvalidError as err:
        log.warning("hmac rejected topic=%s shop=%s: %s",
                    topic, x_shopify_shop_domain, err)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(err))

    if not x_shopify_event_id:
        # Older shops sometimes omit this. Fall back to the body hash so
        # we still dedupe — but warn.
        import hashlib
        x_shopify_event_id = hashlib.sha256(body).hexdigest()
        log.warning("missing X-Shopify-Event-Id, derived id %s", x_shopify_event_id)

    fresh = record_event(x_shopify_event_id, topic)
    if not fresh:
        log.info("idempotent replay topic=%s event=%s", topic, x_shopify_event_id)
        return JSONResponse({"ok": True, "replay": True})

    try:
        import json
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as err:
        log.exception("invalid JSON in webhook body topic=%s", topic)
        raise HTTPException(status_code=400, detail=str(err))

    await handler(x_shopify_shop_domain or "", payload)
    return JSONResponse({"ok": True})


# ── Per-topic routes ─────────────────────────────────────────────────────────

@app.post("/webhooks/orders/create")
async def orders_create(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "orders/create", handle_orders_create,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.post("/webhooks/orders/paid")
async def orders_paid(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "orders/paid", handle_orders_paid,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.post("/webhooks/products/update")
async def products_update(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "products/update", handle_products_update,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.post("/webhooks/inventory_levels/update")
async def inventory_levels_update(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "inventory_levels/update", handle_inventory_update,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.post("/webhooks/app/uninstalled")
async def app_uninstalled(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "app/uninstalled", handle_app_uninstalled,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


# ── GDPR / compliance ────────────────────────────────────────────────────────

@app.post("/webhooks/customers/data_request")
async def customers_data_request(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "customers/data_request", handle_customers_data_request,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.post("/webhooks/customers/redact")
async def customers_redact(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "customers/redact", handle_customers_redact,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.post("/webhooks/shop/redact")
async def shop_redact(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
    x_shopify_event_id: str | None = Header(default=None),
):
    return await _dispatch(
        request, "shop/redact", handle_shop_redact,
        x_shopify_hmac_sha256=x_shopify_hmac_sha256,
        x_shopify_shop_domain=x_shopify_shop_domain,
        x_shopify_event_id=x_shopify_event_id,
    )


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}
