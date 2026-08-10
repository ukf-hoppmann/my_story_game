# Entscheidung: Promptprofil und aktuelle Modellwahl

Status: Auswahlsemantik umgesetzt am 2026-08-10; Story-Workflow bleibt geplant.

Diese Entscheidung konkretisiert die frühere Entscheidung zu Spielzustand und
Persistenz für `GameConfiguration` und die Entscheidung zur
anbieterunabhängigen LLM-Anbindung für Promptvorbereitung und Modellwahl. Die
verbindlichen Architekturregeln bleiben unter
[`../../../.harness/architecture/llm-integration.md`](../../../.harness/architecture/llm-integration.md).

## Ausgangslage

`GameConfiguration` speichert bisher einen allgemeinen Erzählstil, Perspektive,
Steuerungsmodus und je eine logische Modellreferenz für Story, Extraction und
Summary. Das Promptpaket `story.base`/`1` trennt die erzählerischen Vorgaben
dagegen bereits in eigenständige Kategorien mit konkreten Optionen und
Defaults.

Diese beiden Modelle passen nicht vollständig zusammen. Werte wie
`style.dark-fantasy` können Genre, Ton und Prosa vermischen. Gleichzeitig
werden die aktuell verwendeten Modelle bereits zentral je Aufgabe in
`configs/llm.toml` ausgewählt. Ein zusätzlicher Modell-Snapshot in jeder Partie
ist für den gewünschten Betrieb nicht erforderlich.

## Explizites Promptprofil

`GameConfiguration` erhält ein explizites `PromptProfile` mit genau den
Story-Kategorien:

```text
PromptProfile
├── genre
├── tone
├── prose_style
├── perspective
├── pacing
├── control_mode
├── player_agency
├── consequence
├── challenge
└── content_profile
```

Jedes Feld speichert die lokale Options-ID seiner bekannten Kategorie, zum
Beispiel:

```json
{
  "genre": "dark_fantasy",
  "tone": "balanced",
  "prose_style": "balanced",
  "perspective": "third_person_limited",
  "pacing": "balanced",
  "control_mode": "player",
  "player_agency": "strict",
  "consequence": "balanced",
  "challenge": "balanced",
  "content_profile": "teen"
}
```

Die Kategorie muss im Wert nicht wiederholt werden. `balanced` bleibt trotz
seiner Verwendung in mehreren Kategorien eindeutig, weil es immer in einem
konkret benannten Feld steht.

`narration_style_id` entfällt. Die bisher getrennten Felder `perspective_id`
und `control_mode_id` gehen in das Promptprofil ein. Es gibt keine
Legacy-Übersetzung für Werte wie `style.dark`, `style.dark-fantasy`,
`perspective.third-person` oder `control.player`; der noch junge API-, Domain-
und Persistenzvertrag wird geschlossen auf das neue Modell umgestellt.

Außerhalb des Promptprofils bleiben:

- `language`;
- `narrative_boundaries`;
- `prompt_package_id`;
- `prompt_package_version`.

Paket-ID und Version bleiben die konkrete Referenz auf das versionierte
Promptpaket. Der bestehende Catalog-Vertrag
`load(package_id, version)` und die Ablage
`prompts/<package-id>/<version>.toml` bleiben erhalten. Ein zusätzlicher Digest
oder eine weitergehende Replay-Garantie wird nicht eingeführt.

## Defaults und Validierung

Paketdefaults dienen nur dazu, das vollständige Profil einer neuen Partie
vorzubelegen. Das anschließend gewählte Profil wird vollständig gespeichert,
auch wenn alle Werte den Defaults entsprechen. Eine spätere Änderung eines
Defaults verändert daher keine bereits gespeicherte Auswahl.

Die Application validiert vor dem Speichern, dass jede Options-ID in ihrer
Kategorie des referenzierten Promptpakets vorhanden ist. Der Domainwert prüft
seine eigene Struktur, lädt aber kein Promptpaket. Eine ungültige Auswahl wird
als konkreter Application-Fehler an die API gegeben. Die API übersetzt ihn in
eine verständliche Antwort, damit die UI eine andere Auswahl anfordern kann.
Es gibt keinen stillen Ersatz und keinen automatischen Fallback.

## Aufgabenspezifische Promptvorbereitung

Gespeicherte Options-IDs sind keine ausreichenden Anweisungen für ein Modell.
Vor dem Adapter lädt die Application das referenzierte Promptpaket und löst die
für den jeweiligen Auftrag relevanten IDs in ihre verständlichen
Beschreibungen auf. Sie bestimmt damit Reihenfolge und Bedeutung; der spätere
Story- oder Extraction-Workflow ergänzt seinen Kontext und erzeugt den
vollständigen, aufgabenspezifischen Request.

Story-Erzeugung verwendet:

