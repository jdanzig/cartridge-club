"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Hit = {
  id: string;
  handle: string;
  title: string;
  vendor: string;
  featuredImage?: { url: string; altText?: string } | null;
  priceRange: { minVariantPrice: { amount: string; currencyCode: string } };
};

const PREDICTIVE_QUERY = /* GraphQL */ `
  query PredictiveSearch($q: String!) {
    predictiveSearch(query: $q, types: [PRODUCT]) {
      products {
        id handle title vendor
        featuredImage { url altText }
        priceRange { minVariantPrice { amount currencyCode } }
      }
    }
  }
`;

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!q || q.length < 2) {
      setHits([]);
      return;
    }

    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      try {
        const domain = process.env.NEXT_PUBLIC_SHOPIFY_STORE_DOMAIN;
        const token = process.env.NEXT_PUBLIC_SHOPIFY_STOREFRONT_API_TOKEN;
        const version = process.env.NEXT_PUBLIC_SHOPIFY_API_VERSION ?? "2025-01";
        if (!domain || !token) {
          throw new Error("Missing NEXT_PUBLIC_SHOPIFY_* env vars");
        }
        const response = await fetch(
          `https://${domain}/api/${version}/graphql.json`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Shopify-Storefront-Access-Token": token,
            },
            body: JSON.stringify({ query: PREDICTIVE_QUERY, variables: { q } }),
            signal: controller.signal,
          }
        );
        const payload = await response.json();
        if (payload.errors?.length) {
          throw new Error(payload.errors.map((e: { message: string }) => e.message).join("; "));
        }
        setHits(payload.data?.predictiveSearch?.products ?? []);
        setError(null);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError(err instanceof Error ? err.message : String(err));
        setHits([]);
      }
    }, 200);

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [q]);

  return (
    <section>
      <h1>Search the store</h1>
      <p>Type-ahead via the Storefront API <code>predictiveSearch</code> query.</p>
      <div className="cc-search">
        <input
          type="search"
          placeholder="e.g. n64 controller, hdmi, cleaning"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus
        />
      </div>
      {error && <p className="cc-warning" style={{ marginTop: "1rem" }}>{error}</p>}

      <ul style={{ padding: 0, listStyle: "none", marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {hits.map((h) => (
          <li
            key={h.id}
            style={{
              display: "flex",
              gap: "0.75rem",
              alignItems: "center",
              padding: "0.5rem 0.75rem",
              border: "1px solid var(--cc-border)",
              borderRadius: "0.5rem",
              background: "white",
            }}
          >
            <div className="cc-product-img" style={{ width: 48, height: 48, flex: "none" }}>
              {h.featuredImage?.url && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={h.featuredImage.url} alt={h.featuredImage.altText ?? h.title} />
              )}
            </div>
            <div style={{ flex: 1 }}>
              <Link href={`/`} style={{ fontWeight: 600 }}>{h.title}</Link>
              <div className="cc-card__meta">{h.vendor} · {h.priceRange.minVariantPrice.amount} {h.priceRange.minVariantPrice.currencyCode}</div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
