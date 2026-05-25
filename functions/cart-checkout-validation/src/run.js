// @ts-check
/**
 * cart-checkout-validation
 *
 * Returns validation errors when the cart contains:
 *  - An accessory marked `requires_accessory: [...]` without one of those
 *    accessory handles also present.
 *  - Two AV accessories that target different `output_connector` standards
 *    (e.g. HDMI upscaler + PAL SCART cable). Off by default; toggled by the
 *    `cc_functions.block_on_mixed_output` shop metafield.
 *
 * @typedef {{
 *   cart: { lines: Array<{
 *     id: string,
 *     quantity: number,
 *     merchandise: { product: {
 *       handle: string,
 *       requiresAccessory: { value: string } | null,
 *       outputConnector: { value: string } | null,
 *       accessoryKind: { value: string } | null,
 *       compatibleConsoles: { references: { nodes: Array<{ handle: string }> } } | null,
 *     } }
 *   }> },
 *   validationConfig: {
 *     enabled: { value: string } | null,
 *     blockOnMixedOutput: { value: string } | null,
 *   },
 * }} Input
 *
 * @typedef {{ message: string, target: string }} ValidationError
 * @typedef {{ errors: ValidationError[] }} Output
 */

function parseList(value) {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function bool(metafield) {
  if (!metafield) return null;
  return metafield.value === "true" || metafield.value === "1";
}

/**
 * @param {Input} input
 * @returns {Output}
 */
export function run(input) {
  const enabled = bool(input.validationConfig?.enabled);
  if (enabled === false) {
    return { errors: [] };
  }

  const handlesInCart = new Set(
    input.cart.lines.map((line) => line.merchandise.product.handle)
  );
  const errors = [];

  // ── 1. requires_accessory ──────────────────────────────────────────────
  for (const line of input.cart.lines) {
    const required = parseList(line.merchandise.product.requiresAccessory?.value);
    if (required.length === 0) continue;
    const satisfied = required.some((handle) => handlesInCart.has(handle));
    if (!satisfied) {
      const friendly = required.join(", ");
      errors.push({
        message: `${line.merchandise.product.handle} needs one of: ${friendly}. Add a compatible item to continue.`,
        target: `$.cart.lines[${input.cart.lines.indexOf(line)}].quantity`,
      });
    }
  }

  // ── 2. mixed AV output standards ───────────────────────────────────────
  const blockOnMixed = bool(input.validationConfig?.blockOnMixedOutput) ?? true;
  if (blockOnMixed) {
    const avOutputs = new Set();
    for (const line of input.cart.lines) {
      const product = line.merchandise.product;
      if (product.accessoryKind?.value !== "cable" && product.accessoryKind?.value !== "av" && product.accessoryKind?.value !== "adapter") {
        continue;
      }
      if (product.outputConnector?.value) {
        avOutputs.add(product.outputConnector.value);
      }
    }
    const standards = [...avOutputs];
    // Composite + s_video together is fine (same family); flag only when an HDMI/scart pair is mixed.
    const hasHdmi = standards.includes("hdmi");
    const hasScart = standards.includes("scart_rgb");
    if (hasHdmi && hasScart) {
      errors.push({
        message: "These video accessories target different output standards (HDMI + SCART). Please choose one setup type.",
        target: "$.cart",
      });
    }
  }

  return { errors };
}

export default run;
