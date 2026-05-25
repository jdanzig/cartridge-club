// @ts-check
/**
 * cart-transform
 *
 * When a starter-kit "parent" product (e.g. `n64-revival-kit`) is added to
 * cart, expand it at checkout into the component variants listed in
 * `custom.bundle_components`. Each component becomes its own line with the
 * parent priced as a fixed bundle discount across the children.
 *
 * Configuration:
 *   shop metafield `cc_functions.bundle_component_variant_map` is a JSON
 *   object mapping component product handles to their default variant GIDs:
 *     { "composite-cable": "gid://shopify/ProductVariant/123", ... }
 *
 *   The embedded app maintains this mapping. We can't resolve a handle to a
 *   variant GID inside the Function — Functions have no I/O.
 *
 * If the mapping is empty (e.g. first-run before the embedded app fills it
 * in), we no-op rather than breaking checkout.
 */

function parseJson(value) {
  if (!value) return null;
  try { return JSON.parse(value); } catch { return null; }
}

/**
 * @param {{ cart: { lines: any[] }, bundleConfig: { componentLookup: { value: string } | null } }} input
 */
export function run(input) {
  const operations = [];
  const lookup = parseJson(input.bundleConfig?.componentLookup?.value) ?? {};

  for (const line of input.cart.lines) {
    const product = line.merchandise.product;
    const isBundle = product.bundleType?.value === "starter_kit";
    if (!isBundle) continue;

    const components = parseJson(product.bundleComponents?.value);
    if (!Array.isArray(components) || components.length === 0) continue;

    const expandedLines = [];
    for (const handle of components) {
      const variantId = lookup[handle];
      if (!variantId) {
        // Skip — config incomplete. We deliberately don't fail the whole
        // expansion: better to leave the parent line intact than to drop
        // components silently mid-checkout.
        return { operations: [] };
      }
      expandedLines.push({
        merchandiseId: variantId,
        quantity: line.quantity,
      });
    }

    operations.push({
      expand: {
        cartLineId: line.id,
        expandedCartItems: expandedLines,
        // Title shown on the order summary for the parent group.
        title: product.handle,
      },
    });
  }

  return { operations };
}

export default run;
