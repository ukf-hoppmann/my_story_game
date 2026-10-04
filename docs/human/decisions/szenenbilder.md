# Entscheidung: Szenenbilder per Knopfdruck über Modal

Status: Backend, API und Play-Screen umgesetzt (2026-10-04); Livetest gegen
Modal, WorldState im Bildprompt, automatische Erzeugung und Modellprofile sind
Folgearbeit (Backlog `STORY-012` und Kinder).

## Entscheidung

Der Spieler kann im Play-Screen zur aktuellen Szene ein Bild erzeugen. Ein
zusätzlicher LLM-Aufruf macht aus den letzten Zügen (Standard: 3) einen
Bildprompt. Modal rendert das Bild (Z-Image Turbo, optional gefolgt von einer
SDXL-Verfeinerung mit `juggernaut-xl-ragnarok`). Das Bild liegt in Postgres und
wird im Frontend angezeigt.

- **Modal ist der einzige Anbieter und abschaltbar.** `[scene_image] enabled`
  steht standardmäßig auf `false`; die API meldet das über eine
  Capability-Abfrage, das Frontend blendet den Knopf aus. Grund: Der
  Zielbetrieb kann Modal eventuell nicht erreichen.
- **Modell und Refine wählbar** (Modell aus der Modal-Liste, Refine an/aus,
  Stärke 0,1–0,8, Standard 0,35), pro Anfrage.
- **Zwei Promptstile.** Z-Image verträgt lange Prompts, das SDXL-Modell der
  Verfeinerung braucht einen kurzen (≤ 60 Wörter, ~77 Token). Bei Refine
  kürzt ein zweiter LLM-Schritt den langen Prompt. Ein volles Modellprofil-
  System gibt es noch nicht (Backlog `TASK-040`).
- **Erst nur die Zugtexte.** Der Promptschreiber sieht zunächst nur die
  Zugtexte; WorldState (Figurenaussehen, Ort) kommt als zweiter Schritt
  (Backlog `TASK-038`).
- **Fester Rahmen:** 1024×1024, zufälliger Seed, mit dem Bild gespeichert.
- **Asynchron, ohne Retry, idempotent pro Zug.** Der POST antwortet sofort mit
  202; ein laufendes Bild desselben Zugs wird zurückgegeben statt ein zweites
  zu starten. Fehler werden am Bild gespeichert.
- **Kein Teil des GameState.** Bilder haben keinen Revisionsbezug.

## Architektur

Nach `llm-integration.md` §7 hat die Bildgenerierung einen eigenen Port samt
Fehlerfamilie (`SceneImageRenderer`, `ImageGenError`), getrennt von den
Text-Ports. Die Prompt-Schritte sind task-spezifische LLM-Ports
(`SceneImagePromptPort`, `CompactImagePromptPort`) mit einem Task
`scene_image` in `llm.toml`. Workflow (`GenerateSceneImage`), Annahme
(`RequestSceneImage`) und Leseoperationen sind getrennte Operationen; Modal-
Client und Postgres-Speicher sind Adapter, die nur der Composition Root
verdrahtet.

## Alternativen

- *Bild synchron im Request:* verworfen, Kaltstart ~40 s würde Requests
  blockieren.
- *Automatischer Retry:* verworfen, jede Erzeugung kostet Geld.
- *Job-Service wie im Schwesterprojekt:* nicht übernommen; Hintergrundaufgabe
  des API-Prozesses genügt.
- *Bilder im Dateisystem:* verworfen, `bytea` hält Bild und Metadaten in einer
  Transaktion und im Backup.
