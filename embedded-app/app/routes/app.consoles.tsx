import { ActionFunctionArgs, json, LoaderFunctionArgs } from "@remix-run/node";
import { Form, useActionData, useLoaderData, useNavigation } from "@remix-run/react";
import {
  BlockStack, Button, Card, FormLayout, IndexTable, InlineStack,
  Layout, Page, Text, TextField, Banner,
} from "@shopify/polaris";

import { authenticate } from "../shopify.server";

const LIST_QUERY = `#graphql
  query ConsolesAll {
    metaobjects(type: "console", first: 50, sortKey: "release_year") {
      nodes {
        id handle
        name: field(key: "name") { value }
        manufacturer: field(key: "manufacturer") { value }
        release_year: field(key: "release_year") { value }
        generation: field(key: "generation") { value }
      }
    }
  }
`;

const CREATE_MUTATION = `#graphql
  mutation CreateConsole($metaobject: MetaobjectCreateInput!) {
    metaobjectCreate(metaobject: $metaobject) {
      metaobject { id handle }
      userErrors { field message }
    }
  }
`;

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  const res = await admin.graphql(LIST_QUERY);
  const body = await res.json();
  return json({ consoles: body.data?.metaobjects?.nodes ?? [] });
};

export const action = async ({ request }: ActionFunctionArgs) => {
  const { admin } = await authenticate.admin(request);
  const formData = await request.formData();

  const handle = String(formData.get("handle") ?? "").trim();
  const name = String(formData.get("name") ?? "").trim();
  const manufacturer = String(formData.get("manufacturer") ?? "").trim();
  const releaseYear = String(formData.get("release_year") ?? "").trim();
  const generation = String(formData.get("generation") ?? "").trim();

  if (!handle || !name) {
    return json({ error: "handle and name are required" }, { status: 400 });
  }

  const res = await admin.graphql(CREATE_MUTATION, {
    variables: {
      metaobject: {
        type: "console",
        handle,
        fields: [
          { key: "name", value: name },
          { key: "manufacturer", value: manufacturer },
          { key: "release_year", value: releaseYear || "0" },
          { key: "generation", value: generation },
          { key: "region_codes", value: JSON.stringify([]) },
          { key: "av_output_types", value: JSON.stringify([]) },
        ],
      },
    },
  });
  const body = await res.json();
  const userErrors = body.data?.metaobjectCreate?.userErrors ?? [];
  if (userErrors.length) {
    return json({ error: userErrors.map((e: any) => e.message).join("; ") }, { status: 400 });
  }
  return json({ created: body.data?.metaobjectCreate?.metaobject });
};

export default function Consoles() {
  const { consoles } = useLoaderData<typeof loader>();
  const actionData = useActionData<typeof action>();
  const nav = useNavigation();

  return (
    <Page title="Consoles">
      <Layout>
        <Layout.Section>
          <Card>
            <BlockStack gap="300">
              <Text as="h2" variant="headingMd">Existing consoles</Text>
              {consoles.length === 0 ? (
                <Banner tone="info">
                  No consoles yet. Run <code>admin-api/seed_consoles.py</code>
                  or create one below.
                </Banner>
              ) : (
                <IndexTable
                  resourceName={{ singular: "console", plural: "consoles" }}
                  itemCount={consoles.length}
                  headings={[
                    { title: "Handle" },
                    { title: "Name" },
                    { title: "Manufacturer" },
                    { title: "Year" },
                    { title: "Generation" },
                  ]}
                  selectable={false}
                >
                  {consoles.map((c: any, idx: number) => (
                    <IndexTable.Row id={c.id} key={c.id} position={idx}>
                      <IndexTable.Cell>{c.handle}</IndexTable.Cell>
                      <IndexTable.Cell>{c.name?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{c.manufacturer?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{c.release_year?.value}</IndexTable.Cell>
                      <IndexTable.Cell>{c.generation?.value}</IndexTable.Cell>
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
              <Text as="h2" variant="headingMd">Add a console</Text>
              {actionData && "error" in actionData && (
                <Banner tone="critical">{actionData.error}</Banner>
              )}
              {actionData && "created" in actionData && actionData.created && (
                <Banner tone="success">Created {actionData.created.handle}</Banner>
              )}
              <Form method="post">
                <FormLayout>
                  <InlineStack gap="300" wrap>
                    <TextField label="Handle" name="handle" autoComplete="off" />
                    <TextField label="Display name" name="name" autoComplete="off" />
                    <TextField label="Manufacturer" name="manufacturer" autoComplete="off" />
                    <TextField label="Release year" name="release_year" autoComplete="off" />
                    <TextField label="Generation" name="generation" autoComplete="off" />
                  </InlineStack>
                  <Button submit loading={nav.state === "submitting"}>
                    Create console
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
