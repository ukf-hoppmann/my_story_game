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
  - Completion criteria: IDs, Revisionen, Run-Status, Mitgliedsrollen und Sichtbarkeit sind typisiert und validiert. Evidenz gehört ausschließlich zu transienten Application-Vorschlägen und nicht zu kanonischen Facts oder WorldRules. Die Verantwortlichkeiten sind dokumentiert; die Domain importiert keine Datenbank-, API- oder LLM-spezifischen Typen.

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

- `EPIC-002` **LLM-Anbindung und Storyzug-Workflow**
  - Type: Epic.
  - Status: Open.
  - Created: 2026-08-07.
  - Area: LLM-Integration und Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `EPIC-001`.
  - Goal: Einen vollständigen, providerunabhängigen Storyzug aus Modell- und Promptkatalogen, tatsächlichen Modellaufrufen, Story-Erzeugung, WorldState-Extraktion, fachlicher Freigabe und atomarem Turn-Commit zusammensetzen.
  - Completion criteria: Die sieben zugehörigen Stories sind umgesetzt und integriert. Ein vollständiger Storyzug kann zuerst aus einem Initialprompt einen StoryState und danach einen WorldState bilden, den initialen GameState atomar anlegen, den relevanten fortlaufenden GameState-Kontext verwenden, normalisierte Story-Prosa erzeugen, strukturierte Extraktionsvorschläge fachlich prüfen und ausschließlich einen abgeschlossenen StoryTurn mit der resultierenden GameState-Revision persistieren. Modellaufrufe, Rohantworten, ProposedChangeSets und Validierungsergebnisse bleiben transient.

- `STORY-004` **Anbindungsverträge definieren**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-06.
  - Area: LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Die providerunabhängigen, typisierten Verträge für Story-Erzeugung, Extraktion und Modellaufrufe als Application-eigene Ports festlegen.
  - Completion criteria: Task-spezifische Requests und Success-Daten, eine geeignete typisierte Generation-Call-Hülle sowie die gemeinsame `Success`-/`Failure`- und `LLMError`-Grenze sind dokumentiert, implementiert und unabhängig testbar. Providerobjekte, Rohantworten und konkrete Providerformate überschreiten die Application-Grenze nicht.

- `STORY-005` **LLM anbinden**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-07.
  - Area: LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `STORY-004`, `STORY-001`, `STORY-002`.
  - Goal: Die vereinbarten Modellverträge mit dateibasierten Modell- und Promptkatalogen sowie einem austauschbaren Provider-Adapter und Provider-Client ausführbar verbinden.
  - Completion criteria: TOML-basierte globale Konfiguration und versionierte Promptdateien werden über Application-Ports geladen. Provider-Geheimnisse kommen aus einer zugelassenen externen Laufzeitquelle. Ein tatsächlicher Modellaufruf kann über einen Testdouble und den vorgesehenen Providerpfad ausgeführt werden; Rohantworten und Providerfehler bleiben transient beziehungsweise werden in die Application-eigene Fehlerfamilie übersetzt.

- `STORY-006` **Story Generation erstellen**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-07.
  - Area: Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `STORY-005`, `STORY-010`.
  - Goal: Aus GameConfiguration, relevantem WorldState, StoryState und aktuellem Spielerprompt eine fachlich definierte Story-Generation-Anfrage zusammensetzen und daraus normalisierte Story-Prosa erzeugen.
  - Completion criteria: Der Workflow wählt und strukturiert den Kontext in der Application, ruft den Story-Port auf und liefert bei Erfolg nichtleere, valide Prosa. Adapter wählen keine Spieldaten aus und verändern keinen kanonischen GameState. Provider-, Timeout-, Leer- und Fehlerszenarien sind über beobachtbares Workflowverhalten getestet.

- `STORY-007` **Extraktion erstellen**
  - Type: Story.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-07.
  - Area: WorldState-Extraktion und Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `STORY-006`, `STORY-001`, `STORY-002`.
  - Goal: Aus der erzeugten Story-Prosa strukturierte WorldState-Änderungskandidaten extrahieren, fachlich validieren und gemeinsam mit dem abgeschlossenen StoryTurn atomar übernehmen.
  - Completion criteria: Technisch valide Extraktionsdaten werden in typisierte, noch nicht freigegebene Kandidaten überführt. Referenzen, Domain-Invarianten, Revisionen und fachliche Plausibilität werden geprüft; unbestätigte oder teilweise fehlerhafte Ergebnisse schreiben keinen kanonischen Zustand. Nur ein vollständiger, freigegebener Turn persistiert den StoryTurn und die resultierende GameState-Revision gemeinsam.

