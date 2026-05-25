/**
 * Function configuration — writes shop metafields under namespace
 * `cc_functions` that every Function reads at runtime.
 */

import { ActionFunctionArgs, json, LoaderFunctionArgs } from "@remix-run/node";
import { Form, useActionData, useLoaderData, useNavigation } from "@remix-run/react";
import {
  Banner, BlockStack, Button, Card, Checkbox, FormLayout, InlineStack,
  Layout, Page, Text, TextField,
} from "@shopify/polaris";

import { authenticate } from "../shopify.server";

const SHOP_METAFIELDS = `#graphql
  query CcFunctionConfig {
    shop {
      id
      validationEnabled:        metafield(namespace: "cc_functions", key: "validation_enabled") { value }
      blockOnMixedOutput:       metafield(namespace: "cc_functions", key: "block_on_mixed_output") { value }
      starterDiscountEnabled:   metafield(namespace: "cc_functions", key: "starter_discount_enabled") { value }
      starterDiscountPercent:   metafield(namespace: "cc_functions", key: "starter_discount_percent") { value }
      starterRequiredKinds:     metafield(namespace: "cc_functions", key: "starter_discount_required_kinds") { value }
      bundleComponentMap:       metafield(namespace: "cc_functions", key: "bundle_component_variant_map") { value }
    }
  }
`;

const METAFIELDS_SET = `#graphql
  mutation Set($metafields: [MetafieldsSetInput!]!) {
    metafieldsSet(metafields: $metafields) {
      metafields { id key namespace }
      userErrors { field message code }
    }
  }
`;

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  const res = await admin.graphql(SHOP_METAFIELDS);
  const body = await res.json();
  return json(body.data);
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  const fd = await request.formData();
  const shopId = String(fd.get("shop_id") ?? "");

  if (!shopId) {
    return json({ error: "Missing shop id" }, { status: 400 });
  }

  const metafields = [
    {
      ownerId: shopId, namespace: "cc_functions", key: "validation_enabled",
      type: "boolean", value: fd.get("validationEnabled") ? "true" : "false",
    },
    {
      ownerId: shopId, namespace: "cc_functions", key: "block_on_mixed_output",
      type: "boolean", value: fd.get("blockOnMixedOutput") ? "true" : "false",
    },
    {
      ownerId: shopId, namespace: "cc_functions", key: "starter_discount_enabled",
      type: "boolean", value: fd.get("starterDiscountEnabled") ? "true" : "false",
    },
    {
      ownerId: shopId, namespace: "cc_functions", key: "starter_discount_percent",
      type: "number_integer", value: String(fd.get("starterDiscountPercent") ?? "10"),
    },
    {
      ownerId: shopId, namespace: "cc_functions", key: "starter_discount_required_kinds",
      type: "json", value: String(fd.get("starterRequiredKinds") ?? '["controller","cable","maintenance"]'),
    },
    {
      ownerId: shopId, namespace: "cc_functions", key: "bundle_component_variant_map",
      type: "json", value: String(fd.get("bundleComponentMap") ?? "{}"),
    },
  ];

  const res = await admin.graphql(METAFIELDS_SET, { variables: { metafields } });
  const body = await res.json();
  const errs = body.data?.metafieldsSet?.userErrors ?? [];
  if (errs.length) {
    return json({ error: errs.map((e: any) => e.message).join("; ") }, { status: 400 });
  }
  return json({ saved: true });
};

export default function FunctionConfig() {
  const data = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const nav = useNavigation();
  const shop = (data as any)?.shop;

  return (
    <Page title="Function configuration">
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text as="h2" variant="headingMd">Storage: shop metafields</Text>
              <Text as="p">
                These values are written to shop metafields under the
                <code> cc_functions </code> namespace. Each Function reads
                its own keys at runtime.
              </Text>
            </BlockStack>
          </Card>
        </Layout.Section>

        <Layout.Section>
          <Card>
            {actionData && "error" in actionData && (
              <Banner tone="critical">{actionData.error}</Banner>
            )}
            {actionData && "saved" in actionData && (
              <Banner tone="success">Saved.</Banner>
            )}
            <Form method="post">
              <input type="hidden" name="shop_id" value={shop?.id ?? ""} />
              <FormLayout>
                <Text as="h3" variant="headingSm">cart-checkout-validation</Text>
                <InlineStack gap="400" wrap>
                  <Checkbox name="validationEnabled" label="Enabled"
                            checked={shop?.validationEnabled?.value !== "false"} />
                  <Checkbox name="blockOnMixedOutput" label="Block mixed AV output (HDMI + SCART)"
                            checked={shop?.blockOnMixedOutput?.value !== "false"} />
                </InlineStack>

                <Text as="h3" variant="headingSm">product-discount</Text>
                <InlineStack gap="400" wrap>
                  <Checkbox name="starterDiscountEnabled" label="Enabled"
                            checked={shop?.starterDiscountEnabled?.value !== "false"} />
                  <TextField label="Discount percent" name="starterDiscountPercent"
                             type="number" autoComplete="off"
                             value={shop?.starterDiscountPercent?.value ?? "10"} />
                </InlineStack>
                <TextField label="Required accessory kinds (JSON list)"
                           name="starterRequiredKinds"
                           autoComplete="off"
                           helpText='e.g. ["controller","cable","maintenance"]'
                           value={shop?.starterRequiredKinds?.value ?? '["controller","cable","maintenance"]'} />

                <Text as="h3" variant="headingSm">cart-transform</Text>
                <TextField label="Bundle component variant map (JSON)"
                           name="bundleComponentMap"
                           multiline={4}
                           autoComplete="off"
                           helpText="Maps bundle component handles to variant GIDs."
                           value={shop?.bundleComponentMap?.value ?? "{}"} />

                <Button submit loading={nav.state === "submitting"}>
                  Save configuration
                </Button>
              </FormLayout>
            </Form>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
