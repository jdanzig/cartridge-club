// @ts-check
/**
 * product-discount
 *
 * Applies a "Complete Your Setup" percent discount to every line in the cart
 * when the cart contains the merchant-defined required accessory kinds
 * (default: controller + cable + maintenance), all sharing at least one
 * compatible console.
 *
 * Configuration via shop metafields under namespace `cc_functions`:
 *   starter_discount_enabled         : "true" | "false"  (default true)
 *   starter_discount_percent         : "10"             (default 10)
 *   starter_discount_required_kinds  : '["controller","cable","maintenance"]'
 */

function parseJson(value, fallback) {
  if (!value) return fallback;
  try { return JSON.parse(value); } catch { return fallback; }
}

function bool(metafield, defaultValue) {
  if (!metafield) return defaultValue;
  return metafield.value === "true" || metafield.value === "1";
}

/**
 * @param {{ cart: any, discountConfig: any }} input
 */
export function run(input) {
  const enabled = bool(input.discountConfig?.enabled, true);
  if (!enabled) return { discounts: [] };

  const percent = Number(input.discountConfig?.percent?.value ?? "10");
  const requiredKinds = parseJson(
    input.discountConfig?.requiredKinds?.value,
    ["controller", "cable", "maintenance"],
  );

  // Build a map of accessory_kind → set of console handles covered by lines with that kind.
  /** @type {Record<string, Set<string>>} */
  const kindToConsoles = {};
  for (const line of input.cart.lines) {
    const product = line.merchandise.product;
    const kind = product.accessoryKind?.value;
    if (!kind) continue;
    const consoles = (product.compatibleConsoles?.references?.nodes ?? []).map(
      (n) => n.handle,
    );
    if (!kindToConsoles[kind]) kindToConsoles[kind] = new Set();
    for (const c of consoles) kindToConsoles[kind].add(c);
  }

  // Every required kind must be present, and there must be at least one
  // console handle common to all of them.
  for (const k of requiredKinds) {
    if (!kindToConsoles[k] || kindToConsoles[k].size === 0) {
      return { discounts: [] };
    }
  }
  const common = requiredKinds.reduce((acc, k) => {
    if (!acc) return new Set(kindToConsoles[k]);
    const next = new Set();
    for (const c of acc) if (kindToConsoles[k].has(c)) next.add(c);
    return next;
  }, /** @type {Set<string> | null} */ (null));
  if (!common || common.size === 0) {
    return { discounts: [] };
  }

  // Apply percent discount across all qualifying lines (those whose kind is
  // in requiredKinds and which list at least one of `common` consoles).
  const targets = [];
  for (const line of input.cart.lines) {
    const product = line.merchandise.product;
    if (!requiredKinds.includes(product.accessoryKind?.value)) continue;
    const consoles = (product.compatibleConsoles?.references?.nodes ?? []).map(
      (n) => n.handle,
    );
    if (!consoles.some((c) => common.has(c))) continue;
    targets.push({ cartLine: { id: line.id } });
  }

  if (targets.length === 0) return { discounts: [] };

  return {
    discounts: [
      {
        message: `Complete Your Setup — ${percent}% off`,
        targets,
        value: {
          percentage: { value: String(percent) },
        },
      },
    ],
  };
}

export default run;
