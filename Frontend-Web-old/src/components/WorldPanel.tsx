import type { WorldEntity } from "../api/types";

interface Props {
  entities: WorldEntity[];
}

const ROLE_LABEL: Record<string, string> = {
  player: "Spieler",
  npc: "NPC",
  neutral: "Neutral",
};

function EntityCard({ entity }: { entity: WorldEntity }) {
  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <strong>{entity.label}</strong>
        {entity.actor && <span className="badge">{ROLE_LABEL[entity.actor.role] ?? entity.actor.role}</span>}
      </div>
      {entity.description && (
        <p style={{ margin: "4px 0 0", fontSize: "0.9rem", color: "var(--ink-dim)" }}>
          {entity.description}
        </p>
      )}
    </div>
  );
}

/** Simple read-only list view of the current characters and items in play. */
export function WorldPanel({ entities }: Props) {
  const characters = entities.filter((entity) => entity.kind === "character");
  const items = entities.filter((entity) => entity.kind === "item");

  return (
    <div>
      <h2>Figuren</h2>
      {characters.length === 0 && (
        <p style={{ color: "var(--ink-dim)" }}>Keine Figuren bekannt.</p>
      )}
      {characters.map((entity) => (
        <EntityCard key={entity.id} entity={entity} />
      ))}

      <h2 style={{ marginTop: 20 }}>Gegenstände</h2>
      {items.length === 0 && <p style={{ color: "var(--ink-dim)" }}>Keine Gegenstände bekannt.</p>}
      {items.map((entity) => (
        <EntityCard key={entity.id} entity={entity} />
      ))}
    </div>
  );
}
