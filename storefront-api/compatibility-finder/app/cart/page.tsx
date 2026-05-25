"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { clearCartId, readCartId } from "@/lib/cart-cookie";

type Money = { amount: string; currencyCode: string };

type CartLine = {
  id: string;
  quantity: number;
  merchandise: {
    id: string;
    sku?: string;
    price: Money;
    product: {
      handle: string;
      title: string;
      featuredImage?: { url: string; altText?: string } | null;
    };
  };
};

type Cart = {
  id: string;
  checkoutUrl: string;
  totalQuantity: number;
  cost: { totalAmount: Money; subtotalAmount: Money };
  lines: { nodes: CartLine[] };
};

function format(m: Money): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: m.currencyCode,
  }).format(Number(m.amount));
}

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null);
  const [status, setStatus] = useState<"loading" | "empty" | "loaded" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const cartId = readCartId();
    if (!cartId) {
      setStatus("empty");
      return;
    }
    try {
      const response = await fetch("/api/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "get", cartId }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.cart) {
        clearCartId();
        setStatus("empty");
        return;
      }
      setCart(payload.cart);
      setStatus("loaded");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (status === "loading") {
    return <section className="cc-empty">Loading cart…</section>;
  }
  if (status === "empty" || !cart) {
    return (
      <section className="cc-empty">
        <p>Your cart is empty.</p>
        <p><Link href="/">Pick a console to start</Link></p>
      </section>
    );
  }
  if (status === "error") {
    return <section className="cc-empty cc-warning">Cart error: {error}</section>;
  }

  return (
    <section>
      <ol className="cc-stepper">
        <li className="cc-stepper__crumb"><Link href="/">1. Console</Link></li>
        <li className="cc-stepper__crumb">2. Goal</li>
        <li className="cc-stepper__crumb">3. Products</li>
        <li className="cc-stepper__crumb cc-stepper__crumb--current">4. Cart</li>
      </ol>

      <h1>Your cart</h1>
      <p>{cart.totalQuantity} items.</p>

      <ul style={{ padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {cart.lines.nodes.map((line) => (
          <li
            key={line.id}
            style={{
              display: "flex",
              gap: "1rem",
              alignItems: "center",
              padding: "0.75rem",
              border: "1px solid var(--cc-border)",
              borderRadius: "0.5rem",
              background: "white",
            }}
          >
            <div className="cc-product-img" style={{ width: 64, height: 64, flex: "none" }}>
              {line.merchandise.product.featuredImage?.url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={line.merchandise.product.featuredImage.url}
                  alt={line.merchandise.product.featuredImage.altText ?? line.merchandise.product.title}
                />
              ) : (
                ""
              )}
            </div>
            <div style={{ flex: 1 }}>
              <div className="cc-card__title">{line.merchandise.product.title}</div>
              <div className="cc-card__meta">qty {line.quantity} · {format(line.merchandise.price)}</div>
            </div>
          </li>
        ))}
      </ul>

      <div className="cc-cart-summary">
        <div className="cc-cart-summary__row">
          <span>Subtotal</span>
          <span>{format(cart.cost.subtotalAmount)}</span>
        </div>
        <div className="cc-cart-summary__row cc-cart-summary__row--total">
          <span>Total</span>
          <span>{format(cart.cost.totalAmount)}</span>
        </div>
        <a className="cc-checkout-btn" href={cart.checkoutUrl}>
          Checkout →
        </a>
        <p style={{ color: "#888", fontSize: "0.75rem", marginTop: "0.5rem" }}>
          The checkout URL is signed by Shopify and includes this cart.
          Shopify Functions configured for the store will run when the buyer
          proceeds.
        </p>
      </div>

      <p style={{ marginTop: "1.5rem" }}>
        <button
          onClick={() => {
            clearCartId();
            setCart(null);
            setStatus("empty");
          }}
          style={{
            background: "transparent",
            border: "1px solid var(--cc-border)",
            padding: "0.4rem 0.75rem",
            borderRadius: "0.25rem",
            cursor: "pointer",
          }}
        >
          Reset cart (this device)
        </button>
      </p>
    </section>
  );
}