- `STORY-008` **Initialen StoryState erzeugen**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: Story-Initialisierung.
  - Priority: Wichtig.
  - Dependencies: `STORY-005`.
  - Goal: Aus GameConfiguration, einem anfänglichen freien Userprompt und dem im Player Mode vom User angelegten Charakter eine normalisierte Eröffnungsprosa und daraus einen vollständigen transienten StoryState erzeugen, bevor ein WorldState existiert.
  - Completion criteria: `StoryInitialization` trennt Initialprompt von regulären Spielerzügen; Player Mode verlangt genau einen PlayerCharacterSeed und Director Mode verbietet ihn; First und Second Person sind im Director Mode ungültig; ungültige Kombinationen scheitern vor dem Modellaufruf; ein eigener typisierter Modellport erhält keine WorldState- oder StoryState-Eingabe; die Application liefert einen vollständigen StoryState ohne Turns und ohne Persistenz; ein explizit aktivierter LM-Studio-Live-Test verwendet den erforderlichen Charakter, prüft den StoryState und gibt Request und Ergebnis als JSON aus; technische Modellfehler bleiben sichtbare typed Failures.
  - Resolution: Implemented and verified on 2026-08-10.

- `TASK-007` **Spielercharakter und Control-Policy in STORY-008 ergänzen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-008`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: Story-Initialisierung und Promptprojektion.
  - Priority: Wichtig.
  - Dependencies: `STORY-005`.
  - Goal: Den bestehenden Story-Init um einen User-definierten PlayerCharacterSeed, gültige Perspective-/Control-Kombinationen und die klare Director-Semantik erweitern.
  - Completion criteria: Player-Aufrufe enthalten genau einen vertrauenswürdigen Charakter; Director-Aufrufe enthalten weder Charakter noch Player-Agency-Anweisung; First und Second Person mit Director sowie fehlende oder unerwartete Seeds werden vor jedem Modellaufruf abgewiesen; Prompt-, Application-, Adapter- und Live-Test-Inputs sind angepasst.
  - Resolution: Implemented and verified on 2026-08-10.

- `STORY-009` **Initialen WorldState extrahieren**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: WorldState-Initialisierung.
  - Priority: Wichtig.
  - Dependencies: `STORY-008`, `STORY-005`.
  - Goal: Aus der Eröffnungsprosa, den erforderlichen Modusdaten und dem im Player Mode vorhandenen vertrauenswürdigen Spielercharakter einen transienten, fachlich validierten WorldState bilden, ohne einen GameRun oder GameState teilweise zu persistieren.
  - Completion criteria: Ein eigener Initial-Extraction-Port erhält weder ursprünglichen Initialprompt noch Storyprofil oder vorhandenen WorldState; sein strukturiertes Schema enthält nur Entitäten, Beziehungen und Fakten mit lokalen Referenzen; das Modell erzeugt keine Spielerfigur, StableIds, Sichtbarkeit, Evidenz, KnowledgeEntries, WorldRules oder Goals; die Application erzeugt im Player Mode die Spielerfigur sowie in allen Modi StableIds und neutrale weitere Charaktere, validiert alle Referenzen und Domain-Invarianten und übernimmt nur einen vollständigen WorldState; Provider-, Schema-, Referenz- oder Domainfehler erzeugen keinen Teilzustand und keinen Retry. Eine übergeordnete Operation liefert StoryState und WorldState gemeinsam, persistiert aber nichts; der Live-Test gibt beide Requests und Ergebnisse aus.
  - Resolution: Implemented and verified on 2026-08-10.

- `TASK-008` **Kanonische Evidenz entfernen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-009`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: Domainmodell, API und Persistenz.
  - Priority: Wichtig.
  - Dependencies: `STORY-001`, `STORY-002`.
  - Goal: Evidenz aus kanonischen Facts und WorldRules sowie ihren API- und PostgreSQL-Repräsentationen entfernen und ausschließlich als transiente Application-Reviewinformation beibehalten.
  - Completion criteria: Domain, API und PostgreSQL können Facts und Rules ohne Evidence round-trip verarbeiten; die Initialmigration enthält keine Evidence-Spalten und bestehende Entwicklungsdatenbanken müssen ohne Rückwärtskompatibilität neu angelegt werden; ProposedChange kann weiterhin transiente Review-Evidenz tragen; Visibility, Knowledge, Rules und Goals bleiben ansonsten unverändert.
  - Resolution: Implemented and verified on 2026-08-10.

