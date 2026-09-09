export interface PlaceholderScreenProps {
  text: string;
}

/** Stand-in for a screen not built yet — replaced as the roadmap steps land. */
export function PlaceholderScreen({ text }: PlaceholderScreenProps) {
  return (
    <div style={{ padding: 40, color: "var(--text-muted)", fontFamily: "var(--font-ui)" }}>
      {text}
    </div>
  );
}
