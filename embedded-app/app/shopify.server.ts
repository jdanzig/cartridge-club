/**
 * Shopify App Remix configuration.
 *
 * Reads SHOPIFY_API_KEY / SECRET / SCOPES / APP_URL from .env. Sessions
 * persist via Prisma if you wire one up; for a sandbox we ship the
 * in-memory store, which is fine for `shopify app dev` but not for
 * production.
 */

import "@shopify/shopify-app-remix/adapters/node";
import {
  ApiVersion,
  AppDistribution,
  shopifyApp,
} from "@shopify/shopify-app-remix/server";

const shopify = shopifyApp({
  apiKey: process.env.SHOPIFY_API_KEY ?? "",
  apiSecretKey: process.env.SHOPIFY_API_SECRET ?? "",
  apiVersion: ApiVersion.January25,
  scopes: (process.env.SCOPES ?? "").split(","),
  appUrl: process.env.SHOPIFY_APP_URL ?? "",
  authPathPrefix: "/auth",
  distribution: AppDistribution.AppStore,
  isEmbeddedApp: true,
  future: { unstable_newEmbeddedAuthStrategy: true },
});

export default shopify;
export const apiVersion = ApiVersion.January25;
export const addDocumentResponseHeaders = shopify.addDocumentResponseHeaders;
export const authenticate = shopify.authenticate;
export const unauthenticated = shopify.unauthenticated;
export const login = shopify.login;
export const registerWebhooks = shopify.registerWebhooks;
export const sessionStorage = shopify.sessionStorage;
