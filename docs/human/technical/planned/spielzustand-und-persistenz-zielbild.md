# Technisches Zielbild: Spielzustand und Persistenz

Status: Entwurf zur Prüfung. Dieses Dokument beschreibt die beschlossene
Zielarchitektur. Der aktuelle Code und das aktuelle PostgreSQL-Schema weichen
davon noch ab.

## 1. Einordnung in die Schichten

```text
Domain
├── GameRun
├── GameRunMember
├── GameState
│   ├── GameConfiguration
│   ├── WorldState
│   │   └── Goal
│   └── StoryState
│       ├── StoryTurn
│       └── StorySummary
└── freigegebene State-Operationen

Application
├── Spielzug-Workflow
├── Prompt-Zusammensetzung
├── Modellaufruf
├── Extraktion
├── Validierung
├── ProposedChangeSet
└── Ports für Persistenz und Kataloge

Infrastructure
├── PostgreSQL- und JSON-Adapter
├── Keycloak-Adapter
├── LLM-Provider-Adapter
├── TOML-Modellkatalog
└── Datei-Promptkatalog
```

Die Domain kennt weder Datenbank, HTTP, Keycloak noch konkrete LLM-Anbieter.
Die Application organisiert den Ablauf. Die Infrastructure erfüllt die von
den inneren Schichten benötigten Ports.

## 2. Zielmodell der Domain

### GameRun

`GameRun` bildet eine Spielpartie oberhalb des revisionierten GameStates ab.

Vorgesehene Daten:

```text
GameRun
├── id: StableId
├── status: GameRunStatus
├── current_revision: StateRevision
├── members: tuple[GameRunMember, ...]
├── created_at
└── updated_at
```

`GameRunStatus` enthält zunächst:

```text
draft | active | paused | completed
```

Der GameRun-Kopf zeigt auf die zuletzt vollständig gespeicherte Revision. Er
enthält keinen laufenden Workflowstatus.

### GameRunMember

```text
GameRunMember
├── issuer: str
├── subject: str
├── game_role: GameRole
└── player_entity_id: StableId | None
```

`issuer` und `subject` bilden gemeinsam die stabile externe Identität aus dem
Keycloak-Token. Ein lokales Passwortfeld existiert nicht.

Die Verknüpfung `player_entity_id` muss auf eine als Akteur verwendbare
WorldEntity zeigen, sofern sie gesetzt ist.

### GameState

```text
GameState
├── run_id: StableId
├── revision: StateRevision
├── configuration: GameConfiguration
├── world: WorldState
└── story: StoryState
```

Die bisherige Vermischung von Run-ID und GameState-ID wird fachlich aufgelöst:
Der Run besitzt eine Folge unveränderlicher State-Revisionen.

### GameConfiguration

Die genaue technische Repräsentation darf typisiert auf mehrere Value Objects
aufgeteilt werden. Fachlich werden mindestens folgende Werte benötigt:

```text
GameConfiguration
├── language
├── narration_style_id
├── perspective_id
├── control_mode_id
├── narrative_boundaries
├── story_model_id
├── extraction_model_id
├── summary_model_id
├── prompt_package_id
└── prompt_package_version
```

Alle Katalogverweise sind semantische IDs. Zugangsdaten und Anbieterobjekte
sind keine Domainwerte.

### WorldState

Der bestehende WorldState mit Entitäten, Links, Fakten, Wissen und Regeln wird
um Goals erweitert:

```text
WorldState
├── entities
├── links
├── facts
├── knowledge
├── rules
└── goals
```

### Goal

```text
Goal
├── id: StableId
├── kind: GoalKind
├── title: str
├── description: str
├── status: GoalStatus
└── related_entity_ids: tuple[StableId, ...]
```

Enums:

```text
GoalKind   = main | side
GoalStatus = open | completed | failed
```

Alle `related_entity_ids` müssen auf vorhandene WorldEntities zeigen. Die
erste Umsetzung besitzt weder Prozentfortschritt noch Eltern-Kind-Beziehungen
zwischen Goals.

### StoryState

```text
StoryState
├── turns: tuple[StoryTurn, ...]
├── summary: StorySummary | None
└── current_turn_sequence: int
```

`current_turn_sequence` ist null oder positiv und entspricht bei vorhandenen
Turns der höchsten gespeicherten Sequenz. Der StoryState enthält keine Goals,
Scenes, Chapters oder StoryThreads.

### StoryTurn

```text
StoryTurn
├── id: StableId
├── sequence: StorySequence
├── player_input: str
├── narration: str
├── based_on_revision: StateRevision
├── resulting_revision: StateRevision
└── completed_at: datetime
```

Invarianten:

- `sequence` steigt innerhalb eines GameRuns streng monoton.
- `resulting_revision` folgt auf `based_on_revision`.
- Eingabe und Erzählung sind nicht leer.
- Ein StoryTurn ist nach dem Speichern unveränderlich.
- Ein Turn wird nur zusammen mit seiner resultierenden Revision sichtbar.

