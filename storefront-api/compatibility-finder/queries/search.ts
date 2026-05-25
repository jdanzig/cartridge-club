export const PREDICTIVE_SEARCH = /* GraphQL */ `
  query PredictiveSearch($q: String!) {
    predictiveSearch(query: $q, types: [PRODUCT]) {
      products {
        id
        handle
        title
        vendor
        featuredImage { url altText }
        priceRange { minVariantPrice { amount currencyCode } }
      }
    }
  }
`;
