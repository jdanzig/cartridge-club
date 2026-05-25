export const CONSOLES_QUERY = /* GraphQL */ `
  query Consoles {
    metaobjects(type: "console", first: 50) {
      nodes {
        handle
        fields {
          key
          value
        }
      }
    }
  }
`;

export type ConsoleRecord = {
  handle: string;
  name: string;
  manufacturer: string;
  releaseYear?: number;
  generation?: string;
};

export function parseConsoles(raw: {
  metaobjects: { nodes: Array<{ handle: string; fields: Array<{ key: string; value: string }> }> };
}): ConsoleRecord[] {
  return raw.metaobjects.nodes
    .map((n) => {
      const map = Object.fromEntries(n.fields.map((f) => [f.key, f.value]));
      return {
        handle: n.handle,
        name: map.name ?? n.handle,
        manufacturer: map.manufacturer ?? "",
        releaseYear: map.release_year ? Number(map.release_year) : undefined,
        generation: map.generation,
      };
    })
    .sort((a, b) => (a.releaseYear ?? 0) - (b.releaseYear ?? 0));
}