### StorySummary

Für den ersten Schritt genügt eine aktuelle rollierende Zusammenfassung:

```text
StorySummary
├── through_sequence: StorySequence
├── text: str
└── based_on_revision: StateRevision
```

Historische Zusammenfassungen müssen nicht als eigene Memory-Entitäten
verwaltet werden. Frühere GameState-Revisionen bewahren bei Bedarf ihren
damaligen Zusammenfassungsstand.

## 3. Änderungen gegenüber dem aktuellen Domainmodell

Der aktuelle Code besitzt `GameState` als Aggregatwurzel mit `WorldState` und
`StoryState`. Der StoryState enthält derzeit Events, Scenes, Chapters,
StoryThreads, Goals und mehrere Zusammenfassungen.

Für das Zielmodell sind folgende Änderungen vorgesehen:

| Aktuell | Ziel |
| --- | --- |
| `GameState.id` bezeichnet faktisch den Lauf | eigener `GameRun` mit revisionierten GameStates |
| keine GameConfiguration | GameConfiguration als Teil jeder Revision |
| `Goal` im StoryState | `Goal` ausschließlich im WorldState |
| Goal mit `progress` und optionalem Owner | Goal mit `kind`, Beschreibung und einfachem Status |
| `StoryEvent` als Chronologie | `StoryTurn` als abgeschlossener Spielzug |
| Scenes und Chapters | zunächst nicht Teil des Zielmodells |
| StoryThreads | zunächst nicht Teil des Zielmodells |
| mehrere StorySummary-Einträge | eine aktuelle rollierende Zusammenfassung |
| ProposedChangeSet in der Domain | transienter Application-Vertrag |

Freigegebene, revisionierte Domain-Operationen bleiben nötig. Das LLM liefert
weiterhin nur Vorschläge; es erhält keinen direkten Schreibzugriff auf den
GameState.

## 4. Application-Ablauf eines Spielzugs

Der Workflow bleibt explizit und besteht fachlich aus diesen Schritten:

```text
GameRun und aktuellen GameState laden
        ↓
Kataloge und GameConfiguration auflösen
        ↓
Kontext und Prompt zusammensetzen
        ↓
Story-Modell aufrufen
        ↓
Rohantwort in Erzählung und Vorschlagsdaten zerlegen
        ↓
strukturierte Änderungen extrahieren
        ↓
Vorschläge validieren und freigeben
        ↓
freigegebene Operationen auf GameState anwenden
        ↓
Zusammenfassung aktualisieren
        ↓
StoryTurn und neue GameState-Revision atomar speichern
```

Die genaue Aufteilung in Operationen soll dem verbindlichen
Architekturvertrag folgen: fachlich benannte Operationen mit `apply`, konkrete
Request- und Result-Typen sowie schmale Ports.

## 5. Transiente Application-Daten

Folgende Typen dürfen zur klaren Verarbeitung in der Application existieren,
werden aber nicht persistiert:

- zusammengesetzter Prompt;
- Model-Request und Model-Response;
- empfangene Rohantwort;
- Extraktionsergebnis;
- ProposedChangeSet;
- Validierungsergebnis;
- laufender Workflowstatus.

Ein `ApprovedChangeSet` oder eine entsprechende Sammlung freigegebener
Domain-Operationen ist ebenfalls ein Befehl für die Zustandsänderung und kein
eigener gespeicherter Zustand.

## 6. Transaktions- und Fehlergrenze

Der LLM-Aufruf darf nicht innerhalb einer Datenbanktransaktion stattfinden.

Vor dem Modellaufruf wird nur gelesen. Prompt-Aufbau, Modellaufruf, Extraktion
und Validierung geschehen im Arbeitsspeicher. Erst wenn StoryTurn und neuer
GameState vollständig vorliegen, startet die abschließende Transaktion.

Diese Transaktion muss:

1. den aktuellen GameRun-Kopf gegen `based_on_revision` prüfen;
2. die neue GameState-Revision schreiben;
3. den abgeschlossenen StoryTurn schreiben;
4. den GameRun-Kopf auf die neue Revision setzen;
5. vollständig zurückrollen, wenn einer dieser Schritte fehlschlägt.

Ein konkurrierender Zug auf derselben Basisrevision führt zu einem
RevisionConflict. Ein Absturz vor dem Commit hinterlässt keinen halbfertigen
Turn und keine neue Revision.

## 7. Ziel der PostgreSQL-Persistenz

Die physische Datenbank darf von der Verschachtelung des Domainmodells
abweichen, solange der Adapter dasselbe Modell korrekt rekonstruiert.

### Lauf und Mitgliedschaften

```text
game_runs
├── run_id
├── status
├── current_revision
├── created_at
└── updated_at

game_run_members
├── run_id
├── issuer
├── subject
├── game_role
└── player_entity_id
```

Die Kombination aus `run_id`, `issuer` und `subject` identifiziert eine
Mitgliedschaft eindeutig.

