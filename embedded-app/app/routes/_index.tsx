import { redirect, type LoaderFunctionArgs } from "@remix-run/node";

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const url = new URL(request.url);
  if (url.searchParams.get("shop")) {
    throw redirect(`/app?${url.searchParams.toString()}`);
  }
  return new Response(
    "Cartridge Club Compatibility Manager — install this app from the Shopify admin or Partner dashboard.",
    { status: 200, headers: { "content-type": "text/plain" } }
  );
};
