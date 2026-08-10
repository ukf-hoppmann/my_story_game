# Geplante Story-Initialisierung

Status: Zielbild und Umsetzungsplanung. Es ist noch kein Produktcode für die
Story-Initialisierung implementiert.

## Ziel

Ein User kann einen anfänglichen freien Prompt wie „Maren und Almas gehen in
den Dungeon“ eingeben. Das System erzeugt daraus mit den Systemprompts und
der GameConfiguration einen vollständigen, aber zunächst transienten
StoryState. Zu diesem Zeitpunkt gibt es weder einen kanonischen WorldState noch
eine bisherige Story-Chronologie.

Die spätere Initial-Extraction leitet aus diesem StoryState einen WorldState
ab. Erst wenn beide Ergebnisse erfolgreich und fachlich validiert vorliegen,
legt ein separater Workflow einen GameRun und dessen GameState in Revision 1
an.

## Phasen und Grenzen

```text
Phase 1 — jetzt geplant
Initialprompt + Konfiguration
    -> initiale Story-Prosa
    -> transienter StoryState
    -> opt-in Live-Test gibt JSON aus

Phase 2 — später
StoryState
    -> initiale WorldState-Extraction
    -> transienter, validierter WorldState

Phase 3 — später
StoryState + WorldState
    -> atomare Anlage eines GameRun mit Revision 1

Phase 4 — außerhalb dieses Vorhabens
persistierter StoryState + WorldState + Spieleraktion
    -> regulärer StoryTurn
```

Phase 1 erzeugt keinen GameRun, keinen GameState und keine Datenbankzeile.
Sie führt keine automatische Wiederholung durch. Ein Mensch kann die im
Live-Test ausgegebene Prosa prüfen und bei Bedarf einen neuen expliziten
Testlauf starten.

## Fachliches Modell

`StoryState` besitzt künftig eine verpflichtende `StoryInitialization`. Sie
enthält den ursprünglichen Initialprompt, die normalisierte Erzählung und den
Erzeugungszeitpunkt. Sie ist kein `StoryTurn`: Der erste reguläre Spielerzug
bleibt somit Zugnummer 1 und enthält weiterhin eine tatsächliche
Spielereingabe.

Vor der erfolgreichen Story-Initialisierung existiert kein StoryState. Ein
leerer Ersatzwert mit `initialization = None` wird nicht eingeführt, weil er
die fachliche Invariante verwässern würde.

## Spätere Gesamtorchestrierung

`StoryInitialization` wird erst mit Phase 2 als übergeordnete Application-
Operation eingeführt. Sie orchestriert sichtbar und testbar:

1. `GenerateInitialStoryState` erzeugt den transienten StoryState.
2. `ExtractInitialWorldState` erhält den StoryState als fachlichen Input und
   projiziert daraus Initialprompt und Erzählung für den Modellrequest.
3. Der spätere Initialisierungsworkflow gibt beide Werte gemeinsam zurück.

Der Extraction-Adapter erhält keinen Domainbaum. Die Application entscheidet,
welche vollständigen Werte aus der `StoryInitialization` für den konkreten
Request benötigt werden.

## Laufzeitverhalten

Die Modell- und Generierungsparameter werden für jeden Modellaufruf aus der
zentralen Laufzeitkonfiguration aufgelöst. Eine Änderung zwischen zwei Zügen
gilt daher für den nächsten Aufruf, während ein bereits begonnener Aufruf seine
zu Beginn aufgelöste Konfiguration behält.

Story-Initialisierung und reguläre Story Generation verwenden zunächst die
aktive Aufgabe `story`. Die Startkonfiguration ist `temperature = 0.5`.
`max_output_tokens` wird nicht gesetzt; die resultierende
`GenerationOptions.max_output_tokens` bleibt `None`.

## Nicht-Ziele von Phase 1

- keine initiale WorldState-Extraction;
- keine Persistenz oder HTTP-API;
- kein regulärer Spielerzug;
- keine automatische Qualitätsbewertung oder Wiederholung;
- kein Streaming, keine Summary und keine Providerverwaltung.

## Dokumentationsfolgen

Der autoritative Backlog in `docs/TODO.md` verfolgt die Stories und
Abhängigkeiten. Der verbindliche LLM-Architekturvertrag enthält die neue
Initialisierungsgrenze. Das maschinenorientierte Detaildesign und die
Subtasks stehen in
[`docs/llm/planned/story-initialization.md`](../../../llm/planned/story-initialization.md).
