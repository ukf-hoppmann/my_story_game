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
  - Status: Open.
  - Created: 2026-08-04.
  - Area: Domainmodell, Persistenz und API.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Das aus `LLM_Tests` abgeleitete Datenmodell für ein Storygame in einer Onion Architecture neu implementieren. Die Umsetzung erfolgt schrittweise: zuerst fachliche Domain-Entities, danach Datenbankanbindung und anschließend API.
  - Completion criteria: Die zentralen Storygame-Daten können über fachliche Domain-Entities modelliert, anschließend dauerhaft gespeichert und schließlich über eine API erstellt, gelesen und verändert werden. Kanonische Zustandsänderungen werden ausschließlich über geprüfte Anwendungslogik übernommen; das LLM erhält keinen direkten Schreibzugriff auf den GameState.

- `STORY-001` **Fachliche Domain-Entities für den Storygame-Zustand**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Einen technologieunabhängigen Domain-Kern für den Storygame-Zustand in der innersten Schicht der Onion Architecture definieren. Der Kern bildet stabile Entitäten, Beziehungen und bestätigte Fakten ab, ohne LLM-, API- oder Persistenzabhängigkeiten.
  - Completion criteria: Figuren, Orte, Gegenstände, Beziehungen, Fakten und der aggregierte GameState besitzen stabile Identitäten und fachliche Invarianten. Beziehungen referenzieren nur gültige Entitäten; Sichtbarkeit und Evidenz bestätigter Fakten sind modellierbar; automatisierte Domain-Tests prüfen die wesentlichen Regeln.

- `TASK-001` **Domain-Grundtypen und Aggregatgrenzen festlegen**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Die technologieunabhängigen Grundtypen für stabile Identitäten, State-Revisionen, Sichtbarkeit, Evidenz und fachliche Statuswerte definieren sowie `GameState` als Aggregatwurzel mit getrenntem `WorldState` und `StoryState` festlegen.
  - Completion criteria: Die Aggregatgrenzen und Verantwortlichkeiten sind dokumentiert und im Domain-Code abbildbar. Ungültige IDs, Revisionen und Sichtbarkeitswerte werden fachlich abgewiesen. Die Domain-Schicht importiert weder Datenbank-, API- noch LLM-spezifische Typen.

- `TASK-002` **WorldState mit Entitäten und kanonischen Beziehungen modellieren**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-001`.
  - Goal: Figuren, Orte, Gegenstände, Kreaturen und Fraktionen über stabile World-Entities modellieren und deren kanonische Beziehungen, Fakten, akteursbezogenes Wissen und Weltregeln abbilden.
  - Completion criteria: Entitäten besitzen eindeutige IDs und typisierte Profile. Beziehungen wie Aufenthaltsort, Besitz, Behälter, Zugehörigkeit und soziale Verbindung referenzieren nur vorhandene Entitäten. Fakten enthalten Evidenz und Sichtbarkeit; Wissen ist einem gültigen Akteur und Fakt zugeordnet. Inventar wird aus Besitzbeziehungen abgeleitet und nicht als widersprüchliche Parallelstruktur geführt.

- `TASK-003` **StoryState mit Chronologie und Handlungsfortschritt modellieren**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-002`.
  - Goal: Den zeitlichen und dramaturgischen Zustand der Geschichte mit Ereignissen, Szenen, Kapiteln, offenen Threads, Zielen, Story-Zeit und Zusammenfassungen modellieren.
  - Completion criteria: Ereignisse sind chronologisch und grundsätzlich unveränderlich. Eine Szene kann nur auf vorhandene Orte und tatsächlich zugeordnete Entitäten verweisen. Kapitel, Threads und Ziele besitzen nachvollziehbare Zustände; Zusammenfassungen bleiben als abgeleitete Erinnerung von den kanonischen World-Fakten getrennt.

- `TASK-004` **Vorschlags- und Freigabegrenze für Zustandsänderungen definieren**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-002`, `TASK-003`.
  - Goal: Einen fachlichen Änderungsvertrag für vorgeschlagene und geprüfte Zustandsänderungen definieren, der den LLM-Ausgabepfad vom kanonischen GameState trennt.
  - Completion criteria: Ein Vorschlag enthält mindestens Basisrevision, Zielbereich, typisierte Operation, Zielreferenz, Evidenz und Status. Rohdaten oder Prosa können den GameState nicht direkt verändern. Nur ein von der Anwendung freigegebener Änderungssatz kann fachlich angewendet werden; veraltete Revisionen, ungültige Referenzen und geschützte Fakten werden abgewiesen.

- `TASK-005` **Domain-Invarianten und Storygame-Beispielfälle testen**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-004`.
  - Goal: Die fachlichen Regeln des Domain-Kerns mit deterministischen Tests absichern und anhand eines kleinen Storygame-Szenarios den konsistenten Aufbau des GameState prüfen.
  - Completion criteria: Tests decken stabile IDs, Referenzkonsistenz, Sichtbarkeit, Wissen, Besitz, Chronologie, Szenenbesetzung, Revisionskonflikte und die Ablehnung ungeprüfter LLM-Änderungen ab. Ein Beispielablauf kann eine Figur, einen Ort, einen Gegenstand, eine Besitzänderung, ein Ereignis und einen neuen State-Stand konsistent darstellen.

- `STORY-002` **Datenbankanbindung für den Storygame-Zustand**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Persistenz.
  - Priority: Wichtig.
  - Dependencies: `STORY-001`.
  - Goal: Die fachlichen Domain-Entities dauerhaft und nachvollziehbar speichern, ohne die Domain-Schicht an ein konkretes Datenbanksystem zu koppeln. Der persistierte Stand soll rekonstruierbar und für spätere geprüfte Zustandsänderungen geeignet sein.
  - Completion criteria: Ein GameState kann über einen Persistenzadapter angelegt, geladen und aktualisiert werden. Entitäten, Beziehungen und Fakten bleiben referenziell konsistent; relevante Zustandsstände sind versionierbar oder anderweitig nachvollziehbar; Persistenzfehler führen nicht zu halb gespeicherten Zuständen; Integrations- und Domain-Tests decken den Ablauf ab.

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
