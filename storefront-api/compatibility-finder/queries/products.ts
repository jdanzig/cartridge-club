/**
 * Products are filtered by `compatible_consoles` metaobject reference and by
 * `accessory_kind` (the "goal" the customer picked). Both are stored on
 * `custom.*` metafields by the admin-api seeders.
 *
 * Storefront API filtering on metafield references works at query time via
 * the `query` argument's filter syntax — but the metafield must first be
 * exposed as a filter in the shop's storefront settings, OR we filter
 * client-side after fetching by tag. To stay portable we fetch by tag (which
 * the seeders also write: `console:<handle>` and `category:<kind>`).
 */

export const PRODUCTS_BY_CONSOLE_AND_KIND = /* GraphQL */ `
  query ProductsByConsoleAndKind($query: String!, $first: Int!) {
    products(first: $first, query: $query, sortKey: BEST_SELLING) {
      nodes {
        id
        handle
        title
        vendor
        productType
        tags
        featuredImage { url altText width height }
        priceRange { minVariantPrice { amount currencyCode } }
        variants(first: 1) { nodes { id sku availableForSale } }
        warning: metafield(namespace: "custom", key: "warning") { value }
        requires: metafield(namespace: "custom", key: "requires_accessory") { value }
        accessoryKind: metafield(namespace: "custom", key: "accessory_kind") { value }
        compatibleConsoles: metafield(namespace: "custom", key: "compatible_consoles") {
          references(first: 25) {
            nodes {
              ... on Metaobject {
                handle
                fields { key value }
              }
            }
          }
        }
      }
    }
  }
`;

export function buildProductsQuery(consoleHandle: string, kind: string | null): string {
  const parts = [`tag:'console:${consoleHandle}'`];
  if (kind) parts.push(`tag:'category:${kind}'`);
  parts.push(`status:active`);
  return parts.join(" AND ");
}
