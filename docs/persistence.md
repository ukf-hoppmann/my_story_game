# Persistenz

Die Persistenz behandelt den `GameState` als kanonischen Zustand. Ein Modell
darf diesen Zustand nicht direkt schreiben. Es erzeugt Prosa und geprüfte
Änderungsvorschläge; erst eine Anwendungskomponente baut daraus einen
`ApprovedChangeSet`, den die Domain mit einer erwarteten `StateRevision`
anwendet.

## Kleine Ports und Operationen statt einer God-Klasse

Die Anwendung kennt schmale, fachlich benannte Ports:

- `GameStateReader.load(run_id, revision)` lädt einen validierten Zustand.
- `GameStateWriter.create_initial(state)` legt den initialen Zustand an.
- `GameStateWriter.commit(run_id, changes)` wendet einen geprüften
  Änderungssatz atomar auf die erwartete Revision an.
- `GameStateDocumentCodec` übersetzt das versionierte Zustandsdokument, ohne
  den HTTP-Adapter an die konkrete JSON-Implementierung zu koppeln.

Darauf aufbauend führen `CreateInitialGameState`, `LoadGameState` und
`CommitGameStateChanges` jeweils genau einen Anwendungsfall aus. Sie liefern
ein typisiertes `Success`- oder `Failure`-Ergebnis. Die API setzt diese
Operationen zusammen und übersetzt die Fehler erst an ihrer HTTP-Grenze.

Die JSON-Implementierung besteht aus getrennten Komponenten:

- `JsonStateReader` liest und validiert ein versioniertes Snapshot-Dokument.
- `JsonStateWriter` schreibt einen Snapshot über eine temporäre Datei und
  `os.replace`, damit kein halbes JSON als Zustand sichtbar wird.
- `mapper.py` übersetzt ausschließlich zwischen JSON und Domainobjekten.
- `JsonGameStateStore` verbindet Reader, Writer und den Domain-Apply-Schritt.

Der JSON-Adapter ist ein Mockup für lokale Entwicklung und Tests. Er speichert
nur die aktuelle Revision und keine Historie. Die Beispieldaten in
`tests/fixtures/` enthalten bereits verschachtelte Item-Beziehungen:
`mara-backpack` besitzt den Rucksack und `backpack-sword` enthält das Schwert.

## PostgreSQL-Adapter

PostgreSQL ist als separater Adapter umgesetzt. Die Datenbank speichert nicht
eine unstrukturierte God-JSON-Spalte, sondern getrennte fachliche Tabellen für
Lauf, Revisionen, Entitäten, Beziehungen, Fakten, Wissen und Storydaten. Ein
Commit erhält die erwartete Revision, sperrt den Laufkopf innerhalb einer
Transaktion, schreibt die neue Revision und aktualisiert den Kopf nur bei
erfolgreicher Domainvalidierung. Ein veralteter Kopf führt zu einem
Concurrency-Konflikt.

LLM-Prozessdaten wie Modelllauf, Prosa, Vorschlag, Prüfung und Turn-Historie
bleiben getrennt vom kanonischen Zustand. Dadurch kann die Anwendung jeden
Vorschlag ablehnen, ohne den `GameState` zu verändern.

## Lokale PostgreSQL-Umgebung

Die Entwicklungsdatenbank wird über `compose.yaml` gestartet. Der Host-Port
ist standardmäßig `5433`, damit ein lokaler Standard-PostgreSQL auf `5432`
nicht kollidiert:

```bash
docker compose up --detach --wait postgres
```

Danach wird das versionierte Schema einmalig beziehungsweise idempotent
aktualisiert:

```bash
export STORY_GAME_POSTGRES_DSN=postgresql://story_game:story_game_dev@localhost:5433/story_game
PYTHONPATH=src python -m story_game.infrastructure.persistence.postgres.migrate
```

Die Integrationstests verwenden denselben DSN, wenn
`STORY_GAME_POSTGRES_DSN` gesetzt ist. Ohne DSN bleiben sie bewusst als
Umgebungstest übersprungen; die JSON-Tests benötigen keinen Dienst.

Die Compose-Volume `story-game-postgres-data` ist eine lokale
Entwicklungsressource. Sie enthält persistente Daten und wird nicht von den
isolierten Standardtests verwaltet.
