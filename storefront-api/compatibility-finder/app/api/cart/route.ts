/**
 * Thin server route that proxies cart mutations to the Storefront API.
 *
 * We don't strictly need server-side proxying for public Storefront tokens,
 * but running cart mutations server-side gives a single place to log
 * Function-rejected carts later, and keeps cart errors from leaking raw
 * GraphQL details to the client.
 */

import { NextRequest, NextResponse } from "next/server";
import { storefront } from "@/lib/shopify";
import { CART_CREATE, CART_LINES_ADD, CART_QUERY } from "@/queries/cart";

type LineInput = { merchandiseId: string; quantity: number };

type Body = {
  action: "create" | "add" | "get";
  cartId?: string | null;
  lines?: LineInput[];
};

type CartResponse = {
  cart: {
    id: string;
    checkoutUrl: string;
    totalQuantity: number;
    cost: { totalAmount: { amount: string; currencyCode: string }; subtotalAmount: { amount: string; currencyCode: string } };
    lines: { nodes: Array<unknown> };
  } | null;
  userErrors?: Array<{ field: string[]; message: string }>;
};

export async function POST(req: NextRequest) {
  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  try {
    if (body.action === "create") {
      const data = await storefront<{ cartCreate: CartResponse }>(CART_CREATE, {
        lines: body.lines ?? [],
      });
      if (data.cartCreate.userErrors?.length) {
        return NextResponse.json(
          { error: data.cartCreate.userErrors.map((e) => e.message).join("; ") },
          { status: 400 }
        );
      }
      return NextResponse.json({ cart: data.cartCreate.cart });
    }

    if (body.action === "add") {
      if (!body.cartId) {
        return NextResponse.json({ error: "cartId required for add" }, { status: 400 });
      }
      const data = await storefront<{ cartLinesAdd: CartResponse }>(CART_LINES_ADD, {
        cartId: body.cartId,
        lines: body.lines ?? [],
      });
      if (data.cartLinesAdd.userErrors?.length) {
        return NextResponse.json(
          { error: data.cartLinesAdd.userErrors.map((e) => e.message).join("; ") },
          { status: 400 }
        );
      }
      return NextResponse.json({ cart: data.cartLinesAdd.cart });
    }

    if (body.action === "get") {
      if (!body.cartId) {
        return NextResponse.json({ error: "cartId required for get" }, { status: 400 });
      }
      const data = await storefront<{ cart: CartResponse["cart"] }>(CART_QUERY, {
        id: body.cartId,
      });
      return NextResponse.json({ cart: data.cart });
    }

    return NextResponse.json({ error: `Unknown action ${body.action}` }, { status: 400 });
  } catch (err) {
    return NextResponse.json(
      { error: err instanceof Error ? err.message : String(err) },
      { status: 500 }
    );
  }
}
