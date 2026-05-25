export const CART_CREATE = /* GraphQL */ `
  mutation CartCreate($lines: [CartLineInput!]) {
    cartCreate(input: { lines: $lines }) {
      cart {
        id
        checkoutUrl
        totalQuantity
        cost { totalAmount { amount currencyCode } subtotalAmount { amount currencyCode } }
        lines(first: 50) {
          nodes {
            id
            quantity
            merchandise {
              ... on ProductVariant {
                id sku
                product { handle title featuredImage { url altText } }
                price { amount currencyCode }
              }
            }
          }
        }
      }
      userErrors { field message }
    }
  }
`;

export const CART_LINES_ADD = /* GraphQL */ `
  mutation CartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
    cartLinesAdd(cartId: $cartId, lines: $lines) {
      cart {
        id
        checkoutUrl
        totalQuantity
        cost { totalAmount { amount currencyCode } subtotalAmount { amount currencyCode } }
        lines(first: 50) {
          nodes {
            id quantity
            merchandise {
              ... on ProductVariant {
                id sku
                product { handle title featuredImage { url altText } }
                price { amount currencyCode }
              }
            }
          }
        }
      }
      userErrors { field message }
    }
  }
`;

export const CART_QUERY = /* GraphQL */ `
  query Cart($id: ID!) {
    cart(id: $id) {
      id
      checkoutUrl
      totalQuantity
      cost { totalAmount { amount currencyCode } subtotalAmount { amount currencyCode } }
      lines(first: 50) {
        nodes {
          id quantity
          merchandise {
            ... on ProductVariant {
              id sku
              product { handle title featuredImage { url altText } }
              price { amount currencyCode }
            }
          }
        }
      }
    }
  }
`;
