import { test } from "node:test";
import assert from "node:assert/strict";
import { run } from "./run.js";

function line(handle, opts = {}) {
  return {
    id: `gid://shopify/CartLine/${handle}`,
    quantity: opts.quantity ?? 1,
    merchandise: {
      product: {
        handle,
        bundleType: opts.bundleType ? { value: opts.bundleType } : null,
        bundleComponents: opts.bundleComponents
          ? { value: JSON.stringify(opts.bundleComponents) }
          : null,
      },
    },
  };
}

test("non-bundle products are not expanded", () => {
  const out = run({
    cart: { lines: [line("composite-cable")] },
    bundleConfig: { componentLookup: null },
  });
  assert.deepEqual(out.operations, []);
});

test("starter-kit expands when lookup covers every component", () => {
  const lookup = {
    "n64-replacement-controller": "gid://shopify/ProductVariant/1",
    "composite-cable":            "gid://shopify/ProductVariant/2",
    "cartridge-cleaning-kit":     "gid://shopify/ProductVariant/3",
  };
  const out = run({
    cart: {
      lines: [
        line("n64-revival-kit", {
          bundleType: "starter_kit",
          bundleComponents: [
            "n64-replacement-controller",
            "composite-cable",
            "cartridge-cleaning-kit",
          ],
        }),
      ],
    },
    bundleConfig: { componentLookup: { value: JSON.stringify(lookup) } },
  });
  assert.equal(out.operations.length, 1);
  assert.equal(out.operations[0].expand.expandedCartItems.length, 3);
});

test("missing variant in lookup → no expansion attempted", () => {
  const out = run({
    cart: {
      lines: [
        line("n64-revival-kit", {
          bundleType: "starter_kit",
          bundleComponents: ["composite-cable"],
        }),
      ],
    },
    bundleConfig: { componentLookup: { value: JSON.stringify({}) } },
  });
  assert.deepEqual(out.operations, []);
});