- `TASK-009` **Initial-Extraction-Port und JSON-Schema anbinden**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-009`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: LLM-Verträge und LM-Studio-Adapter.
  - Priority: Wichtig.
  - Dependencies: `TASK-007`, `STORY-005`.
  - Goal: Einen providerneutralen Initial-Extraction-Vertrag und einen LM-Studio-Structured-Output-Pfad für Entitäten, Beziehungen und Fakten implementieren.
  - Completion criteria: Der technische Request übermittelt das geschlossene JSON-Schema; der Adapter liefert ausschließlich typisierte Candidates oder sichtbare LLMErrors; unbekannte Felder, falsche Typen, ungültige Enums, Text statt JSON, leere oder abgeschnittene Antworten und Providerfehler sind getestet; Rohantworten überschreiten die Adaptergrenze nicht.
  - Resolution: Implemented and verified on 2026-08-10.

- `TASK-010` **Initial-Candidate in WorldState überführen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-009`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: WorldState-Initialisierung.
  - Priority: Wichtig.
  - Dependencies: `TASK-008`, `TASK-009`.
  - Goal: Lokale Candidate-Referenzen und den vertrauenswürdigen PlayerCharacterSeed all-or-nothing in einen vollständigen transienten WorldState überführen.
  - Completion criteria: Die Application erzeugt StableIds und im Player Mode die einzige PLAYER-Entität; Modellcharaktere sind optional und neutral; reservierte, doppelte oder unbekannte Referenzen sowie Domainfehler verwerfen den gesamten Candidate; Visibility nutzt nur den technischen Public-Default und Knowledge, Rules und Goals bleiben leer.
  - Resolution: Implemented and verified on 2026-08-10.

