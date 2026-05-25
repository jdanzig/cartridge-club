import { ActionFunctionArgs, json, LoaderFunctionArgs } from "@remix-run/node";
import { Form, useActionData, useLoaderData, useNavigation } from "@remix-run/react";
import {
  Banner, BlockStack, Button, Card, FormLayout, IndexTable, InlineStack,
  Layout, Page, Select, Text, TextField,
} from "@shopify/polaris";

import { authenticate } from "../shopify.server";

const RULES_QUERY = `#graphql
  query RulesAll {
    consoles: metaobjects(type: "console", first: 50) {
      nodes { id handle name: field(key: "name") { value } }
    }
    rules: metaobjects(type: "compatibility_rule", first: 100) {
      nodes {
        id handle
        source: field(key: "source_console") {
          reference { ... on Metaobject { handle name: field(key: "name") { value } } }
        }
        target: field(key: "target_console") {
          reference { ... on Metaobject { handle name: field(key: "name") { value } } }
        }
        kind: field(key: "accessory_kind") { value }
        status: field(key: "status") { value }
        note: field(key: "note") { value }
      }
    }
  }
`;

const CREATE_RULE = `#graphql
  mutation CreateRule($metaobject: MetaobjectCreateInput!) {
    metaobjectCreate(metaobject: $metaobject) {
      metaobject { id handle }
      userErrors { field message }
    }
  }
`;

const STATUSES = [
  { label: "Works", value: "works" },
  { label: "Works with caveats", value: "works_with_caveats" },
  { label: "Requires adapter", value: "requires_adapter" },
  { label: "Incompatible", value: "incompatible" },
];

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  const res = await admin.graphql(RULES_QUERY);
  const body = await res.json();
  return json({
    consoles: body.data?.consoles?.nodes ?? [],
    rules: body.data?.rules?.nodes ?? [],
  });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  const fd = await request.formData();

  const sourceGid = String(fd.get("source_console") ?? "");
  const targetGid = String(fd.get("target_console") ?? "");
  const kind = String(fd.get("accessory_kind") ?? "");
  const status = String(fd.get("status") ?? "");
  const note = String(fd.get("note") ?? "");
  const handle = `${sourceGid.split("/").pop()}-${targetGid.split("/").pop()}-${kind || "any"}-${Date.now()}`;

  if (!sourceGid || !targetGid || !status) {
    return json({ error: "source, target, and status are required" }, { status: 400 });
  }

  const res = await admin.graphql(CREATE_RULE, {
    variables: {
      metaobject: {
        type: "compatibility_rule",
        handle,
        fields: [
          { key: "source_console", value: sourceGid },
          { key: "target_console", value: targetGid },
          { key: "accessory_kind", value: kind },
          { key: "status", value: status },
          { key: "note", value: note },
        ],
      },
    },
  });
  const body = await res.json();
  const errs = body.data?.metaobjectCreate?.userErrors ?? [];
  if (errs.length) return json({ error: errs.map((e: any) => e.message).join("; ") }, { status: 400 });
  return json({ created: body.data?.metaobjectCreate?.metaobject });
};

export default function Rules() {
  const { consoles, rules } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const nav = useNavigation();

  const consoleOptions = consoles.map((c: any) => ({
    label: c.name?.value ?? c.handle,
    value: c.id,
  }));

  return (
    <Page title="Compatibility Rules">
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text as="h2" variant="headingMd">All rules</Text>
              {rules.length === 0 ? (
                <Banner tone="info">
                  No compatibility rules yet. Seed them with
                  <code> admin-api/seed_rules.py </code> or create one below.
                </Banner>
              ) : (
                <IndexTable
                  resourceName={{ singular: "rule", plural: "rules" }}
                  itemCount={rules.length}
                  headings={[
                    { title: "Source" }, { title: "Target" }, { title: "Kind" },
                    { title: "Status" }, { title: "Note" },
                  ]}
                  selectable={false}
                >
                  {rules.map((r: any, idx: number) => (
                    <IndexTable.Row id={r.id} key={r.id} position={idx}>
                      <IndexTable.Cell>{r.source?.reference?.name?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{r.target?.reference?.name?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{r.kind?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{r.status?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{r.note?.value}</IndexTable.Cell>
                    </IndexTable.Row>
                  ))}
                </IndexTable>
              )}
            </BlockStack>
          </Card>
        </Layout.Section>

        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text as="h2" variant="headingMd">Add a rule</Text>
              {actionData && "error" in actionData && (
                <Banner tone="critical">{actionData.error}</Banner>
              )}
              {actionData && "created" in actionData && actionData.created && (
                <Banner tone="success">Created rule {actionData.created.handle}</Banner>
              )}
              <Form method="post">
                <FormLayout>
                  <InlineStack gap="300" wrap>
                    <Select label="Source console" name="source_console"
                            options={[{ label: "Choose…", value: "" }, ...consoleOptions]} />
                    <Select label="Target console" name="target_console"
                            options={[{ label: "Choose…", value: "" }, ...consoleOptions]} />
                    <TextField label="Accessory kind" name="accessory_kind"
                               placeholder="controller, cable, av…" autoComplete="off" />
                    <Select label="Status" name="status"
                            options={[{ label: "Choose…", value: "" }, ...STATUSES]} />
                  </InlineStack>
                  <TextField label="Note" name="note" multiline={3} autoComplete="off" />
                  <Button submit loading={nav.state === "submitting"}>
                    Create rule
                  </Button>
                </FormLayout>
              </Form>
            </BlockStack>
          </Card>
        </Layout.Section>
      </Layout>
    </Page>
  );
}
