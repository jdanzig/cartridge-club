/**
 * Minimal Shopify Storefront API client.
 *
 * No SDK; the Storefront API surface is small enough that a raw
 * `fetch` against the JSON endpoint is clearer than another dependency.
 */

const DOMAIN = process.env.NEXT_PUBLIC_SHOPIFY_STORE_DOMAIN;
const TOKEN = process.env.NEXT_PUBLIC_SHOPIFY_STOREFRONT_API_TOKEN;
const API_VERSION = process.env.NEXT_PUBLIC_SHOPIFY_API_VERSION ?? "2025-01";

if (!DOMAIN || !TOKEN) {
  // Don't throw on import — we want builds to succeed without env, and the
  // pages render a clear "missing env" message instead.
  // eslint-disable-next-line no-console
  console.warn(
    "[shopify] NEXT_PUBLIC_SHOPIFY_STORE_DOMAIN and NEXT_PUBLIC_SHOPIFY_STOREFRONT_API_TOKEN must be set in .env.local"
  );
}

export type StorefrontResponse<T> = { data?: T; errors?: Array<{ message: string }> };

export async function storefront<T>(
  query: string,
  variables: Record<string, unknown> = {},
  init: { cache?: RequestCache; tags?: string[] } = {}
): Promise<T> {
  if (!DOMAIN || !TOKEN) {
    throw new Error("Shopify Storefront env vars missing. See README.");
  }

  const response = await fetch(
    `https://${DOMAIN}/api/${API_VERSION}/graphql.json`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Shopify-Storefront-Access-Token": TOKEN,
        Accept: "application/json",
      },
      body: JSON.stringify({ query, variables }),
      next: init.tags ? { tags: init.tags } : undefined,
      cache: init.cache,
    }
  );

  if (!response.ok) {
    throw new Error(`Storefront API ${response.status}: ${await response.text()}`);
  }

  const payload = (await response.json()) as StorefrontResponse<T>;
  if (payload.errors?.length) {
    throw new Error(payload.errors.map((e) => e.message).join("; "));
  }
  if (!payload.data) {
    throw new Error("Storefront API returned no data");
  }
  return payload.data;
}

// ── Small helpers shared across pages. ─────────────────────────────────────

export type Money = { amount: string; currencyCode: string };

export function formatMoney(m: Money | undefined): string {
  if (!m) return "";
  const n = Number(m.amount);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: m.currencyCode,
  }).format(n);
}
