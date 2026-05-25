"use client";

import { useState } from "react";
import { readCartId, writeCartId } from "@/lib/cart-cookie";

export default function AddToCartButton({
  variantId,
  disabled,
}: {
  variantId?: string;
  disabled?: boolean;
}) {
  const [status, setStatus] = useState<"idle" | "loading" | "added" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  if (!variantId) {
    return (
      <button className="cc-card__cta" disabled aria-disabled>
        Unavailable
      </button>
    );
  }

  async function handleClick() {
    setStatus("loading");
    setMessage(null);
    try {
      const cartId = readCartId();
      const response = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: cartId ? "add" : "create",
          cartId,
          lines: [{ merchandiseId: variantId, quantity: 1 }],
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error ?? "Add to cart failed");
      }
      writeCartId(payload.cart.id);
      setStatus("added");
      setMessage(`In cart (${payload.cart.totalQuantity} items)`);
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <>
      <button
        className="cc-card__cta"
        onClick={handleClick}
        disabled={disabled || status === "loading"}
      >
        {status === "loading" ? "Adding…" : status === "added" ? "Add another" : "Add to cart"}
      </button>
      {message && (
        <p
          className={status === "error" ? "cc-warning" : ""}
          style={{ fontSize: "0.75rem", margin: 0 }}
        >
          {message}
        </p>
      )}
    </>
  );
}