- `TASK-011` **Zweistufige Initialisierung orchestrieren**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-009`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: Application-Orchestrierung.
  - Priority: Wichtig.
  - Dependencies: `TASK-007`, `TASK-010`.
  - Goal: StoryState-Erzeugung und initiale WorldState-Extraction als getrennte Operationen unter einem transienten Gesamtworkflow ausführen.
  - Completion criteria: Extraction startet ausschließlich nach erfolgreicher Story-Erzeugung; Initialprompt wird nur dem Story-Aufruf übergeben; Fehler identifizieren ihre Stage und stoppen den Ablauf; Erfolg liefert genau einen StoryState und WorldState; kein Repository, GameRun oder GameState wird geschrieben.
  - Resolution: Implemented and verified on 2026-08-10.

- `TASK-012` **Live-Diagnose und Gesamtverifikation ergänzen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-009`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: LLM-Live-Test und Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-011`.
  - Goal: Den vollständigen transienten Initialisierungsablauf mit bewusst aktiviertem LM Studio nachvollziehbar prüfen und offline reproduzierbar absichern.
  - Completion criteria: Der Opt-in-Live-Test druckt beide exakten Requests einschließlich Modell, Optionen und Response-Schema, beide Modellantworten sowie StoryState und WorldState; Extraction verwendet Temperatur 0.1 ohne Tokenlimit; ohne Aktivierungsflag erfolgt kein externer Aufruf; mit Aktivierungsflag läuft der Test erfolgreich gegen das bereitgestellte LM Studio und ein Skip zählt nicht als Live-Nachweis; deterministische Tests und das vollständige Standardprofil bestehen.
  - Resolution: Implemented and verified on 2026-08-10.

- `STORY-010` **Initialen GameRun atomar anlegen**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-10.
  - Area: Story-Initialisierung und Persistenz.
  - Priority: Wichtig.
  - Dependencies: `STORY-008`, `STORY-009`, `STORY-002`.
  - Goal: Den erfolgreich erzeugten transienten StoryState und WorldState zu einem vollständigen initialen GameState zusammenführen und zusammen mit dem GameRun als Revision 1 atomar anlegen.
  - Completion criteria: Ein sichtbarer Application-Workflow orchestriert Story- und WorldState-Initialisierung; Modell- oder Validierungsfehler hinterlassen keinen GameRun; Erfolg persistiert genau einen vollständigen GameRun mit Revision 1; Wiederholungs- und Konfliktverhalten sind getestet. Ein öffentlicher HTTP-Startendpunkt bleibt Teil von `STORY-003`.
  - Resolution: Implemented and verified on 2026-08-11. `InitializeGameRun` creates a `DRAFT` run, revision 1, the initiator's `OWNER` membership, and the UUID-backed Player Mode binding; persistence conflicts and all-or-nothing failure paths are covered. No public HTTP endpoint was added.

- `TASK-013` **Interne StableIds nativ als UUID führen**
  - Type: Task.
  - Status: Completed.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-11.
  - Area: Domainmodell, Persistenz und API.
  - Priority: Wichtig.
  - Dependencies: `STORY-001`, `STORY-002`.
  - Goal: Alle vom Storygame kontrollierten kanonischen Identitäten als streng validierte UUIDs modellieren und in PostgreSQL nativ als UUID speichern, während Keycloak-, TOML-, Prompt-, Provider-, Modell- und lokale LLM-Referenzen textuell bleiben und menschlich lesbare Namen in eigenen Fachfeldern liegen.
  - Completion criteria: `StableId` akzeptiert ausschließlich UUIDs; GameRun-, Entity-, Link-, Fact-, Rule-, Goal- und Turn-IDs sowie ihre internen Referenzen sind in Domain, API und PostgreSQL UUID-typisiert; Goal-Entity-Referenzen liegen nicht mehr als ID-Strings in JSONB; GameRun besitzt einen getrennten Anzeigenamen; lokale LLM-Referenzen werden weiterhin erst durch die Application auf StableIds abgebildet; Fremd- und Konfigurationsreferenzen bleiben Text; die dokumentierte Datenstrategie wurde vor der Schemaänderung bestätigt und die vollständige isolierte Harness-Verifikation besteht.
  - Resolution: Implemented, verified and confirmed by the owner on 2026-08-11.

- `TASK-014` **Szenenzeiger im WorldState einführen**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-006`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Domainmodell, Persistenz, API und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `STORY-009`, `TASK-009`, `STORY-002`.
  - Goal: Den aktuellen Schauplatz der Erzählung als eigene geordnete Aussage im WorldState führen, damit die Kontextauswahl eines Storyzugs nicht auf Ableitungen aus Aufenthaltsbeziehungen angewiesen ist. Aufenthaltsbeziehungen sagen, wo eine Entität ist; der Szenenzeiger sagt, wohin die Erzählung blickt. Im Director Mode fallen beide legitim auseinander. Dieser Task erweitert ausdrücklich den mit `TASK-009` bestätigten Initial-Extraction-Vertrag: der Kandidat besteht nicht mehr nur aus Entities, Links und Facts, sondern zusätzlich aus geordneten lokalen Schauplatzreferenzen. Autoritative Quelle für den erweiterten Vertrag bleibt `.harness/architecture/llm-integration.md` Abschnitt 6a; `TASK-009` wird als abgeschlossene Historie nicht rückwirkend umgeschrieben.
  - Completion criteria: `WorldState.scene_location_ids` ist eine geordnete, duplikatfreie Liste vorhandener Orte mit `primary_scene_location()`; PostgreSQL speichert sie relational und revisionsgebunden in `world_scene_locations`; die API überträgt sie als UUID-Liste; die Initial-Extraction liefert geordnete lokale Schauplatzreferenzen, und unbekannte, doppelte oder nicht auf einen Ort zeigende Referenzen verwerfen den gesamten Kandidaten; `.harness/architecture/llm-integration.md` Abschnitt 6a ist entsprechend erweitert; die Begründung gegen Redundanz ist dokumentiert; bestehende Entwicklungsdatenbanken müssen ohne Upgrade-Migration neu angelegt werden; die vollständige Verifikation einschließlich PostgreSQL besteht.

