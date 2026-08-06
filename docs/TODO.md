# Project Backlog

This file is the authoritative record of concrete project work that has been
intentionally deferred, is being implemented, or awaits an explicit
project-owner decision.

It uses backlog format version 2. Every work item stores its own type, lifecycle
status, and relationships. Position and ordering in this document do not
determine status or hierarchy.

## Status model

- `Open`: Accepted backlog work that has not started.
- `In progress`: Work whose implementation or investigation has begun.
- `Awaiting confirmation`: Implementation and verification are complete, but
  project-owner confirmation is still pending.
- `Completed`: Explicitly confirmed as complete by the project owner.
- `Rejected`: Explicitly rejected by the project owner.

Passing tests, commits, merges, silence, and agent assessment do not constitute
completion confirmation.

## Work-item types

- `Epic`: A larger outcome containing multiple independently verifiable
  results.
- `Story`: An independently deliverable and observable result for a user,
  operator, or consuming system.
- `Task`: Supporting work that does not by itself deliver an independent
  stakeholder-visible result.

An epic has no parent. A story may belong to one epic. A task may belong to one
story or directly to one epic when it enables multiple stories. Stories and
tasks may also be standalone.

`Parent` records outcome membership. `Dependencies` record prerequisites or
execution ordering. These relationships are independent.

## Required fields

Every entry contains `Type`, `Status`, `Created`, `Area`, `Priority`,
`Dependencies`, `Goal`, and `Completion criteria`.

A story or task additionally contains `Parent`. A parented story or task
contains `Required for parent`.

A completed or rejected entry contains `Resolution`, recording the explicit
project-owner decision. Missing historical evidence remains visible and is
never invented.

Default priorities are `Dringend`, `Wichtig`, and `Perspektivisch`. Project
rules may define different priorities and areas.

## Entry templates

### Epic

```markdown
- `EPIC-NNN` **Concise epic title**
  - Type: Epic.
  - Status: Open.
  - Created: YYYY-MM-DD.
  - Area: Project area.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Describe the complete outcome delivered by the epic.
  - Completion criteria: State the integration-level, verifiable conditions
    required to finish the epic.
```

### Story belonging to an epic

```markdown
- `STORY-NNN` **Concise story title**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-NNN`.
  - Required for parent: Yes.
  - Created: YYYY-MM-DD.
  - Area: Project area.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Describe the independently deliverable and observable result.
  - Completion criteria: State how the result is verified through its
    supported workflow.
```

### Task belonging to a story or epic

```markdown
- `TASK-NNN` **Concise task title**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-NNN`.
  - Required for parent: Yes.
  - Created: YYYY-MM-DD.
  - Area: Project area.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Describe the supporting work outcome.
  - Completion criteria: State the verifiable conditions required to finish
    this task.
```

### Standalone story or task

```markdown
- `STORY-NNN` **Concise standalone title**
  - Type: Story.
  - Status: Open.
  - Parent: None.
  - Created: YYYY-MM-DD.
  - Area: Project area.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Describe the independently understandable outcome.
  - Completion criteria: State the verifiable conditions required to finish
    this item.
```

### Resolution field

After explicit project-owner confirmation:

```markdown
  - Resolution: Confirmed by the project owner on YYYY-MM-DD.
```

After explicit rejection:

```markdown
  - Resolution: Rejected by the project owner on YYYY-MM-DD — concise reason.
```

## Work items

- `TASK-006` **Komponierbare Operationsarchitektur verbindlich einführen**
  - Type: Task.
  - Status: Completed.
  - Parent: None.
  - Created: 2026-08-05.
  - Area: Anwendungsarchitektur.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Die bestehende GameState-Anwendung verhaltensgleich auf kleine typisierte Operationen, anwendungseigene Ports und explizite Verdrahtung migrieren und diese Struktur anschließend als verbindlichen Architekturvertrag festhalten.
  - Completion criteria: Die frühere GameState-Service-Fassade enthält keine Anwendungslogik mehr; Erstellen, Laden und Committen sind unabhängig testbare Operationen mit `Success`- und `Failure`-Ergebnissen; Domain und Anwendung hängen nicht von API oder Infrastruktur ab; Architekturtests sichern die Grenzen; eine verständliche deutsche Erklärung und die verbindliche Regelquelle sind vorhanden; die vollständige isolierte Prüfung mit PostgreSQL besteht.
  - Resolution: Confirmed by the project owner on 2026-08-05.

