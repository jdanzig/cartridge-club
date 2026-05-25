// Smoke tests for cart-checkout-validation.run.
// Run with: node --test src/run.test.js

import { test } from "node:test";
import assert from "node:assert/strict";
import { run } from "./run.js";

function line(handle, extras = {}) {
  return {
    id: `gid://shopify/CartLine/${handle}`,
    quantity: 1,
    merchandise: {
      product: {
        handle,
        requiresAccessory: extras.requiresAccessory ?? null,
        outputConnector: extras.outputConnector ?? null,
        accessoryKind: extras.accessoryKind ?? null,
        compatibleConsoles: extras.compatibleConsoles ?? null,
      },
    },
  };
}

test("empty cart passes", () => {
  const out = run({
    cart: { lines: [] },
    validationConfig: { enabled: null, blockOnMixedOutput: null },
  });
  assert.equal(out.errors.length, 0);
});

test("requires_accessory: missing required item raises an error", () => {
  const out = run({
    cart: {
      lines: [
        line("replacement-analog-stick", {
          requiresAccessory: { value: JSON.stringify(["n64-replacement-controller"]) },
        }),
      ],
    },
    validationConfig: { enabled: null, blockOnMixedOutput: null },
  });
  assert.equal(out.errors.length, 1);
  assert.match(out.errors[0].message, /n64-replacement-controller/);
});

test("requires_accessory: required item present clears the error", () => {
  const out = run({
    cart: {
      lines: [
        line("replacement-analog-stick", {
          requiresAccessory: { value: JSON.stringify(["n64-replacement-controller"]) },
        }),
        line("n64-replacement-controller"),
      ],
    },
    validationConfig: { enabled: null, blockOnMixedOutput: null },
  });
  assert.equal(out.errors.length, 0);
});

test("mixed AV: HDMI + SCART rejected", () => {
  const out = run({
    cart: {
      lines: [
        line("hdmi-upscaler", {
          accessoryKind: { value: "av" },
          outputConnector: { value: "hdmi" },
        }),
        line("scart-adapter", {
          accessoryKind: { value: "adapter" },
          outputConnector: { value: "scart_rgb" },
        }),
      ],
    },
    validationConfig: { enabled: null, blockOnMixedOutput: null },
  });
  assert.equal(out.errors.length, 1);
  assert.match(out.errors[0].message, /different output standards/);
});

test("disabling validation via shop metafield skips all checks", () => {
  const out = run({
    cart: {
      lines: [
        line("replacement-analog-stick", {
          requiresAccessory: { value: JSON.stringify(["n64-replacement-controller"]) },
        }),
      ],
    },
    validationConfig: { enabled: { value: "false" }, blockOnMixedOutput: null },
  });
  assert.equal(out.errors.length, 0);
});
