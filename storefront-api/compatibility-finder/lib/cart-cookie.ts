/**
 * Cart ID is persisted client-side in localStorage. We avoid an httpOnly
 * cookie because every mutation in this demo runs from the client (the cart
 * API is a thin proxy that takes the id as input).
 */

const KEY = "cc_cart_id";

export function readCartId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function writeCartId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, id);
}

export function clearCartId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
}