- `EPIC-001` **Storygame-Datenmodell neu implementieren**
  - Type: Epic.
  - Status: In progress.
  - Created: 2026-08-04.
  - Area: Domainmodell, Persistenz und API.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Das beschlossene Datenmodell für ein Storygame in einer Onion Architecture umsetzen. Die Umsetzung erfolgt schrittweise: zuerst fachliche Domain-Entities, danach Datenbankanbindung und anschließend die produktive API.
  - Completion criteria: Die zentralen Storygame-Daten können über fachliche Domain-Entities modelliert, anschließend dauerhaft gespeichert und schließlich über eine API erstellt, gelesen und verändert werden. Kanonische Zustandsänderungen werden ausschließlich über geprüfte Anwendungslogik übernommen; das LLM erhält keinen direkten Schreibzugriff auf den GameState.

- `STORY-001` **Fachliche Domain-Entities für den Storygame-Zustand**
  - Type: Story.
  - Status: Awaiting confirmation.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Einen technologieunabhängigen Domain-Kern aus `GameRun` und revisioniertem `GameState` definieren. Der GameState trennt die partielle Konfiguration, die strukturierte Welt einschließlich Goals und die konkrete Turn-Chronologie, ohne LLM-, API- oder Persistenzabhängigkeiten.
  - Completion criteria: GameRun, Mitgliedschaften, GameConfiguration, WorldState, Goals, StoryTurns und StorySummary besitzen verständliche Verantwortlichkeiten und fachliche Invarianten. Goals liegen ausschließlich im WorldState; der StoryState enthält nur abgeschlossene Turns, aktuelle Zusammenfassung und Zugnummer; automatisierte Domain- und Architekturtests sichern die Regeln.

- `TASK-001` **Domain-Grundtypen und Aggregatgrenzen festlegen**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Die technologieunabhängigen Grundtypen und die Grenze zwischen `GameRun` und revisioniertem `GameState` mit `GameConfiguration`, `WorldState` und `StoryState` festlegen.
  - Completion criteria: IDs, Revisionen, Run-Status, Mitgliedsrollen, Sichtbarkeit und Evidenz sind typisiert und validiert. Die Verantwortlichkeiten sind dokumentiert; die Domain importiert keine Datenbank-, API- oder LLM-spezifischen Typen.

- `TASK-002` **WorldState mit Entitäten und kanonischen Beziehungen modellieren**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-001`.
  - Goal: Figuren, Orte, Gegenstände, Kreaturen und Fraktionen sowie ihre Beziehungen, Fakten, Wissen, Weltregeln und Haupt- beziehungsweise Nebenziele im WorldState abbilden.
  - Completion criteria: Entitäten und Goal-Referenzen sind konsistent. Beziehungen wie Aufenthaltsort, Besitz, Behälter, Zugehörigkeit und soziale Verbindung referenzieren nur vorhandene Entitäten. Goals unterscheiden `main` und `side` sowie `open`, `completed` und `failed`; Inventar wird aus Besitzbeziehungen abgeleitet.

- `TASK-003` **StoryState als konkrete Turn-Chronologie modellieren**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-002`.
  - Goal: Die konkrete Geschichte als Folge vollständig abgeschlossener StoryTurns mit einer aktuellen rollierenden Zusammenfassung und Zugnummer modellieren.
  - Completion criteria: StoryTurns enthalten `player_input`, Erzählung, Sequenz, Basis- und Ergebnisrevision sowie Abschlusszeitpunkt. Sequenzen sind lückenlos; Goals, Chapters, Scenes, StoryThreads und ein zusätzliches StoryEvent sind nicht Teil des StoryState.

