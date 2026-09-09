import { describe, expect, it } from "vitest";
import { formatOptionLabel } from "./formatOptionLabel";

describe("formatOptionLabel", () => {
  it("title-cases a snake_case option id", () => {
    expect(formatOptionLabel("dark_fantasy")).toBe("Dark Fantasy");
  });

  it("handles single-word ids", () => {
    expect(formatOptionLabel("balanced")).toBe("Balanced");
  });

  it("handles multi-part ids", () => {
    expect(formatOptionLabel("third_person_limited")).toBe("Third Person Limited");
  });
});