- `TASK-015` **Kontextauswahl für einen regulären Storyzug**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-006`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `TASK-014`.
  - Goal: Aus dem vollständigen GameState und der Spielereingabe einen deterministischen, erklärbaren und budgetierten Ausschnitt auswählen, den der folgende Story-Modellaufruf als Kontext erhält.
  - Completion criteria: Eine zusammengesetzte Application-Operation delegiert an einzeln testbare Schritte für Grundgerüst, Namenserkennung, Schauplatzbevölkerung, Ein-Hop-Erweiterung, zugehörige Fakten/Wissen/Ziele und Budgetierung; gleicher Zustand und gleiche Eingabe liefern dasselbe Ergebnis; der Eingabezustand bleibt unverändert; die Auswahl filtert nicht nach Visibility; die Budgetkappung bleibt referenziell geschlossen; kein Modellaufruf und keine Persistenz finden statt.

- `TASK-017` **Story-Generation-Aufruf für einen regulären Storyzug**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-006`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-015`, `STORY-005`.
  - Goal: Den ausgewählten Turn-Kontext in den bestehenden `StoryGenerationRequest` projizieren, den Story-Port aufrufen und daraus normalisierte Prosa für den nächsten Zug erhalten. Zusammen mit `TASK-015` erfüllt dieser Task die Completion criteria von `STORY-006`.
  - Completion criteria: Eine Application-Operation bildet den Kontext auf die fünf Textfelder des Requests ab, löst Promptprofil und aktives Story-Modell auf und ruft den Story-Port auf; Erfolg liefert nichtleere normalisierte Prosa; Provider-, Timeout-, Leer- und Fehlerszenarien führen zu typisierten, sichtbaren Failures ohne Retry; der Adapter wählt keine Spieldaten aus; kein kanonischer GameState wird gelesen oder geschrieben; ein leerer Weltausschnitt erzeugt einen gültigen Request statt eines Abbruchs. Verdecktes Wissen wird in diesem ersten Wurf bewusst nicht gekennzeichnet; diese Entscheidung wird unter `TASK-018` beobachtet und gegebenenfalls nachgezogen.

- `TASK-018` **Verdecktes Wissen im Story-Prompt kennzeichnen**
  - Type: Task.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Story-Workflow und Promptgestaltung.
  - Priority: Perspektivisch.
  - Dependencies: `TASK-017`.
  - Goal: Entscheiden und umsetzen, wie dem Modell im Story-Prompt kenntlich gemacht wird, dass ein Teil des Kontexts der Spielerseite noch nicht bekannt ist. Die Kontextauswahl filtert bewusst nicht nach `Visibility`, damit das Modell auf verdeckte Ziele hinarbeiten kann; der erste Wurf von `TASK-017` kennzeichnet den Unterschied im Prompt jedoch bewusst gar nicht. Beobachtet werden muss, ob das Modell dadurch verdeckte Plotpunkte vorzeitig ausspricht.
  - Completion criteria: Es ist entschieden, welche Sichtbarkeitsstufen als verdeckt gelten — mindestens `director_only`, gegebenenfalls auch Wissen anderer Figuren — und wie sie im Prompt erscheinen; die Regel für den Director Mode ohne Spielerfigur ist festgelegt; Projektion und Promptpaket setzen sie um und sind getestet.

- `TASK-019` **Zustandsoperationen für einen Zug ergänzen**
  - Type: Task.
  - Status: Awaiting confirmation.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-014`.
  - Goal: Die beiden Zustandsoperationen ergänzen, ohne die ein regulärer Zug den Weltzustand nicht sinnvoll fortschreiben kann: den Szenenzeiger weiterbewegen und eine nicht mehr geltende Tatsache entfernen.
  - Completion criteria: `SetSceneLocations` setzt geordnete Schauplätze und weist unbekannte Entitäten sowie Nicht-Orte ab; eine leere Liste löscht die Szene. `RemoveFact` entfernt genau eine Tatsache und nimmt das Wissen darüber mit, sodass kein verwaistes Wissen zurückbleibt; eine unbekannte Tatsache wird abgewiesen. Beide Operationen laufen über den freigegebenen Änderungssatz und erhöhen die Revision wie jede andere Änderung. Die Persistenz benötigt keine Schemaänderung, weil je Revision der vollständige Weltsnapshot geschrieben wird.