- `TASK-004` **Vorschlags- und Freigabegrenze für Zustandsänderungen definieren**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-002`, `TASK-003`.
  - Goal: Unbestätigte LLM-Vorschläge als transiente Application-Daten von freigegebenen Domain-Operationen und dem kanonischen GameState trennen.
  - Completion criteria: `ProposedChangeSet` liegt ausschließlich in der Application und wird nicht persistiert. Rohdaten oder Prosa können den GameState nicht direkt verändern. Nur ein `ApprovedChangeSet` kann auf der erwarteten Revision angewendet werden; veraltete Revisionen und ungültige Referenzen werden abgewiesen.

- `TASK-005` **Domain-Invarianten und Storygame-Beispielfälle testen**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-004`.
  - Goal: Die fachlichen Regeln des Domain-Kerns deterministisch absichern und anhand eines kleinen zielorientierten Storygame-Szenarios prüfen.
  - Completion criteria: Tests decken IDs, Mitgliedschaften, Referenzkonsistenz, Sichtbarkeit, Wissen, Besitz, Goals, Turn-Chronologie und Revisionskonflikte ab. Das Beispiel kann Almas, ein Hauptziel und einen abgeschlossenen Turn konsistent in den nächsten GameState überführen.

- `STORY-002` **Datenbankanbindung für den Storygame-Zustand**
  - Type: Story.
  - Status: Awaiting confirmation.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Persistenz.
  - Priority: Wichtig.
  - Dependencies: `STORY-001`.
  - Goal: GameRun und revisionierten GameState über einen PostgreSQL-Adapter dauerhaft speichern, ohne die Domain an PostgreSQL zu koppeln.
  - Completion criteria: Ein vollständiger neuer Lauf sowie aktuelle und historische Revisionen können gespeichert und geladen werden. GameConfiguration, WorldState einschließlich Goals und StoryState werden rekonstruiert. Konfigurationsrevisionen benötigen keinen Turn; ein abgeschlossener Turn und seine Ergebnisrevision werden atomar gespeichert. Das alte JSON- und Story-Tabellenmodell ist entfernt; PostgreSQL-Integrationstests bestehen.

- `STORY-003` **API für den Storygame-Zustand**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: API.
  - Priority: Wichtig.
  - Dependencies: `STORY-002`.
  - Goal: Den Storygame-Zustand über eine stabile API für die späteren Benutzeroberflächen und Anwendungsfälle zugänglich machen. Die API trennt Lesen, fachliche Änderungsanträge und deren geprüfte Übernahme.
  - Completion criteria: Ein Client kann einen Storygame-Zustand anlegen, laden und fachlich valide Änderungen anfordern. Die API gibt keine direkten LLM-Schreibrechte frei, validiert Referenzen und Zustandsrevisionen und liefert verständliche Fehler bei ungültigen oder veralteten Änderungen. API- und Integrations-Tests prüfen die unterstützten Abläufe.

- `STORY-004` **LLM-, Prompt- und Modellkonfigurationsschicht integrieren**
  - Type: Story.
  - Status: Open.
  - Parent: None.
  - Created: 2026-08-06.
  - Area: LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `STORY-001`, `STORY-002`.
  - Goal: Einen vollständigen Spielzug aus dateibasierten Modell- und Promptkatalogen, tatsächlichen Modellaufrufen, transienter Narrative- und WorldState-Extraktion, fachlicher Freigabe und atomarem Turn-Commit zusammensetzen.
  - Completion criteria: TOML-basierte globale Konfiguration und versionierte Promptdateien werden hinter Application-eigenen Ports geladen; Provider-Geheimnisse bleiben außerhalb der Domain und des Repository-Katalogs; der Workflow setzt die GameConfiguration in konkrete Aufrufe um, validiert unbestätigte Vorschläge und persistiert ausschließlich den abgeschlossenen StoryTurn mit der resultierenden GameState-Revision. Modellaufrufe, Rohantworten, ProposedChangeSets und Validierungsergebnisse bleiben transient und besitzen keine eigenen Tabellen.
