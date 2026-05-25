"""Smoke tests for webhook verification and idempotency."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Configure a throwaway DB and a deterministic secret before importing the app.
_TMP_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
os.environ["WEBHOOK_SERVICE_DB_PATH"] = _TMP_DB.name
os.environ["SHOPIFY_WEBHOOK_SECRET"] = "test-secret-do-not-use-in-prod"

from fastapi.testclient import TestClient  # noqa: E402

from app import app  # noqa: E402

client = TestClient(app)


def sign(body: bytes, secret: str = "test-secret-do-not-use-in-prod") -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def post(path: str, body: dict, *, event_id: str = "evt-1",
         shop: str = "test.myshopify.com", bad_hmac: bool = False):
    raw = json.dumps(body).encode()
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Hmac-Sha256": "totally-wrong" if bad_hmac else sign(raw),
        "X-Shopify-Topic": path.rsplit("/", 1)[-1],
        "X-Shopify-Shop-Domain": shop,
        "X-Shopify-Event-Id": event_id,
    }
    return client.post(path, content=raw, headers=headers)


# ── HMAC verification ─────────────────────────────────────────────────────────

def test_rejects_bad_hmac():
    res = post("/webhooks/orders/create", {"id": 1, "line_items": []}, bad_hmac=True)
    assert res.status_code == 401


def test_accepts_good_hmac():
    res = post("/webhooks/orders/create",
               {"id": 100, "line_items": [], "total_price": "0.00", "currency": "USD"},
               event_id="evt-hmac-ok")
    assert res.status_code == 200
    assert res.json()["ok"] is True


# ── Idempotency ──────────────────────────────────────────────────────────────

def test_replay_is_idempotent():
    body = {"id": 101, "line_items": [], "total_price": "0.00", "currency": "USD"}
    a = post("/webhooks/orders/create", body, event_id="evt-replay")
    b = post("/webhooks/orders/create", body, event_id="evt-replay")
    assert a.status_code == 200
    assert b.status_code == 200
    assert b.json().get("replay") is True


# ── Order classification ─────────────────────────────────────────────────────

def test_single_console_classification():
    body = {
        "id": 200,
        "total_price": "29.99",
        "currency": "USD",
        "line_items": [
            {"title": "N64 Replacement Controller", "handle": "n64-replacement-controller",
             "tags": "console:n64,category:controller"},
            {"title": "Composite Cable", "handle": "composite-cable",
             "tags": "console:n64,category:cable"},
        ],
    }
    res = post("/webhooks/orders/create", body, event_id="evt-single-console")
    assert res.status_code == 200

    # Verify it landed in the DB.
    import sqlite3
    with sqlite3.connect(os.environ["WEBHOOK_SERVICE_DB_PATH"]) as conn:
        row = conn.execute(
            "SELECT setup_type, flagged FROM orders_normalized WHERE order_id = ?",
            ("200",),
        ).fetchone()
    assert row is not None
    assert row[0] == "n64_setup"
    assert row[1] == 0


def test_mixed_consoles_classification():
    body = {
        "id": 201,
        "total_price": "100.00",
        "currency": "USD",
        "line_items": [
            {"title": "Snes controller", "handle": "snes-usb-controller-adapter",
             "tags": "console:snes,category:adapter"},
            {"title": "N64 controller", "handle": "n64-replacement-controller",
             "tags": "console:n64,category:controller"},
        ],
    }
    res = post("/webhooks/orders/create", body, event_id="evt-mixed-console")
    assert res.status_code == 200
    import sqlite3
    with sqlite3.connect(os.environ["WEBHOOK_SERVICE_DB_PATH"]) as conn:
        row = conn.execute(
            "SELECT setup_type FROM orders_normalized WHERE order_id = ?",
            ("201",),
        ).fetchone()
    assert row[0] == "mixed_or_unknown"


# ── GDPR ──────────────────────────────────────────────────────────────────────

def test_gdpr_topics_ack_200():
    for path in (
        "/webhooks/customers/data_request",
        "/webhooks/customers/redact",
        "/webhooks/shop/redact",
    ):
        res = post(path, {"shop_domain": "test.myshopify.com"},
                   event_id=f"evt-{path}")
        assert res.status_code == 200, f"{path} returned {res.status_code}"


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"ok": True}
