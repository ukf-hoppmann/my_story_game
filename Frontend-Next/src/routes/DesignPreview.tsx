import { Button } from "../components/Button/Button";
import { Chip } from "../components/Chip/Chip";
import { ImageSlot } from "../components/ImageSlot/ImageSlot";
import { Panel } from "../components/Panel/Panel";
import { ArrowRightIcon, PersonIcon } from "../icons";

/**
 * Temporary visual check for the Schritt-1 UI primitives against the
 * approved mockups. Replaced by the real routes (Landing/Bibliothek/Wizard/
 * Play) in Schritt 5 — not meant to ship as a real screen.
 */
export function DesignPreview() {
  return (
    <div style={{ padding: 40, display: "flex", flexDirection: "column", gap: 24, maxWidth: 480 }}>
      <div style={{ display: "flex", gap: 12 }}>
        <Button icon={<ArrowRightIcon />}>Handlung ausführen</Button>
        <Button variant="ghost">Anmelden</Button>
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Chip selected>Dark Fantasy</Chip>
        <Chip selected={false}>Fantasy</Chip>
        <Chip>Umsehen</Chip>
      </div>

      <Panel title="Figuren" icon={<PersonIcon />}>
        <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>Bran, der Wirt — wirkt besorgt.</p>
      </Panel>

      <ImageSlot label="Platzhalter · Szenenbild folgt" style={{ height: 200 }} />
      <ImageSlot shape="circle" placeholderIcon={<PersonIcon />} style={{ width: 60, height: 60 }} />
    </div>
  );
}
