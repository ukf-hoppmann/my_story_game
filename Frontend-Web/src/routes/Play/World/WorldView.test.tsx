import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { WorldState } from "../../../api/types";
import { WorldView } from "./WorldView";

const PUBLIC = { scope: "public" as const, actor_id: null };

function buildWorld(overrides: Partial<WorldState> = {}): WorldState {
  return {
    entities: [
      {
        id: "mara",
        kind: "character",
        label: "Mara",
        description: "Fährtenleserin aus dem Grenzland.",
        actor: { role: "player" },
        conditions: [{ name: "Erschöpft", description: "Kaum geschlafen." }],
        aliases: [],
      },
      {
        id: "hedda",
        kind: "character",
        label: "Wirtin Hedda",
        description: "Kennt jeden Klatsch.",
        actor: { role: "npc" },
        conditions: [],
        aliases: ["die Wirtin"],
      },
      {
        id: "krug",
        kind: "location",
        label: "Gasthaus Zum Krug",
        description: "Niedriger Schankraum.",
        actor: null,
        conditions: [],
        aliases: [],
      },
    ],
    links: [
      { id: "l1", source_id: "mara", target_id: "krug", kind: "located_in", visibility: PUBLIC, quantity: null, description: null },
    ],
    facts: [
      { id: "f1", statement: "Die Brücke ist eingestürzt.", visibility: PUBLIC, subject_id: "krug" },
      {
        id: "f2",
        statement: "Hedda verdünnt den Wein.",
        visibility: { scope: "actor_known", actor_id: "hedda" },
        subject_id: "hedda",
      },
    ],
    knowledge: [],
    rules: [{ id: "r1", statement: "Magie hat immer einen Preis.", visibility: PUBLIC }],
    goals: [],
    scene_location_ids: ["krug"],
    ...overrides,
  };
}

describe("WorldView", () => {
  it("lists characters with their main traits and opens the first one", () => {
    render(<WorldView world={buildWorld()} currentTurn={4} />);

    expect(screen.getByRole("tab", { name: /Figuren/ })).toHaveAttribute("aria-selected", "true");
    const list = screen.getByRole("navigation", { name: "Einträge" });
    expect(within(list).getByText("Gasthaus Zum Krug · Erschöpft")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Mara" })).toBeInTheDocument();
    expect(screen.getByText("Fährtenleserin aus dem Grenzland.")).toBeInTheDocument();
  });

  it("shows the full entry of a character picked from the list", async () => {
    render(<WorldView world={buildWorld()} currentTurn={4} />);

    await userEvent.click(screen.getByRole("button", { name: /Wirtin Hedda/ }));

    expect(screen.getByRole("heading", { level: 2, name: "Wirtin Hedda" })).toBeInTheDocument();
    expect(screen.getByText("auch: die Wirtin")).toBeInTheDocument();
    expect(screen.getByText("Figurenwissen: Wirtin Hedda")).toBeInTheDocument();
  });

  it("follows a relation into the tab of the linked entry", async () => {
    render(<WorldView world={buildWorld()} currentTurn={4} />);

    await userEvent.click(screen.getByRole("button", { name: "Gasthaus Zum Krug" }));

    expect(screen.getByRole("tab", { name: /Orte/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { level: 2, name: "Gasthaus Zum Krug" })).toBeInTheDocument();
    expect(screen.getByText("Aktuelle Szene")).toBeInTheDocument();
    expect(screen.getByText("hier befindet sich")).toBeInTheDocument();
  });

  it("says plainly that no knowledge is recorded and hides the turn slider", async () => {
    render(<WorldView world={buildWorld()} currentTurn={4} />);

    expect(screen.getByText("Noch kein Wissen erfasst.")).toBeInTheDocument();
    expect(screen.queryByRole("slider")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: /Wissen/ }));
    expect(screen.getByText(/Sobald Figuren Fakten erfahren/)).toBeInTheDocument();
  });

  it("shows forgotten knowledge and moves it back in time with the slider", () => {
    const world = buildWorld({
      knowledge: [
        { actor_id: "mara", fact_id: "f1", learned_at: 2, forgotten_at: 5 },
        { actor_id: "mara", fact_id: "f2", learned_at: 6, forgotten_at: null },
      ],
    });
    render(<WorldView world={world} currentTurn={8} />);

    expect(screen.getByText("vergessen Zug 5")).toBeInTheDocument();
    expect(screen.getByText("gelernt Zug 6")).toBeInTheDocument();
    expect(screen.getByText("Zug 8 (aktuell)")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("slider"), { target: { value: "3" } });

    expect(screen.getByText("Zug 3")).toBeInTheDocument();
    expect(screen.queryByText("vergessen Zug 5")).not.toBeInTheDocument();
    expect(screen.queryByText("gelernt Zug 6")).not.toBeInTheDocument();
    expect(screen.getByText("gelernt Zug 2")).toBeInTheDocument();
  });

  it("filters an actor's knowledge to forgotten entries", async () => {
    const world = buildWorld({
      knowledge: [
        { actor_id: "mara", fact_id: "f1", learned_at: 2, forgotten_at: 5 },
        { actor_id: "mara", fact_id: "f2", learned_at: 6, forgotten_at: null },
      ],
    });
    render(<WorldView world={world} currentTurn={8} />);

    await userEvent.click(screen.getByRole("button", { name: "Vergessen" }));

    expect(screen.getByText("vergessen Zug 5")).toBeInTheDocument();
    expect(screen.queryByText("gelernt Zug 6")).not.toBeInTheDocument();
  });

  it("lists facts with their subject and the world rules, filterable by visibility", async () => {
    render(<WorldView world={buildWorld()} currentTurn={4} />);
    await userEvent.click(screen.getByRole("tab", { name: /Fakten/ }));

    expect(screen.getByText("Die Brücke ist eingestürzt.")).toBeInTheDocument();
    expect(screen.getByText("Magie hat immer einen Preis.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Figurenwissen" }));

    expect(screen.queryByText("Die Brücke ist eingestürzt.")).not.toBeInTheDocument();
    expect(screen.getByText("Hedda verdünnt den Wein.")).toBeInTheDocument();
  });

  it("shows who knows what in the knowledge matrix", async () => {
    const world = buildWorld({
      knowledge: [{ actor_id: "hedda", fact_id: "f2", learned_at: 1, forgotten_at: null }],
    });
    render(<WorldView world={world} currentTurn={3} />);
    await userEvent.click(screen.getByRole("tab", { name: /Wissen/ }));

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Wirtin Hedda" })).toBeInTheDocument();
    expect(within(table).getByText("ab 1")).toBeInTheDocument();
  });
});
