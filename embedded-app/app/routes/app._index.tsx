import { json, LoaderFunctionArgs } from "@remix-run/node";
import { useLoaderData, Link } from "@remix-run/react";
import {
  Page, Layout, Card, BlockStack, Text, Badge, InlineStack,
} from "@shopify/polaris";

import { authenticate } from "../shopify.server";

const COUNTS_QUERY = `#graphql
  query Counts {
    consoles: metaobjects(type: "console", first: 1) {
      edges { node { id } }
    }
    rules: metaobjects(type: "compatibility_rule", first: 1) {
      edges { node { id } }
    }
    products(first: 1) { edges { node { id } } }
  }
`;

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  // Sanity ping — confirms scopes resolve and the session token works.
  const ok = await admin.graphql(COUNTS_QUERY).then((r) => r.ok).catch(() => false);
  return json({ ok });
};

export default function Dashboard() {
  const { ok } = useLoaderData<typeof loader>();
  return (
    <Page title="Compatibility Manager">
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <InlineStack gap="200" align="space-between">
                <Text as="h2" variant="headingMd">Source of truth</Text>
                <Badge tone={ok ? "success" : "critical"}>{ok ? "Connected" : "API unreachable"}</Badge>
              </InlineStack>
              <Text as="p">
                Every value edited in this app is written to Shopify metaobjects
                or shop metafields. Functions, the Liquid theme, and the
                headless storefront all read from those — no app database.
              </Text>
            </BlockStack>
          </Card>
        </Layout.Section>

        <Layout.Section variant="oneThird">
          <Card>
            <BlockStack gap="200">
              <Text as="h3" variant="headingSm">Consoles</Text>
              <Text as="p">Manage the `console` metaobjects that every other surface references.</Text>
              <Link to="/app/consoles">Open →</Link>
            </BlockStack>
          </Card>
        </Layout.Section>
        <Layout.Section variant="oneThird">
          <Card>
            <BlockStack gap="200">
              <Text as="h3" variant="headingSm">Compatibility Rules</Text>
              <Text as="p">CRUD `compatibility_rule` metaobjects in a console × accessory matrix.</Text>
              <Link to="/app/rules">Open →</Link>
            </BlockStack>
          </Card>
        </Layout.Section>
        <Layout.Section variant="oneThird">
          <Card>
            <BlockStack gap="200">
              <Text as="h3" variant="headingSm">Function Configuration</Text>
              <Text as="p">Toggle Functions and tune thresholds. Writes shop metafields under `cc_functions`.</Text>
              <Link to="/app/functions">Open →</Link>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
