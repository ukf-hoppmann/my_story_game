# Versioniertes Prompt-Paket und dateibasierter Catalog

Status: Umgesetzt am 2026-08-10.

## Vertrag

Das Paket `story.base` in Version `1` liegt vollständig in
[`prompts/story.base/1.toml`](../../../prompts/story.base/1.toml). Es gibt keine
separaten Prompt-Textdateien. Der TOML-Aufbau enthält:

- genau die Tasks `story_generation` und `worldstate_extraction`;
- die auswählbaren Kategorien `genre`, `tone`, `prose_style`, `perspective`,
  `pacing`, `control_mode`, `player_agency`, `consequence`, `challenge`,
  `extraction` und `content_profile`;
- pro Kategorie Optionen mit kurzer konkreter Verhaltensbeschreibung und
  einen vorhandenen Default;
- die nicht auswählbare Directive `narrative_boundaries`.

`extraction` enthält zunächst ausschließlich `combined`. Ein Summary-Task ist
nicht Teil des Pakets und wurde nicht implementiert.

## Verantwortungsgrenzen

`PromptPackageCatalog` und seine unveränderlichen Promptwerte gehören zur
Application und kennen weder Dateispeicherung noch Provider. Infrastructure
implementiert `FilePromptPackageCatalog` und lädt
`<root>/<package-id>/<version>.toml`.

Der Loader unterscheidet fehlende Pakete von ungültigen Paketen und bricht bei
ungültigem TOML, falscher Identität, unbekannten Feldern oder Typen, leeren
Texten, doppelten IDs, fehlenden Optionen und ungültigen Defaults ab. IDs in
Paket- und Versionsreferenzen dürfen keine Pfadbestandteile enthalten.

`GameConfiguration` wurde nicht verändert. Sie speichert bereits
`narration_style_id`, `perspective_id`, `control_mode_id` und
`narrative_boundaries`, aber noch keine persistierten Auswahlfelder für Genre,
Tone, Pacing, Player Agency, Consequence, Challenge oder Content Profile. Die
Zuordnung dieser Werte wird erst vor dem Story-Use-Case entschieden und nicht
im Loader versteckt.

Die Directive `narrative_boundaries` darf das gewählte Content Profile
verschärfen, aber nicht lockern. Die Content-Profile sind im Paket mit ihren
Mindestgrenzen beschrieben. Das experimentelle Dokument
[`docs/tests/worldstate-extraction-prompts.md`](../../tests/worldstate-extraction-prompts.md)
bleibt ein Testpaket und ist kein Produktionsvertrag.

## Nicht enthalten

Es gibt keine Story-Orchestrierung, Story-API, StoryTurn-Persistenz, Live-
LLM-Aufrufe oder Summary-Aufgabe. WorldState-Extraction liefert im Paket nur
die Anweisung für unbestätigte Vorschläge; kanonischer Zustand wird dadurch
weder geschrieben noch als aktualisiert bezeichnet.
