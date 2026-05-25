"""HMAC verification for Shopify webhooks.

Shopify signs every webhook payload with HMAC-SHA256 using the app secret,
encoded base64, sent in the `X-Shopify-Hmac-Sha256` header. The signature is
computed over the **raw request body** — so the verification has to read
bytes, not parsed JSON.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


class HmacInvalidError(Exception):
    """Raised when an incoming webhook fails HMAC verification."""


def shopify_webhook_secret() -> str:
    secret = os.environ.get("SHOPIFY_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError(
            "SHOPIFY_WEBHOOK_SECRET is not set. Use the app's API secret."
        )
    return secret


def verify_shopify_hmac(body: bytes, header_value: str, secret: str | None = None) -> bool:
    """Return True iff the base64 HMAC matches the secret over `body`.

    Constant-time comparison via hmac.compare_digest.
    """
    if not header_value:
        return False
    key = (secret or shopify_webhook_secret()).encode("utf-8")
    digest = hmac.new(key, body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, header_value)


def require_hmac(body: bytes, header_value: str) -> None:
    """Raise HmacInvalidError on failure — easier to chain than returning bool."""
    if not verify_shopify_hmac(body, header_value):
        raise HmacInvalidError("Bad or missing X-Shopify-Hmac-Sha256")
