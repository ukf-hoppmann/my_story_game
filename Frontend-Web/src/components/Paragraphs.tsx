interface Props {
  text: string;
}

/**
 * Renders narration text as separate <p> elements, one per paragraph.
 *
 * Paragraphs are expected to be separated by a blank line (\n\n) as
 * instructed in the story prompts, but a single \n is also accepted as a
 * fallback for text that isn't split that cleanly. If no line breaks are
 * present at all, the whole text is rendered as one paragraph, same as
 * before.
 */
export function Paragraphs({ text }: Props) {
  const paragraphs = text
    .split(/\n{2,}/)
    .flatMap((block) => block.split("\n"))
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0);

  if (paragraphs.length === 0) return null;

  return (
    <>
      {paragraphs.map((paragraph, index) => (
        <p key={index}>{paragraph}</p>
      ))}
    </>
  );
}
