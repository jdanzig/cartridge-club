import { test } from "node:test";
import assert from "node:assert/strict";
import { run } from "./run.js";

function line(handle, kind, consoles) {
  return {
    id: `gid://shopify/CartLine/${handle}`,
    quantity: 1,
    cost: { amountPerQuantity: { amount: "10.00", currencyCode: "USD" } },
    merchandise: {
      product: {
        handle,
        accessoryKind: kind ? { value: kind } : null,
        compatibleConsoles: {
          references: { nodes: consoles.map((h) => ({ handle: h })) },
        },
      },
    },
  };
}

const baseConfig = {
  enabled: null,
  percent: null,
  requiredKinds: null,
};

test("no discount when required kinds are missing", () => {
  const out = run({
    cart: { lines: [line("a", "controller", ["n64"])] },
    discountConfig: baseConfig,
  });
  assert.deepEqual(out.discounts, []);
});

test("controller + cable + maintenance on same console → discount applied", () => {
  const out = run({
    cart: {
      lines: [
        line("n64-replacement-controller", "controller", ["n64"]),
        line("composite-cable",            "cable",      ["n64", "snes"]),
        line("cartridge-cleaning-kit",     "maintenance", ["n64", "snes"]),
      ],
    },
    discountConfig: baseConfig,
  });
  assert.equal(out.discounts.length, 1);
  assert.equal(out.discounts[0].targets.length, 3);
  assert.equal(out.discounts[0].value.percentage.value, "10");
});

test("required kinds on different consoles → no discount", () => {
  const out = run({
    cart: {
      lines: [
        line("n64-replacement-controller", "controller", ["n64"]),
        line("composite-cable",            "cable",      ["snes"]),
        line("cartridge-cleaning-kit",     "maintenance", ["genesis"]),
      ],
    },
    discountConfig: baseConfig,
  });
  assert.deepEqual(out.discounts, []);
});

test("merchant disables discount via shop metafield", () => {
  const out = run({
    cart: {
      lines: [
        line("a", "controller", ["n64"]),
        line("b", "cable",      ["n64"]),
        line("c", "maintenance", ["n64"]),
      ],
    },
    discountConfig: { ...baseConfig, enabled: { value: "false" } },
  });
  assert.deepEqual(out.discounts, []);
});

test("custom percent value flows through", () => {
  const out = run({
    cart: {
      lines: [
        line("a", "controller", ["n64"]),
        line("b", "cable",      ["n64"]),
        line("c", "maintenance", ["n64"]),
      ],
    },
    discountConfig: { ...baseConfig, percent: { value: "15" } },
  });
  assert.equal(out.discounts[0].value.percentage.value, "15");
});