### Revisionen und Konfiguration

```text
game_state_revisions
├── run_id
├── revision
├── previous_revision
└── committed_at

game_state_configurations
├── run_id
├── revision
└── typisierte Konfigurationswerte
```

Die bestehende `story_state_commits`-Tabelle wird fachlich zu
`game_state_revisions`, weil die Revision den gesamten GameState und nicht nur
den StoryState beschreibt.

### WorldState

Die vorhandenen revisionierten Tabellen für WorldEntities, Links, Fakten,
Wissen und Regeln bleiben grundsätzlich passend. Ergänzt wird:

```text
world_goals
├── run_id
├── revision
├── goal_id
├── kind
├── title
├── description
├── status
└── related_entity_ids
```

Die bisherige Tabelle `story_goals` entfällt nach der Migration.

### StoryState und StoryTurns

```text
story_state_metadata
├── run_id
├── revision
├── current_turn_sequence
├── summary_through_sequence
├── summary_text
└── summary_based_on_revision

story_turns
├── turn_id
├── run_id
├── sequence
├── player_input
├── narration
├── based_on_revision
├── resulting_revision
└── completed_at
```

Jeder StoryTurn wird genau einmal gespeichert. Beim Laden einer historischen
Revision berücksichtigt der Adapter nur Turns, deren `resulting_revision`
höchstens der angeforderten Revision entspricht.

Die bisherigen Tabellen für Events, Scenes, SceneParticipants, Chapters,
StoryThreads, StoryGoals und die Liste von StorySummaries gehören nicht zum
Zielschema.

### Bewusst nicht vorhandene Tabellen

Es werden keine Tabellen angelegt für:

- Workflowstatus;
- Modellaufrufe;
- Rohantworten;
- Extraktionsläufe;
- MemorySnapshots;
- ProposedChangeSets;
- Validierungsergebnisse.

## 8. Datei- und Katalogadapter

Die Application besitzt schmale Ports, beispielsweise:

```text
ModelCatalog
PromptCatalog
ModelInvoker
GameRunReader
GameStateReader
CompletedTurnWriter
```

Die Infrastructure stellt zunächst bereit:

- TOML-Adapter für Provider, Modelle und Defaults;
- einen Prompt-Katalog aus TOML-Metadaten und Textdateien;
- JSON-Schemas für strukturierte Modellantworten;
- konkrete Modellanbieter-Adapter;
- PostgreSQL- und lokale JSON-Persistenzadapter.

Eine spätere Datenbankimplementierung von `ModelCatalog` oder `PromptCatalog`
ändert weder Use Cases noch Domain.

## 9. Konfigurationsdateien

Vorgesehene Richtung:

```text
config/
├── providers.toml
├── models.toml
└── defaults.toml

prompts/
├── catalog.toml
├── story/
├── styles/
├── perspectives/
├── summary/
├── extraction/
└── repair/

schemas/
└── model-output/*.json
```

Statische IDs sind lesbar und stabil. UUIDs werden nur für dynamische
Laufzeitdaten wie GameRuns und StoryTurns verwendet. Secrets stehen nicht in
diesen Dateien.

## 10. Umsetzungsschritte

Die spätere Implementierung sollte in fachlich prüfbaren Schritten erfolgen:

1. Ziel-Domainmodell für GameRun, GameConfiguration, Goal und StoryTurn durch
   Tests festlegen.
2. StoryState vereinfachen und Goal in WorldState verschieben.
3. Persistenzschema und Mapper auf das neue Domainmodell migrieren.
4. GameRun-Mitgliedschaften und Keycloak-Identitätsreferenzen ergänzen.
5. Datei-basierte Modell- und Prompt-Kataloge hinter Application-Ports
   einführen.
6. den vollständigen transienten Spielzug-Workflow implementieren.
7. gemeinsam verifizieren, dass ein Turn nur vollständig oder gar nicht
   gespeichert wird.

Die genaue Zerlegung wird erst nach Prüfung dieser Zielbeschreibung geplant.
Die hier festgelegten fachlichen Zuordnungen gelten dabei nicht als offene
Fragen.

## 11. Abnahmekriterien des Zielbilds

Das Ziel ist erreicht, wenn:

- Goals ausschließlich über WorldState geladen und verändert werden;
- StoryState nur StoryTurns, aktuelle Zusammenfassung und Zugnummer enthält;
- jeder abgeschlossene Zug genau einen StoryTurn und genau eine neue Revision
  erzeugt;
- ein Fehler vor dem Abschluss weder Turn noch Revision hinterlässt;
- ein RevisionConflict konkurrierende Änderungen sichtbar ablehnt;
- GameRuns Keycloak-Mitglieder besitzen können;
- ein gespeichertes Spiel seine GameConfiguration behält;
- Use Cases Datei- und spätere Datenbankkataloge über denselben Port verwenden;
- keine transiente LLM-Verarbeitung in der Datenbank benötigt wird.
