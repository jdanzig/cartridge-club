import Link from "next/link";
import { storefront } from "@/lib/shopify";
import { CONSOLES_QUERY, parseConsoles } from "@/queries/consoles";

export const revalidate = 60;

export default async function ConsolePicker() {
  let consoles;
  try {
    const data = await storefront<{
      metaobjects: { nodes: Array<{ handle: string; fields: Array<{ key: string; value: string }> }> };
    }>(CONSOLES_QUERY, {}, { tags: ["consoles"] });
    consoles = parseConsoles(data);
  } catch (err) {
    return (
      <section className="cc-empty">
        <h1>Compatibility Finder</h1>
        <p>Could not load consoles from the Storefront API.</p>
        <p style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
          {err instanceof Error ? err.message : String(err)}
        </p>
      </section>
    );
  }

  return (
    <section>
      <ol className="cc-stepper">
        <li className="cc-stepper__crumb cc-stepper__crumb--current">1. Console</li>
        <li className="cc-stepper__crumb">2. Goal</li>
        <li className="cc-stepper__crumb">3. Products</li>
        <li className="cc-stepper__crumb">4. Cart</li>
      </ol>

      <h1>Which console are you setting up?</h1>
      <p>Pick one. We'll only show accessories that work with it.</p>

      <div className="cc-grid" style={{ marginTop: "2rem" }}>
        {consoles.map((c) => (
          <Link
            key={c.handle}
            href={`/${c.handle}`}
            className="cc-card"
            style={{ color: "inherit" }}
          >
            <div className="cc-card__title">{c.name}</div>
            <div className="cc-card__meta">
              {c.manufacturer} {c.releaseYear ? `· ${c.releaseYear}` : ""}
            </div>
            {c.generation && <div className="cc-badge cc-badge--works">{c.generation}</div>}
          </Link>
        ))}
      </div>
    </section>
  );
}
