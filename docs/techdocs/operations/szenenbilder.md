# Szenenbilder betreiben

Szenenbilder erzeugen zu einem Spielzug ein Bild: Ein LLM schreibt aus den
letzten Zügen einen Bildprompt, Modal (GPU-Dienst) rendert ihn. Ohne Abschnitt
`[scene_image]` ist das Feature aus; die mitgelieferte `app.toml` schaltet es
ein. Wo der Zielbetrieb Modal nicht erreichen kann, wird es abgeschaltet.
Schnittstelle: [HTTP-API](../../development/interfaces/http-api.md).

## Einschalten

In `Backend/configs/app.toml`:

```toml
[scene_image]
enabled = true
turn_window = 3          # aus wie vielen letzten Zügen der Prompt entsteht
width = 1024
height = 1024
refine = false           # Standard für die optionale Verfeinerung
refine_model = "juggernaut-xl-ragnarok"
refine_strength = 0.35   # 0.1 – 0.8, wie stark die Verfeinerung ändern darf
compact_prompt_max_words = 60

[scene_image.modal]
url = "https://…--image-gpu.modal.run"
control_url = "https://…--image-control.modal.run"
model = "z-image-turbo"
timeout_seconds = 900
# negative_prompt = ""
# refine_negative_prompt = ""
```

Bei `enabled = true` ist `[scene_image.modal]` Pflicht (`url`, `control_url`,
`model`); unbekannte Felder und ungültige Werte lassen den Start scheitern.
Die Konfiguration wird beim Start gelesen: Änderungen brauchen einen Neustart.

Der Bildprompt wird mit dem Modell der Aufgabe `scene_image` aus
`configs/llm.toml` geschrieben (Vorgabe `[task_models] scene_image` und
`[generation_options.scene_image]`, danach in den Einstellungen wählbar;
Katalogeinträge mit `task = "scene_image"`).
Derselbe Aufruf schreibt bei aktiver Verfeinerung auch den Kurzprompt.

## Versionen und Anzeige

Jede Erzeugung legt ein neues Bild an, auch mehrere zum selben Zug; nichts wird
überschrieben. Jedes Bild merkt sich den Zug, zu dem es entstand. Im Spiel zeigt
die Fließtext-Ansicht beim Scrollen das Bild des gerade sichtbaren Zuges (oder
das letzte davor), die Chat-Ansicht hängt es an die Antwort seines Zuges. Gibt
es mehrere Versionen zu einem Zug, blättert man mit den Pfeilen am Bild.

## Zugangsdaten

Das Modal-Proxy-Token gehört **nicht** in `app.toml`. Lege
`Backend/configs/scene_image.secrets.toml` an (gitignoriert; Vorlage:
`scene_image.secrets.toml.example`):

```toml
[modal]
key = "wk-…"
secret = "ws-…"
```

Es wird bei jedem Aufruf neu gelesen, ein getauschtes Token wirkt ohne
Neustart. Fehlt die Datei, schlägt eine Erzeugung mit einer Konfigurations-
Fehlermeldung am Bild fehl (nicht der Start).

## Ausschalten

`enabled = false` (oder den Abschnitt `[scene_image]` entfernen) und neu starten. Der Server baut dann keinen
Modal-Client, kontaktiert Modal nie, die Szenenbild-Endpunkte antworten 409
`scene_image_disabled`, `GET /api/v1/scene-images/capabilities` meldet
`enabled: false`, und das Frontend zeigt nur den Platzhalter ohne Knopf.

## Ablauf und Fehler

1. Knopfdruck → Bild als `pending` gespeichert, 202.
2. Hintergrund: Bildprompt (LLM) → bei Refine Kurzprompt (LLM, ≤ 60 Wörter)
   → Modal `/generate` (Hauptmodell) → bei Refine zweiter `/generate`-Aufruf
   mit dem ersten Bild → Bild gespeichert (`ready`).
3. Jeder erwartete Fehler (LLM, Modal, Token) wird am Bild als `failed` mit
   Meldung gespeichert. Es gibt keinen automatischen Retry; ein neuer Knopfdruck
   startet neu. Kaltstart von Modal dauert etwa 40 s, ein warmer Aufruf etwa 5 s.
4. Wird der Server mitten in einer Erzeugung beendet, bleibt das Bild
   `pending`. Nach Ablauf von `2 × timeout_seconds + 120 s` gilt es als
   verwaist und blockiert den Zug nicht mehr.

## Tests

Die regulären Tests nutzen keine echte Modal-Verbindung (`httpx.MockTransport`
bzw. ein lokaler Fake-Server). Ein Livetest gegen Modal kostet Geld und läuft
nur auf ausdrückliche Freigabe.
