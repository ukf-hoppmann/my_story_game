import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("boots the Redux store and router, rendering the Landing page at /", () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "Geschichten, die deinen Entscheidungen folgen." }),
    ).toBeInTheDocument();
  });
});