- den Task `story_generation`;
- alle zehn Werte aus `PromptProfile`;
- Sprache und erzählerische Grenzen;
- relevante WorldState- und StoryState-Daten;
- die aktuelle Spielereingabe.

WorldState-Extraction verwendet dagegen:

- den Task `worldstate_extraction`;
- ausschließlich die Paketoption `extraction.combined`;
- den gerade erzeugten Storytext;
- den relevanten aktuellen WorldState.

Die Story-Kategorien werden nicht in den Extraction-Prompt übernommen.
`extraction.combined` ist umgekehrt kein Bestandteil des gespeicherten
Story-Promptprofils. Summary bleibt außerhalb dieser Promptprofil-Erweiterung;
das dafür konfigurierte Modell wird dadurch nicht entfernt.

Der Adapter erhält bereits den fachlich vollständigen Request. Er darf ihn als
Provider-Nachrichten, benannte Textabschnitte, JSON oder eine andere technisch
passende Darstellung serialisieren. Er wählt keine Kategorien, löst keine
Options-IDs auf und setzt keine fachlichen Defaults. Nach dem Aufruf übersetzt
er die technische Providerantwort in den konkreten Erfolgstyp oder einen
anbieterunabhängigen `LLMError`.

## Aktuelle Modellwahl

Die Modellreferenzen `story_model_id`, `extraction_model_id` und
`summary_model_id` entfallen aus `GameConfiguration`. Entscheidend ist die
aktuelle Systemkonfiguration, nicht der Modellstand einer vergangenen
GameState-Revision.

Die zentrale LLM-Konfiguration speichert weiterhin:

- die verfügbaren logischen Modelleinträge;
- die aktive Modellreferenz für Story;
- die aktive Modellreferenz für Extraction;
- die aktive Modellreferenz für Summary;
- die jeweilige technische Zuordnung zu Provider und konkreter Modell-ID.

`LlmTask` kennzeichnet dabei nur den Auftrag `story`, `extraction` oder
`summary`. Die Konfigurations- und Verdrahtungsgrenze verwendet diese Kennung,
um die aktive Referenz auf eine konkrete `ModelSelection` aufzulösen. Der
anschließende `LLMGenerationCall` transportiert bereits `provider_id` und
`model_id`; Adapter und Provider-Client entscheiden das Modell nicht erneut.

Spätere zusätzliche Modelle können in den zentralen Modellkatalog aufgenommen
werden. Eine spätere UI zur globalen Modellwahl muss die aktive Referenz je
Aufgabe persistent ändern. Der heutige dateibasierte Vertrag bleibt bis zu
einer solchen Erweiterung die maßgebliche Persistenz.

## Beibehaltene Vertragsgrenzen

Story, Extraction und Summary behalten aufgabenspezifische Application-Ports,
Requests und Ergebnisse. Die gemeinsame Hülle `LLMGenerationCall[RequestT]`
darf Modellwahl und technische Optionen transportieren, ersetzt aber keinen
dieser Verträge durch einen universellen `PreparedPrompt` oder `LLMService`.

Provider-URLs, Secrets, Rohprompts, Rohantworten und laufende Modellaufrufe
bleiben außerhalb von `GameConfiguration` und des dauerhaft gespeicherten
GameState.

## Betrachtete Alternativen

### Allgemeines Auswahl-Dictionary

Ein beliebiges Dictionary würde die erwarteten Kategorien im Domain- und
API-Vertrag unsichtbar machen. Das explizite Promptprofil hält stattdessen alle
zulässigen Felder verständlich und vollständig fest.

### Nur Paketdefaults und Overrides speichern

Verworfen wurde, lediglich Abweichungen vom Paketdefault zu speichern. Das
effektive Profil wäre dann nur zusammen mit einer erneuten Defaultauflösung
sichtbar. Die vollständige Auswahl wird deshalb direkt persistiert.

### Modelle je Partie einfrieren

Verworfen wurde der Snapshot der drei logischen Modellreferenzen in jeder
`GameConfiguration`. Die aktive Auswahl ist eine globale Systemeinstellung je
Aufgabe und wird beim konkreten Call aufgelöst.

### Options-IDs im Adapter auflösen

Verworfen wurde, Promptbedeutung in den Adapter zu verschieben. Die Application
kennt Aufgabe und Domainkontext; der Adapter besitzt ausschließlich
Darstellung, Transport und technische Ergebnisnormalisierung.

## Folgen

Die Umsetzung ersetzt den bestehenden Domain-, API- und Persistenzvertrag
bewusst ohne Legacy-Schicht. Technische Dokumente beschreiben den neuen
Ist-Zustand; Story-Orchestrierung, Summary-Promptvorbereitung und eine UI für
Paketoptionen oder globale Modellwahl bleiben davon getrennte Folgearbeiten.