- `TASK-020` **Extraktionsvertrag und Modellaufruf für einen Zug**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: LLM-Integration und Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `TASK-019`, `TASK-017`.
  - Goal: Aus der neu erzeugten Prosa und dem relevanten bestehenden Weltausschnitt strukturierte, noch nicht freigegebene Änderungskandidaten gewinnen. Ein kombinierter Aufruf, weil lokale Modellaufrufe lange dauern; eine spätere Aufteilung in gezielte Teilaufrufe bleibt möglich.
  - Completion criteria: Ein eigener Extraktionsport mit typisiertem Request und Kandidatentyp existiert; der Kandidat trägt ausschließlich Handles und lokale Referenzen, nie stabile IDs oder freigegebene Operationen. Eine eigene Extraktionsprojektion nennt bestehende Entitäten über kurze Handles, getrennt von der Story-Projektion, die bewusst keine Identifikatoren enthält. Der Adapter übermittelt ein geschlossenes JSON-Schema und lehnt unbekannte Felder, falsche Typen, leere und abgeschnittene Antworten ab; Rohantworten überschreiten die Portgrenze nicht. Der Modellrequest enthält Systemprompts, die neue Prosa und den Vergleichsausschnitt, aber keine Spielereingabe und kein Storyprofil.

- `TASK-021` **Kandidaten fachlich prüfen und freigeben**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `TASK-020`.
  - Goal: Den unbestätigten Kandidaten in einen freigegebenen Änderungssatz überführen. Dieser Pfad ist der gemeinsame Trichter, auf den später auch spezialisierte Extraktionsvarianten münden.
  - Completion criteria: Handles und lokale Referenzen werden gegen die aktuelle Revision aufgelöst, neue Entitäten erhalten erst dabei stabile IDs; ein transienter `ProposedChangeSet` entsteht als Zwischenstufe, an der Reviewevidenz hängen kann. Unbekannte oder doppelte Referenzen, nicht vorhandene zu entfernende Beziehungen, Revisionskonflikte und Domainverstöße verwerfen jeweils den gesamten Vorschlag; es entsteht kein Teilzustand und kein Retry. Die Domain-Invarianten werden über einen verworfenen Trockenlauf geprüft, statt in der Application nachgebaut zu werden. Erfolg liefert genau einen `ApprovedChangeSet`.

- `TASK-022` **Vollständigen Storyzug orchestrieren**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Application-Orchestrierung.
  - Priority: Wichtig.
  - Dependencies: `TASK-021`.
  - Goal: Laden, Kontextauswahl, Story-Erzeugung, Extraktion, Freigabe und atomaren Commit als einen sichtbaren Workflow verbinden.
  - Completion criteria: Die Reihenfolge ist auf Workflowebene sichtbar und über beobachtbares Verhalten getestet; die gesteuerte Figur wird aus der Mitgliedschaft aufgelöst; Modellaufrufe liegen außerhalb der Datenbanktransaktion; ein Fehler vor dem Commit lässt GameState und StoryTurn unverändert; Erfolg persistiert StoryTurn und resultierende Revision gemeinsam. Ein ausdrücklich aktivierter Live-Test führt einen vollständigen Zug gegen LM Studio aus.

- `TASK-023` **Rollierende Zusammenfassung erzeugen**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-022`.
  - Goal: Nach einem abgeschlossenen Zug die fortlaufende Zusammenfassung der bisherigen Geschichte erzeugen und mit dem Zug persistieren.
  - Completion criteria: Ein eigener Port und ein neuer Prompt-Task im Paket existieren; `GenerationTask.SUMMARY` ist bereits konfiguriert, der Prompt-Task fehlte bislang. Der Zug übergibt die erzeugte Zusammenfassung an den atomaren Commit; ein Fehlschlag der Zusammenfassung ist typisiert und macht sichtbar, ob der Zug trotzdem gültig abgeschlossen wurde.

- `TASK-016` **Mehrere gesteuerte Figuren im Director Mode**
  - Type: Task.
  - Status: Open.
  - Parent: `EPIC-001`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Domainmodell und Persistenz.
  - Priority: Perspektivisch.
  - Dependencies: `STORY-001`, `STORY-002`.
  - Goal: Klären und umsetzen, wie ein Benutzer im Director Mode eine oder mehrere Figuren steuert. Heute bindet `GameRunMember` genau eine Figur, und die Director-Initialisierung lässt die Bindung bewusst leer.
  - Completion criteria: Entschieden und dokumentiert ist, ob eine Mitgliedschaft mehrere gesteuerte Figuren binden darf und wie diese bei der Welt-Erzeugung entstehen; Domain, Persistenz und API bilden das Ergebnis ab; die Kontextauswahl nimmt alle gesteuerten Figuren auf.
