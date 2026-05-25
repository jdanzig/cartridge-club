import Link from "next/link";

const GOALS = [
  { handle: "controller", title: "Controllers & Adapters", emoji: "🎮",
    description: "Replacement controllers, USB adapters, Bluetooth receivers." },
  { handle: "av",         title: "Video & Audio",          emoji: "📺",
    description: "HDMI upscalers, S-Video cables, SCART adapters, switch boxes." },
  { handle: "maintenance",title: "Cleaning & Maintenance", emoji: "🧼",
    description: "Cartridge cleaning kits, replacement save batteries, contact cleaner." },
  { handle: "storage",    title: "Storage & Display",      emoji: "📦",
    description: "Display stands, dust covers, label protectors, wall mounts." },
  { handle: "starter_kit",title: "Starter Bundles",        emoji: "📦",
    description: "All-in-one kits for getting a console back on the TV fast." },
];

export default function GoalPicker({ params }: { params: { console: string } }) {
  return (
    <section>
      <ol className="cc-stepper">
        <li className="cc-stepper__crumb">
          <Link href="/">1. Console</Link>
        </li>
        <li className="cc-stepper__crumb cc-stepper__crumb--current">2. Goal</li>
        <li className="cc-stepper__crumb">3. Products</li>
        <li className="cc-stepper__crumb">4. Cart</li>
      </ol>

      <h1>What are you looking for?</h1>
      <p>
        Console: <strong>{params.console}</strong>.{" "}
        <Link href="/">change</Link>
      </p>

      <div className="cc-grid" style={{ marginTop: "2rem" }}>
        {GOALS.map((g) => (
          <Link
            key={g.handle}
            href={`/${params.console}/${g.handle}`}
            className="cc-card"
            style={{ color: "inherit" }}
          >
            <div style={{ fontSize: "2rem" }}>{g.emoji}</div>
            <div className="cc-card__title">{g.title}</div>
            <div className="cc-card__meta">{g.description}</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
