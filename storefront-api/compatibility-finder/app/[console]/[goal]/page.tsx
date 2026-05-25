import Link from "next/link";
import { storefront, formatMoney } from "@/lib/shopify";
import {
  PRODUCTS_BY_CONSOLE_AND_KIND,
  buildProductsQuery,
} from "@/queries/products";
import AddToCartButton from "./AddToCartButton";

type Params = { console: string; goal: string };

type ProductNode = {
  id: string;
  handle: string;
  title: string;
  vendor: string;
  tags: string[];
  featuredImage?: { url: string; altText?: string } | null;
  priceRange: { minVariantPrice: { amount: string; currencyCode: string } };
  variants: { nodes: Array<{ id: string; sku?: string; availableForSale: boolean }> };
  warning?: { value: string } | null;
  requires?: { value: string } | null;
  accessoryKind?: { value: string } | null;
};

export const revalidate = 30;

export default async function ProductsPage({ params }: { params: Params }) {
  const q = buildProductsQuery(params.console, params.goal === "all" ? null : params.goal);
  let products: ProductNode[] = [];
  let error: string | null = null;
  try {
    const data = await storefront<{ products: { nodes: ProductNode[] } }>(
      PRODUCTS_BY_CONSOLE_AND_KIND,
      { query: q, first: 24 },
      { tags: [`products:${params.console}:${params.goal}`] }
    );
    products = data.products.nodes;
  } catch (err) {
    error = err instanceof Error ? err.message : String(err);
  }

  return (
    <section>
      <ol className="cc-stepper">
        <li className="cc-stepper__crumb"><Link href="/">1. Console</Link></li>
        <li className="cc-stepper__crumb"><Link href={`/${params.console}`}>2. Goal</Link></li>
        <li className="cc-stepper__crumb cc-stepper__crumb--current">3. Products</li>
        <li className="cc-stepper__crumb"><Link href="/cart">4. Cart</Link></li>
      </ol>

      <h1>Compatible {params.goal === "starter_kit" ? "bundles" : params.goal}s for {params.console}</h1>
      <p>
        Filtered by tags <code>console:{params.console}</code> and{" "}
        <code>category:{params.goal}</code>.{" "}
        <Link href={`/${params.console}`}>change goal</Link>
      </p>

      {error && (
        <div className="cc-warning" style={{ margin: "1rem 0" }}>
          Storefront error: {error}
        </div>
      )}

      {!error && products.length === 0 && (
        <div className="cc-empty">
          <p>No matching products yet.</p>
          <p>Did you run <code>seed_products.py</code> and <code>bulk_tag_by_console.py</code>?</p>
        </div>
      )}

      <div className="cc-grid" style={{ marginTop: "2rem" }}>
        {products.map((p) => {
          const variant = p.variants.nodes[0];
          return (
            <article key={p.id} className="cc-card">
              <div className="cc-product-img">
                {p.featuredImage?.url ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img src={p.featuredImage.url} alt={p.featuredImage.altText ?? p.title} />
                ) : (
                  "no image"
                )}
              </div>
              <div className="cc-card__title">{p.title}</div>
              <div className="cc-card__meta">
                {p.vendor} · {formatMoney(p.priceRange.minVariantPrice)}
              </div>
              <div>
                <span className="cc-badge cc-badge--works">
                  Compatible with {params.console}
                </span>
              </div>
              {p.warning?.value && (
                <p className="cc-warning">{p.warning.value}</p>
              )}
              {variant?.availableForSale === false && (
                <p className="cc-warning">Currently out of stock</p>
              )}
              <AddToCartButton
                variantId={variant?.id}
                disabled={!variant?.availableForSale}
              />
            </article>
          );
        })}
      </div>
    </section>
  );
}
