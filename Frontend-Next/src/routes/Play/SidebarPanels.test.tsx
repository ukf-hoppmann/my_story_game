import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Fact, Goal, WorldEntity } from "../../api/types";
import { CharactersPanel, FactsPanel, GoalsPanel } from "./SidebarPanels";

describe("GoalsPanel", () => {
  it("shows an empty state when there are no goals", () => {
    render(<GoalsPanel goals={[]} />);

    expect(screen.getByText("Noch keine Ziele bekannt.")).toBeInTheDocument();
  });

  it("renders title, description and status without a progress bar", () => {
    const goals: Goal[] = [
      {
        id: "goal-1",
        kind: "main",
        title: "Finde den verschwundenen Kurier",
        description: "Die Spur beginnt am Marktplatz.",
        status: "open",
        related_entity_ids: [],
      },
    ];
    render(<GoalsPanel goals={goals} />);

    expect(screen.getByText("Finde den verschwundenen Kurier")).toBeInTheDocument();
    expect(screen.getByText("Die Spur beginnt am Marktplatz.")).toBeInTheDocument();
    expect(screen.getByText("Offen")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });
});

describe("FactsPanel", () => {
  it("shows an empty state when there are no facts", () => {
    render(<FactsPanel facts={[]} />);

    expect(screen.getByText("Noch nichts über die Welt bekannt.")).toBeInTheDocument();
  });

  it("renders full fact sentences, not truncated labels", () => {
    const facts: Fact[] = [
      {
        id: "fact-1",
        statement: "Der Regen hat die meisten Spuren auf dem Marktplatz fortgespült.",
        visibility: { scope: "public", actor_id: null },
        subject_id: null,
      },
    ];
    render(<FactsPanel facts={facts} />);

    expect(
      screen.getByText("Der Regen hat die meisten Spuren auf dem Marktplatz fortgespült."),
    ).toBeInTheDocument();
  });
});

describe("CharactersPanel", () => {
  it("shows an empty state when there are no characters", () => {
    render(<CharactersPanel entities={[]} />);

    expect(screen.getByText("Noch keine Figuren bekannt.")).toBeInTheDocument();
  });

  it("ignores non-character entities and shows name, role and description", () => {
    const entities: WorldEntity[] = [
      {
        id: "char-1",
        kind: "character",
        label: "Bran",
        description: "Wirkt besorgt, sagt aber wenig.",
        actor: { role: "npc" },
        conditions: [],
        aliases: [],
      },
      {
        id: "item-1",
        kind: "item",
        label: "Laterne",
        description: "",
        actor: null,
        conditions: [],
        aliases: [],
      },
    ];
    render(<CharactersPanel entities={entities} />);

    expect(screen.getByText("Bran")).toBeInTheDocument();
    expect(screen.getByText("NPC")).toBeInTheDocument();
    expect(screen.getByText("Wirkt besorgt, sagt aber wenig.")).toBeInTheDocument();
    expect(screen.queryByText("Laterne")).not.toBeInTheDocument();
  });

  it("omits the role badge when the entity has no actor profile", () => {
    const entities: WorldEntity[] = [
      { id: "char-1", kind: "character", label: "Unbekannter", description: "", actor: null, conditions: [], aliases: [] },
    ];
    render(<CharactersPanel entities={entities} />);

    expect(screen.getByText("Unbekannter")).toBeInTheDocument();
    expect(screen.queryByText("NPC")).not.toBeInTheDocument();
    expect(screen.queryByText("Spieler")).not.toBeInTheDocument();
  });
});
