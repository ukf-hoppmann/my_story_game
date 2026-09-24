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
  - Status: Completed.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Einen technologieunabhängigen Domain-Kern aus `GameRun` und revisioniertem `GameState` definieren. Der GameState trennt die partielle Konfiguration, die strukturierte Welt einschließlich Goals und die konkrete Turn-Chronologie, ohne LLM-, API- oder Persistenzabhängigkeiten.
  - Completion criteria: GameRun, Mitgliedschaften, GameConfiguration, WorldState, Goals, StoryTurns und StorySummary besitzen verständliche Verantwortlichkeiten und fachliche Invarianten. Goals liegen ausschließlich im WorldState; der StoryState enthält nur abgeschlossene Turns, aktuelle Zusammenfassung und Zugnummer; automatisierte Domain- und Architekturtests sichern die Regeln.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-001` **Domain-Grundtypen und Aggregatgrenzen festlegen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Die technologieunabhängigen Grundtypen und die Grenze zwischen `GameRun` und revisioniertem `GameState` mit `GameConfiguration`, `WorldState` und `StoryState` festlegen.
  - Completion criteria: IDs, Revisionen, Run-Status, Mitgliedsrollen und Sichtbarkeit sind typisiert und validiert. Evidenz gehört ausschließlich zu transienten Application-Vorschlägen und nicht zu kanonischen Facts oder WorldRules. Die Verantwortlichkeiten sind dokumentiert; die Domain importiert keine Datenbank-, API- oder LLM-spezifischen Typen.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-002` **WorldState mit Entitäten und kanonischen Beziehungen modellieren**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-001`.
  - Goal: Figuren, Orte, Gegenstände, Kreaturen und Fraktionen sowie ihre Beziehungen, Fakten, Wissen, Weltregeln und Haupt- beziehungsweise Nebenziele im WorldState abbilden.
  - Completion criteria: Entitäten und Goal-Referenzen sind konsistent. Beziehungen wie Aufenthaltsort, Besitz, Behälter, Zugehörigkeit und soziale Verbindung referenzieren nur vorhandene Entitäten. Goals unterscheiden `main` und `side` sowie `open`, `completed` und `failed`; Inventar wird aus Besitzbeziehungen abgeleitet.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-003` **StoryState als konkrete Turn-Chronologie modellieren**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-002`.
  - Goal: Die konkrete Geschichte als Folge vollständig abgeschlossener StoryTurns mit einer aktuellen rollierenden Zusammenfassung und Zugnummer modellieren.
  - Completion criteria: StoryTurns enthalten `player_input`, Erzählung, Sequenz, Basis- und Ergebnisrevision sowie Abschlusszeitpunkt. Sequenzen sind lückenlos; Goals, Chapters, Scenes, StoryThreads und ein zusätzliches StoryEvent sind nicht Teil des StoryState.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-004` **Vorschlags- und Freigabegrenze für Zustandsänderungen definieren**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-002`, `TASK-003`.
  - Goal: Unbestätigte LLM-Vorschläge als transiente Application-Daten von freigegebenen Domain-Operationen und dem kanonischen GameState trennen.
  - Completion criteria: `ProposedChangeSet` liegt ausschließlich in der Application und wird nicht persistiert. Rohdaten oder Prosa können den GameState nicht direkt verändern. Nur ein `ApprovedChangeSet` kann auf der erwarteten Revision angewendet werden; veraltete Revisionen und ungültige Referenzen werden abgewiesen.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-005` **Domain-Invarianten und Storygame-Beispielfälle testen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-004`.
  - Goal: Die fachlichen Regeln des Domain-Kerns deterministisch absichern und anhand eines kleinen zielorientierten Storygame-Szenarios prüfen.
  - Completion criteria: Tests decken IDs, Mitgliedschaften, Referenzkonsistenz, Sichtbarkeit, Wissen, Besitz, Goals, Turn-Chronologie und Revisionskonflikte ab. Das Beispiel kann Almas, ein Hauptziel und einen abgeschlossenen Turn konsistent in den nächsten GameState überführen.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `STORY-002` **Datenbankanbindung für den Storygame-Zustand**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: Persistenz.
  - Priority: Wichtig.
  - Dependencies: `STORY-001`.
  - Goal: GameRun und revisionierten GameState über einen PostgreSQL-Adapter dauerhaft speichern, ohne die Domain an PostgreSQL zu koppeln.
  - Completion criteria: Ein vollständiger neuer Lauf sowie aktuelle und historische Revisionen können gespeichert und geladen werden. GameConfiguration, WorldState einschließlich Goals und StoryState werden rekonstruiert. Konfigurationsrevisionen benötigen keinen Turn; ein abgeschlossener Turn und seine Ergebnisrevision werden atomar gespeichert. Das alte JSON- und Story-Tabellenmodell ist entfernt; PostgreSQL-Integrationstests bestehen.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `STORY-003` **API für den Storygame-Zustand**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-001`.
  - Required for parent: Yes.
  - Created: 2026-08-04.
  - Area: API.
  - Priority: Wichtig.
  - Dependencies: `STORY-002`.
  - Goal: Den Storygame-Zustand über eine stabile API für die späteren Benutzeroberflächen und Anwendungsfälle zugänglich machen. Die API trennt Lesen, fachliche Änderungsanträge und deren geprüfte Übernahme.
  - Completion criteria: Ein Client kann einen Storygame-Zustand anlegen, laden und fachlich valide Änderungen anfordern. Die API gibt keine direkten LLM-Schreibrechte frei, validiert Referenzen und Zustandsrevisionen und liefert verständliche Fehler bei ungültigen oder veralteten Änderungen. API- und Integrations-Tests prüfen die unterstützten Abläufe. Erfüllt über `TASK-029` (Lauf-Lebenszyklus-Endpunkte: Liste, Laden, Vorlage anlegen, Abzweig, Zug) und den Propose/Confirm-Init-Flow (`POST /api/v1/runs/proposals`, `POST /api/v1/runs`); Fehlerabbildung in `Backend/src/story_game/api/errors.py` deckt Revisionskonflikte, ungültige Referenzen, Domain-Ablehnung und Statusverletzungen typisiert ab; `Backend/tests/api/test_api.py` (12 Tests) prüft Laden, Liste, Propose/Confirm, Playthrough-Start und Turn-Play inklusive Ablehnungsfällen.
  - Resolution: Confirmed by the project owner on 2026-08-19.

- `TASK-029` **Lauf-Lebenszyklus-Endpunkte mit fester Entwicklungsidentität**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-003`.
  - Required for parent: Yes.
  - Created: 2026-08-18.
  - Area: API.
  - Priority: Wichtig.
  - Dependencies: `STORY-008`, `STORY-009`, `STORY-010`, `TASK-022`.
  - Goal: Die vorhandenen `InitializeGameRun`- und `PlayStoryTurn`-Workflows über echte HTTP-Endpunkte erreichbar machen, damit eine UI eine Geschichte auflisten, laden, starten und einen Zug spielen kann — ohne Keycloak, über eine fest verdrahtete, austauschbare Entwicklungsidentität. Ergänzt eine neue `StartPlaythrough`-Operation: `InitializeGameRun` legt eine unveränderliche `DRAFT`-Vorlage an; erst ein expliziter Abzweig kopiert sie in einen unabhängigen `ACTIVE`-Lauf, sodass dasselbe Szenario mehrfach gespielt werden kann.
  - Completion criteria: `GET /api/v1/runs` (Liste), `GET /api/v1/runs/{run_id}` (laden), `POST /api/v1/runs` (Vorlage erzeugen), `POST /api/v1/runs/{run_id}/playthroughs` (Abzweig) und `POST /api/v1/runs/{run_id}/turns` (Zug) sind implementiert; die alten provisorischen Endpunkte (`POST /api/v1/runs` mit rohem GameDocument, `GET .../state`) sind ersetzt. Ein Zug gegen eine `DRAFT`-Vorlage wird mit `run_not_active` abgewiesen; ein Abzweig von einem bereits aktiven Lauf mit `playthrough_source_not_draft`. Eine feste, über `STORY_GAME_DEV_ISSUER`/`STORY_GAME_DEV_SUBJECT` konfigurierbare Identität wird über eine einzige austauschbare Dependency aufgelöst. `StoryInitializationError`, `StoryTurnError` und `ContextSelectionError` sind vollständig auf HTTP-Fehlercodes abgebildet. Ein neuer `PlayableRunLister`-Port mit PostgreSQL-Adapter und zusätzlichem `(issuer, subject)`-Index liefert die Liste ohne vollen WorldState pro Zeile. Alle betroffenen Tests (`tests/api`) sind angepasst und bestehen; der volle End-to-End-Ablauf (Vorlage → Abzweig → Zug) wurde manuell gegen echtes PostgreSQL und LM Studio geprüft. Ein öffentlicher Konfigurations- oder Auth-Endpunkt ist weiterhin nicht Teil dieser Arbeit.
  - Resolution: Confirmed by the project owner on 2026-08-19.
  - Subsequent state: The completed item records the then-current fixed
    development identity and direct initialization flow. Since 2026-09-08,
    run endpoints authenticate Keycloak bearer tokens and authorize access by
    membership. Since 2026-09-09, the public prompt-profile catalog plus
    proposal-time and revisioned configuration selection extend the API.
    The current public contract is maintained in
    `docs/human/technical/api.md`; this historical completion record remains
    unchanged.

- `EPIC-002` **LLM-Anbindung und Storyzug-Workflow**
  - Type: Epic.
  - Status: In progress.
  - Created: 2026-08-07.
  - Area: LLM-Integration und Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `EPIC-001`.
  - Goal: Einen vollständigen, providerunabhängigen Storyzug aus Modell- und Promptkatalogen, tatsächlichen Modellaufrufen, Story-Erzeugung, WorldState-Extraktion, fachlicher Freigabe und atomarem Turn-Commit zusammensetzen.
  - Completion criteria: Die sieben zugehörigen Stories sind umgesetzt und integriert. Ein vollständiger Storyzug kann zuerst aus einem Initialprompt einen StoryState und danach einen WorldState bilden, den initialen GameState atomar anlegen, den relevanten fortlaufenden GameState-Kontext verwenden, normalisierte Story-Prosa erzeugen, strukturierte Extraktionsvorschläge fachlich prüfen und ausschließlich einen abgeschlossenen StoryTurn mit der resultierenden GameState-Revision persistieren. Modellaufrufe, Rohantworten, ProposedChangeSets und Validierungsergebnisse bleiben transient.

- `STORY-004` **Anbindungsverträge definieren**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-06.
  - Area: LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Die providerunabhängigen, typisierten Verträge für Story-Erzeugung, Extraktion und Modellaufrufe als Application-eigene Ports festlegen.
  - Completion criteria: Task-spezifische Requests und Success-Daten, eine geeignete typisierte Generation-Call-Hülle sowie die gemeinsame `Success`-/`Failure`- und `LLMError`-Grenze sind dokumentiert, implementiert und unabhängig testbar. Providerobjekte, Rohantworten und konkrete Providerformate überschreiten die Application-Grenze nicht.
  - Resolution: Confirmed by the project owner on 2026-08-19.

- `STORY-005` **LLM anbinden**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-07.
  - Area: LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `STORY-004`, `STORY-001`, `STORY-002`.
  - Goal: Die vereinbarten Modellverträge mit dateibasierten Modell- und Promptkatalogen sowie einem austauschbaren Provider-Adapter und Provider-Client ausführbar verbinden.
  - Completion criteria: TOML-basierte globale Konfiguration und versionierte Promptdateien werden über Application-Ports geladen. Provider-Geheimnisse kommen aus einer zugelassenen externen Laufzeitquelle. Ein tatsächlicher Modellaufruf kann über einen Testdouble und den vorgesehenen Providerpfad ausgeführt werden; Rohantworten und Providerfehler bleiben transient beziehungsweise werden in die Application-eigene Fehlerfamilie übersetzt.
  - Resolution: Confirmed by the project owner on 2026-08-19.

- `STORY-006` **Story Generation erstellen**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-07.
  - Area: Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `STORY-005`, `STORY-010`.
  - Goal: Aus GameConfiguration, relevantem WorldState, StoryState und aktuellem Spielerprompt eine fachlich definierte Story-Generation-Anfrage zusammensetzen und daraus normalisierte Story-Prosa erzeugen.
  - Completion criteria: Der Workflow wählt und strukturiert den Kontext in der Application, ruft den Story-Port auf und liefert bei Erfolg nichtleere, valide Prosa. Adapter wählen keine Spieldaten aus und verändern keinen kanonischen GameState. Provider-, Timeout-, Leer- und Fehlerszenarien sind über beobachtbares Workflowverhalten getestet.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `STORY-007` **Extraktion erstellen**
  - Type: Story.
  - Status: Completed.
  - Parent: `EPIC-002`.
  - Required for parent: Yes.
  - Created: 2026-08-07.
  - Area: WorldState-Extraktion und Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `STORY-006`, `STORY-001`, `STORY-002`.
  - Goal: Aus der erzeugten Story-Prosa strukturierte WorldState-Änderungskandidaten extrahieren, fachlich validieren und gemeinsam mit dem abgeschlossenen StoryTurn atomar übernehmen.
  - Completion criteria: Technisch valide Extraktionsdaten werden in typisierte, noch nicht freigegebene Kandidaten überführt. Referenzen, Domain-Invarianten, Revisionen und fachliche Plausibilität werden geprüft; unbestätigte oder teilweise fehlerhafte Ergebnisse schreiben keinen kanonischen Zustand. Nur ein vollständiger, freigegebener Turn persistiert den StoryTurn und die resultierende GameState-Revision gemeinsam.
  - Resolution: Confirmed by the project owner on 2026-08-18.

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

- `TASK-028` **Repetition-Loop und Entitäts-Relevanz bei der Initial-Extraction beheben**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-009`.
  - Required for parent: No.
  - Created: 2026-08-18.
  - Area: LLM-Integration, Initial-Extraction (Prompt und Sampling).
  - Priority: Wichtig.
  - Dependencies: `STORY-009`, `TASK-009`, `TASK-012`.
  - Goal: Der Live-Test `test_state_extract` schlägt reproduzierbar fehl, weil das
    Extraction-Modell (`llama@q4_k_m`, Temperature 0.1, striktes JSON-Schema) in
    eine Wiederholungsschleife läuft und dieselbe Handvoll Entitäten wiederholt
    ausgibt, bis das Kontextlimit erreicht und die Antwort abgeschnitten wird.
    Unabhängig davon fragmentiert der Prompt Objekte zu grob in Teil-Entitäten
    (z. B. "Griff des Schwertes" statt "Schwert") und extrahiert auch narrativ
    irrelevante, transiente Requisiten (z. B. ein Buttermesser beim
    Brotschmieren), während plotrelevante Gegenstände (ein Schwert, ein Messer
    als Waffe) korrekt als Entität geführt werden sollen. `TASK-012` hat
    Temperatur 0.1 ohne Tokenlimit bewusst bestätigt; diese Entscheidung muss
    im Licht des Repetition-Loops erneut geprüft werden, nicht stillschweigend
    überschrieben werden.
  - Completion criteria: Entschieden und umgesetzt ist, wie die Wiederholungs-
    schleife verhindert wird (z. B. Sampling-Anpassung, Modellwahl oder eine neue
    Generation-Option) und wie der Prompt Objekte nach narrativer Relevanz statt
    nach bloßer Erwähnung extrahiert, ohne plotrelevante Gegenstände wie Waffen
    zu verlieren. Der Live-Test `test_state_extract` läuft wiederholt ohne
    Abschneiden durch; der resultierende WorldState enthält keine künstlich
    fragmentierten Teil-Entitäten und keine transienten Requisiten ohne
    erwartbare Wiederverwendung. Jede Sampling- oder Modelländerung ist mit
    Begründung dokumentiert und gegen die in `TASK-012` bestätigte Entscheidung
    abgeglichen.

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
  - Status: Completed.
  - Parent: `STORY-006`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Domainmodell, Persistenz, API und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `STORY-009`, `TASK-009`, `STORY-002`.
  - Goal: Den aktuellen Schauplatz der Erzählung als eigene geordnete Aussage im WorldState führen, damit die Kontextauswahl eines Storyzugs nicht auf Ableitungen aus Aufenthaltsbeziehungen angewiesen ist. Aufenthaltsbeziehungen sagen, wo eine Entität ist; der Szenenzeiger sagt, wohin die Erzählung blickt. Im Director Mode fallen beide legitim auseinander. Dieser Task erweitert ausdrücklich den mit `TASK-009` bestätigten Initial-Extraction-Vertrag: der Kandidat besteht nicht mehr nur aus Entities, Links und Facts, sondern zusätzlich aus geordneten lokalen Schauplatzreferenzen. Autoritative Quelle für den erweiterten Vertrag bleibt `.harness/architecture/llm-integration.md` Abschnitt 6a; `TASK-009` wird als abgeschlossene Historie nicht rückwirkend umgeschrieben.
  - Completion criteria: `WorldState.scene_location_ids` ist eine geordnete, duplikatfreie Liste vorhandener Orte mit `primary_scene_location()`; PostgreSQL speichert sie relational und revisionsgebunden in `world_scene_locations`; die API überträgt sie als UUID-Liste; die Initial-Extraction liefert geordnete lokale Schauplatzreferenzen, und unbekannte, doppelte oder nicht auf einen Ort zeigende Referenzen verwerfen den gesamten Kandidaten; `.harness/architecture/llm-integration.md` Abschnitt 6a ist entsprechend erweitert; die Begründung gegen Redundanz ist dokumentiert; bestehende Entwicklungsdatenbanken müssen ohne Upgrade-Migration neu angelegt werden; die vollständige Verifikation einschließlich PostgreSQL besteht.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-015` **Kontextauswahl für einen regulären Storyzug**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-006`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `TASK-014`.
  - Goal: Aus dem vollständigen GameState und der Spielereingabe einen deterministischen, erklärbaren und budgetierten Ausschnitt auswählen, den der folgende Story-Modellaufruf als Kontext erhält.
  - Completion criteria: Eine zusammengesetzte Application-Operation delegiert an einzeln testbare Schritte für Grundgerüst, Namenserkennung, Schauplatzbevölkerung, Ein-Hop-Erweiterung, zugehörige Fakten/Wissen/Ziele und Budgetierung; gleicher Zustand und gleiche Eingabe liefern dasselbe Ergebnis; der Eingabezustand bleibt unverändert; die Auswahl filtert nicht nach Visibility; die Budgetkappung bleibt referenziell geschlossen; kein Modellaufruf und keine Persistenz finden statt.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-017` **Story-Generation-Aufruf für einen regulären Storyzug**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-006`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-015`, `STORY-005`.
  - Goal: Den ausgewählten Turn-Kontext in den bestehenden `StoryGenerationRequest` projizieren, den Story-Port aufrufen und daraus normalisierte Prosa für den nächsten Zug erhalten. Zusammen mit `TASK-015` erfüllt dieser Task die Completion criteria von `STORY-006`.
  - Completion criteria: Eine Application-Operation bildet den Kontext auf die fünf Textfelder des Requests ab, löst Promptprofil und aktives Story-Modell auf und ruft den Story-Port auf; Erfolg liefert nichtleere normalisierte Prosa; Provider-, Timeout-, Leer- und Fehlerszenarien führen zu typisierten, sichtbaren Failures ohne Retry; der Adapter wählt keine Spieldaten aus; kein kanonischer GameState wird gelesen oder geschrieben; ein leerer Weltausschnitt erzeugt einen gültigen Request statt eines Abbruchs. Verdecktes Wissen wird in diesem ersten Wurf bewusst nicht gekennzeichnet; diese Entscheidung wird unter `TASK-018` beobachtet und gegebenenfalls nachgezogen.
  - Resolution: Confirmed by the project owner on 2026-08-18.

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
  - Status: Completed.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Domainmodell.
  - Priority: Wichtig.
  - Dependencies: `TASK-014`.
  - Goal: Die beiden Zustandsoperationen ergänzen, ohne die ein regulärer Zug den Weltzustand nicht sinnvoll fortschreiben kann: den Szenenzeiger weiterbewegen und eine nicht mehr geltende Tatsache entfernen.
  - Completion criteria: `SetSceneLocations` setzt geordnete Schauplätze und weist unbekannte Entitäten sowie Nicht-Orte ab; eine leere Liste löscht die Szene. `RemoveFact` entfernt genau eine Tatsache und nimmt das Wissen darüber mit, sodass kein verwaistes Wissen zurückbleibt; eine unbekannte Tatsache wird abgewiesen. Beide Operationen laufen über den freigegebenen Änderungssatz und erhöhen die Revision wie jede andere Änderung. Die Persistenz benötigt keine Schemaänderung, weil je Revision der vollständige Weltsnapshot geschrieben wird.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-020` **Extraktionsvertrag und Modellaufruf für einen Zug**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: LLM-Integration und Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `TASK-019`, `TASK-017`.
  - Goal: Aus der neu erzeugten Prosa und dem relevanten bestehenden Weltausschnitt strukturierte, noch nicht freigegebene Änderungskandidaten gewinnen. Ein kombinierter Aufruf, weil lokale Modellaufrufe lange dauern; eine spätere Aufteilung in gezielte Teilaufrufe bleibt möglich.
  - Completion criteria: Ein eigener Extraktionsport mit typisiertem Request und Kandidatentyp existiert; der Kandidat trägt ausschließlich Handles und lokale Referenzen, nie stabile IDs oder freigegebene Operationen. Eine eigene Extraktionsprojektion nennt bestehende Entitäten über kurze Handles, getrennt von der Story-Projektion, die bewusst keine Identifikatoren enthält. Der Adapter übermittelt ein geschlossenes JSON-Schema und lehnt unbekannte Felder, falsche Typen, leere und abgeschnittene Antworten ab; Rohantworten überschreiten die Portgrenze nicht. Der Modellrequest enthält Systemprompts, die neue Prosa und den Vergleichsausschnitt, aber keine Spielereingabe und kein Storyprofil.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-021` **Kandidaten fachlich prüfen und freigeben**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow.
  - Priority: Wichtig.
  - Dependencies: `TASK-020`.
  - Goal: Den unbestätigten Kandidaten in einen freigegebenen Änderungssatz überführen. Dieser Pfad ist der gemeinsame Trichter, auf den später auch spezialisierte Extraktionsvarianten münden.
  - Completion criteria: Handles und lokale Referenzen werden gegen die aktuelle Revision aufgelöst, neue Entitäten erhalten erst dabei stabile IDs; ein transienter `ProposedChangeSet` entsteht als Zwischenstufe, an der Reviewevidenz hängen kann. Unbekannte oder doppelte Referenzen, nicht vorhandene zu entfernende Beziehungen, Revisionskonflikte und Domainverstöße verwerfen jeweils den gesamten Vorschlag; es entsteht kein Teilzustand und kein Retry. Die Domain-Invarianten werden über einen verworfenen Trockenlauf geprüft, statt in der Application nachgebaut zu werden. Erfolg liefert genau einen `ApprovedChangeSet`.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-022` **Vollständigen Storyzug orchestrieren**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Application-Orchestrierung.
  - Priority: Wichtig.
  - Dependencies: `TASK-021`.
  - Goal: Laden, Kontextauswahl, Story-Erzeugung, Extraktion, Freigabe und atomaren Commit als einen sichtbaren Workflow verbinden.
  - Completion criteria: Die Reihenfolge ist auf Workflowebene sichtbar und über beobachtbares Verhalten getestet; die gesteuerte Figur wird aus der Mitgliedschaft aufgelöst; Modellaufrufe liegen außerhalb der Datenbanktransaktion; ein Fehler vor dem Commit lässt GameState und StoryTurn unverändert; Erfolg persistiert StoryTurn und resultierende Revision gemeinsam. Ein ausdrücklich aktivierter Live-Test führt einen vollständigen Zug gegen LM Studio aus — erfüllt durch `TestStoryTurnHuman.test_full_turn`, das `PlayStoryTurn` gegen echtes LM Studio und einen In-Memory-Store laufen lässt. Die zuvor offene Lücke, dass kein Lauf echtes LM Studio und echte PostgreSQL-Persistenz verbindet, ist geschlossen durch `TestFullPlaythroughHuman.test_init_and_play_one_turn` (`InitializeGameRun` gefolgt von `PlayStoryTurn`, beide gegen echtes LM Studio und eine echte PostgreSQL-Instanz, mit Aufräumen des angelegten Runs danach; verifiziert am 2026-08-17).
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-023` **Rollierende Zusammenfassung erzeugen**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-007`.
  - Required for parent: Yes.
  - Created: 2026-08-17.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-022`.
  - Goal: Nach einem abgeschlossenen Zug die fortlaufende Zusammenfassung der bisherigen Geschichte erzeugen und mit dem Zug persistieren.
  - Completion criteria: Ein eigener Port und ein neuer Prompt-Task im Paket existieren; `GenerationTask.SUMMARY` war bereits konfiguriert, der Prompt-Task fehlte. Der Zug übergibt die erzeugte Zusammenfassung an den atomaren Commit. Ein Fehlschlag der Zusammenfassung bricht den Zug **nicht** ab: Prosa und Änderungen werden regulär persistiert, und der typisierte Fehler bleibt über das Zugergebnis sichtbar. Der dauerhafte Logeintrag, an dem sich wiederkehrende Fehlschläge erkennen lassen, steht noch aus und gehört zu `TASK-024`.
  - Resolution: Confirmed by the project owner on 2026-08-18.
  - Subsequent state: `TASK-032` replaced the single rolling summary with an append-only chain of immutable `StorySummarySegment` values. This historical item remains unchanged as the original decision record; the current behavior is documented in the domain, persistence, and story-generation documentation.

- `TASK-025` **Historische Daten in den Turn-Kontext aufnehmen**
  - Type: Task.
  - Status: Open.
  - Parent: `EPIC-002`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Story-Workflow.
  - Priority: Perspektivisch.
  - Dependencies: `TASK-015`.
  - Goal: Bezugnahmen auf Vergangenes im Prompt auflösbar machen. Die Kontextauswahl liest heute ausschließlich die aktuelle Revision. Sagt der Spieler „ich gehe zurück", weiß das Modell nur dann was gemeint ist, wenn der frühere Ort zufällig noch in den letzten Zügen oder der Zusammenfassung vorkommt. Die Information liegt vollständig in der Datenbank — jede Revision hält einen kompletten Weltsnapshot, alte Revisionen werden nie gelöscht — sie erreicht nur den Prompt nicht.
  - Completion criteria: Entschieden und umgesetzt ist, welcher historische Ausschnitt in den Kontext gelangt — mindestens der vorherige Schauplatz, gegebenenfalls frühere Aufenthaltsorte oder entfernte Tatsachen. Die Auswahl bleibt deterministisch und budgetiert; die Herkunft der historischen Daten ist im Prompt als solche erkennbar, damit das Modell Vergangenes nicht als Gegenwart erzählt.

- `TASK-026` **Automatischen Review der Änderungsvorschläge einführen**
  - Type: Task.
  - Status: Open.
  - Parent: `STORY-007`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Story-Workflow und Diagnose.
  - Priority: Wichtig.
  - Dependencies: `TASK-021`.
  - Goal: Vorgeschlagene Änderungen automatisch und ohne nennenswerte Rechenlast auf Plausibilität prüfen, statt sie nur strukturell zu validieren. Der Review läuft ohne Benutzereingriff und hält den Spielfluss nicht an; seine Befunde sollen optional anzeigbar sein, damit sichtbar wird, wie oft und wobei das Modell danebenliegt.
  - Completion criteria: Das Delta-Schema führt je Änderung einen Beleg als wörtliches Zitat aus der Erzählung. Deterministische Prüfungen erzeugen je Änderung Befunde: der Beleg kommt in der Erzählung tatsächlich vor; die Bezeichnung einer neu vorgeschlagenen Entität ist in der Erzählung auffindbar; ein neuer Schauplatz ist genannt oder unverändert. Die vorhandene deutschsprachige Namenserkennung wird dafür wiederverwendet, statt eine zweite zu bauen. Befunde sind Hinweise, keine Ablehnung — strukturelle Fehler und Domainverstöße verwerfen den Vorschlag weiterhin ganz. Die Befunde sind abrufbar und im Live-Test sichtbar. Dokumentiert ist, was der automatische Review ausdrücklich nicht leisten kann.

- `TASK-027` **Belege der Änderungsvorschläge optional anfordern**
  - Type: Task.
  - Status: Completed.
  - Parent: `STORY-007`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: LLM-Integration und Diagnose.
  - Priority: Wichtig.
  - Dependencies: `TASK-021`.
  - Goal: Das Modell je vorgeschlagener Änderung ein wörtliches Zitat aus der Erzählung mitliefern lassen, als Grundlage für den automatischen Review und für eine spätere Anzeige. Weil Ausgabetoken lokal die langsamste und bei API-Abrechnung die teuerste Ressource sind, muss die Anforderung abschaltbar sein.
  - Completion criteria: Der Extraktions-Request trägt einen Schalter; der Adapter wählt danach zwischen zwei Schemavarianten, sodass ohne Schalter kein Belegfeld im Schema erscheint. Belege erreichen als Zitat die `ProposalEvidence` der jeweiligen Änderung. Der transiente Vorschlag ist im Zugergebnis lesbar, damit die Begründungen überhaupt sichtbar werden können; persistiert wird er nicht. Eine fehlende Begründung verwirft einen Vorschlag nicht. Die Initial-Extraction bleibt unberührt.
  - Resolution: Confirmed by the project owner on 2026-08-18.

- `TASK-024` **Logging-Grundlage einführen**
  - Type: Task.
  - Status: Completed.
  - Parent: None.
  - Created: 2026-08-17.
  - Area: Betrieb und Diagnose.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Eine schlanke, projektweite Logging-Grundlage schaffen. Das Projekt enthielt zuvor kein einziges Log: weder Modellaufrufe noch verworfene Vorschläge, Revisionskonflikte oder Providerfehler hinterließen eine Spur. Wiederkehrende Probleme im Spielbetrieb waren dadurch nicht erkennbar.
  - Completion criteria: Es ist entschieden, welche Ereignisse geloggt werden und auf welcher Stufe, wie die Ausgabe konfiguriert wird und wie die Schichtengrenzen eingehalten bleiben — die Domain loggt nicht, die Application entscheidet fachlich über einen eigenen `DiagnosticsLog`-Port (`record()`/`trace()`), Infrastruktur (`structlog`) und Composition Root richten ein. Explizit vom Projektbesitzer nachträglich erweitert (2026-08-18): im PROD-Profil (Default) dürfen Spielerprosa, Prompts und Rohantworten nicht ungefiltert im Log landen — durchgesetzt über das geschlossene, typisierte `DiagnosticEvent`-Schema, nicht nur per Konvention; im ausdrücklich aktivierten DEBUG-Profil wird dagegen bewusst exzessiv geloggt, inklusive roher Prompts/Provider-Antworten (in den LM-Studio-Adaptern) und transformierter Zwischendaten an jeder Operationsgrenze (`trace()` in Application), damit auch Fehler innerhalb einer Transformation auffindbar sind. Mindestens fehlgeschlagene Modellaufrufe, verworfene Änderungsvorschläge und Revisionskonflikte sind über `record()` sichtbar. Bestehende typisierte Fehler bleiben unverändert; das Log ergänzt sie, ersetzt sie nicht. Der Modus ist zentral in der versionierten `configs/app.toml` (`[logging]`) gepflegt — dort steht aktuell `mode = "debug"`, weil der Projektbesitzer derzeit durchgängig mit Debug arbeitet; `STORY_GAME_LOG_MODE`/`STORY_GAME_LOG_LEVEL` bleiben als Laufzeit-Override erhalten (Env-Var schlägt Datei schlägt Hardcoded-Default), geladen über `TomlAppConfigurationLoader`/`LoggingSettings.resolve()`. Geloggt wird gleichzeitig nach stdout und in eine rotierende Datei (`logs/story-game.log`, Default 10 MiB × 5 Backups, Pfad und Rotation in derselben Config-Datei einstellbar); `logs/` ist per `.gitignore` ausgeschlossen und in `compose.yaml` als Volume gemountet, damit die Datei Container-Neustarts übersteht. `PlayStoryTurn`, `InitializeGameRun` und die Story-Workflow-Operationen sind in der FastAPI-App verdrahtet; die Diagnostics-Verdrahtung lebt im Composition Root und im Human-Inspection-Testbündel (`tests/infrastructure/llm/lmstudio/human_test_support.py`, dort bewusst fest auf Debug verdrahtet).
  - Resolution: Confirmed by the project owner on 2026-08-19.

- `TASK-016` **Mehrere gesteuerte Figuren im Director Mode**
  - Type: Task.
  - Status: Completed.
  - Parent: `EPIC-001`.
  - Required for parent: No.
  - Created: 2026-08-17.
  - Area: Domainmodell, Story-Initialisierung und API.
  - Priority: Wichtig.
  - Dependencies: `TASK-007`, `TASK-010`, `TASK-011`.
  - Resolution: Confirmed by the project owner on 2026-08-19. Umgesetzt am 2026-08-18. `GameRunMember.player_entity_id` (ein optionaler Wert) wurde zu `controlled_entity_ids: tuple[StableId, ...]` generalisiert; `PlayerCharacterSeed` wurde zu `ControllableCharacterSeed` und der Request nimmt eine Liste `controllable_characters` statt eines Einzelwerts. Player Mode verlangt weiterhin genau eine Figur; Director Mode erlaubt 0..N explizit benannte Figuren (neuer Policy-Fehler `duplicate_controllable_character` bei doppelten Namen). Die reservierte Referenz bei der Welt-Extraktion wurde von einem festen `player_character`-Wort auf eine Liste (`player_character`, `player_character_2`, …) erweitert. Betroffen: Domain (`game_run.py`, `game_state.py`), Application (`initialization_policy.py`, `initial_world_extraction.py`, `play_story_turn.py`, `story_turn_context.py`, `select_always_included.py`, `story_turn_context_models.py`), LM-Studio-Adapter, API (`schemas/common.py`, `schemas/runs.py`, `routers/runs.py`, `mappers/state.py`), Postgres-Migration `003_controllable_characters.sql` (neue Tabelle `game_run_member_controlled_entities` statt der Spalte `player_entity_id`). Zusätzlich wurde `generate_story.py`s System-Prompt um eine feste NPC-Agency-Anweisung ergänzt (nur gesteuerte Figuren handeln auf Prompt-Basis) — best effort, ohne Durchsetzung.
  - Goal: Klären und umsetzen, wie ein Benutzer im Director Mode eine oder mehrere Figuren steuert. Heute bindet `GameRunMember` genau eine Figur, und die Director-Initialisierung lässt die Bindung bewusst leer.
  - Completion criteria: Entschieden und dokumentiert ist, ob eine Mitgliedschaft mehrere gesteuerte Figuren binden darf und wie diese bei der Welt-Erzeugung entstehen; Domain, Persistenz und API bilden das Ergebnis ab; die Kontextauswahl nimmt alle gesteuerten Figuren auf.

- `STORY-011` **Web-Frontend-Grundgerüst**
  - Type: Story.
  - Parent: None.
  - Status: Completed.
  - Created: 2026-08-18.
  - Area: Repo-Struktur und Web-Frontend.
  - Priority: Wichtig.
  - Dependencies: `TASK-029`.
  - Goal: Das Repo in Subprojekte gliedern (`Backend/`, `Frontend-Web/`, Platz für spätere Subprojekte wie Mobile oder Keycloak) und ein minimales, echt gegen die Backend-API sprechendes React/Vite/TypeScript-Grundgerüst anlegen — Runs-Liste, Vorlage starten, Zug spielen.
  - Completion criteria: `src/`, `tests/`, `configs/`, `prompts/`, `pyproject.toml`, `requirements.txt`, `Dockerfile`, `.env.example` liegen unter `Backend/`; `compose.yaml`, `story-starter`, `.devcontainer/` bleiben am Root und funktionieren unverändert (verifiziert: `cd Backend && pytest` — 405 Tests grün; `docker compose build`; `./story-starter` mit funktionierendem `GET /health`, inklusive behobenem fehlenden `COPY prompts` im Dockerfile). Backend erlaubt CORS für den Vite-Dev-Server (`STORY_GAME_CORS_ALLOWED_ORIGINS`). `Frontend-Web/` enthält einen typisierten API-Client (`client.ts`, `types.ts`), einen `useApiRequest`-Hook für Lade-/Fehlerzustände und drei Screens (Runs-Liste, Vorlage starten, Zug spielen) ohne Router und ohne OpenAPI-Codegen (bewusste MVP-Entscheidungen, siehe `Frontend-Web/README.md`). Live gegen echtes Docker-Backend verifiziert: CORS-Preflight, Runs-Liste lädt echte Daten, Formular-Fehler (`invalid_candidate_reference`) wird korrekt als Fehler-Banner angezeigt. Ein vollständiger Klick-Durchlauf bis zum gespielten Zug wurde wegen unzuverlässiger lokaler Modellantworten nicht abschließend live bestätigt — die Turn-Play-Logik selbst ist nicht anders verifiziert als durch Code-Review und TypeScript-Typprüfung.
  - Resolution: Confirmed by the project owner on 2026-08-19.

- `TASK-030` **Frontend-Fehler diagnostizierbar machen (Logging + konkrete Fehlermeldungen)**
  - Type: Task.
  - Status: Completed.
  - Parent: None.
  - Created: 2026-09-10.
  - Area: Web-Frontend, Betrieb und Diagnose.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Anlass war ein konkreter Vorfall am 2026-09-10: Im Wizard schlug "Geschichte beginnen" nach längerer Bearbeitungszeit auf dem Review-Schritt fehl. Die UI zeigte nur die generische Meldung "Die Geschichte konnte nicht gestartet werden. Bitte versuche es erneut." ([Wizard.tsx:506-509](Frontend-Web/src/routes/Wizard/Wizard.tsx:506)); die eigentliche Ursache (`POST /api/v1/runs` → `401 Unauthorized`, vermutlich abgelaufenes Keycloak-Token, das `keycloak.onTokenExpired`/`updateToken` nicht rechtzeitig aufgefrischt hat, siehe [auth.ts:22-31](Frontend-Web/src/api/auth.ts:22)) war nur über `docker compose logs backend` rekonstruierbar, nicht aus der Anwendung selbst. Zusätzlich verschlucken `handleCreateProposal`/`handleConfirmAndStart` in [Wizard.tsx:151-168](Frontend-Web/src/routes/Wizard/Wizard.tsx:151) jeden Fehler, der nicht über den RTK-Query-Mutation-State läuft, in einem leeren `catch {}` — ein synchroner Fehler vor dem eigentlichen Request bliebe komplett unsichtbar. Analog zu `TASK-024` (Backend-Logging) soll das Frontend eigene Fehler und fehlgeschlagene API-Aufrufe sichtbar protokollieren (mindestens Browser-Konsole mit Statuscode/Fehlercode; zu klären, ob zusätzlich ein Versand ans Backend sinnvoll ist) und dem Nutzer bei bekannten Fehlerarten (insbesondere `401`/Session abgelaufen) eine konkretere, handlungsleitende Meldung statt eines generischen Textes zeigen.
  - Completion criteria: Entschieden und dokumentiert ist, welche Frontend-Ereignisse wo geloggt werden (Konsole und/oder Versand ans Backend) und wie das mit dem bestehenden `DiagnosticsLog`-Konzept aus `TASK-024` zusammenpasst. Kein `catch {}` in `Wizard.tsx`/vergleichbaren Flows schluckt einen Fehler mehr stillschweigend. Ein abgelaufenes/ungültiges Token bei einem API-Aufruf führt zu einer für den Nutzer verständlichen, vom generischen Fehler unterscheidbaren Meldung (z. B. "Sitzung abgelaufen, bitte neu anmelden") statt der pauschalen "konnte nicht gestartet werden"-Meldung. Tests belegen das neue Verhalten.
  - Umsetzung (2026-09-13): Die Fehlerbehandlung ist in drei Kategorien geteilt: `401` löst einen erzwungenen Re-Login aus und wird nicht ans Backend geloggt; sonstige Backend-Fehler zeigen den echten Backend-Text; sonstige Frontend-Fehler werden fire-and-forget an `POST /api/v1/diagnostics/frontend-errors` gemeldet. Backend-seitig kamen `FrontendToolingError`, `ReportFrontendError` und der Diagnostics-Router hinzu. Frontend-seitig klassifiziert `toQueryError()` zentral, und `ErrorBanner` wird von Wizard, Library und Play verwendet. Die stillen `catch {}`-Blöcke sind entfernt. 547 Backend-Tests und 128 Frontend-Tests sowie Typecheck und Lint waren erfolgreich. Eine Verifikation mit tatsächlich abgelaufenem Token oder echtem Netzwerkfehler steht noch aus.
  - Resolution: Confirmed by the project owner on 2026-09-13.

- `TASK-031` **Gegenstände im Wizard-Review einer Figur zuordnen können**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-14.
  - Area: Web-Frontend (Wizard), API und Domainmodell.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Im Review-Schritt des Wizards kann ein vorgeschlagener Gegenstand aktuell nur entfernt werden ([Wizard.tsx:533-557](Frontend-Web/src/routes/Wizard/Wizard.tsx:533), `ItemDecisionState` in [wizardSlice.ts:24](Frontend-Web/src/features/wizard/wizardSlice.ts:24) kennt nur `removed`; ebenso serverseitig `ItemDecision` in [confirm_game_run_proposal.py:49](Backend/src/story_game/application/confirm_game_run_proposal.py:49)). Stattdessen soll jeder Gegenstand bei der Erstellung frei einer beliebigen vorgeschlagenen Figur (Spieler oder NPC) zugeordnet werden können, analog zur bestehenden Spieler/NPC-Rollenwahl bei Figuren ([Wizard.tsx:501-527](Frontend-Web/src/routes/Wizard/Wizard.tsx:501)). Zusätzlich wird eine neue Warnung eingeführt, wenn ein Gegenstand noch keiner Figur zugeordnet ist — diese Warnung darf frühestens erscheinen, nachdem der Nutzer die Rollenwahl der Figuren (Spieler/NPC) abgeschlossen hat, nicht schon vorher (z. B. nicht sofort beim Laden des Vorschlags oder während die Figuren noch unentschieden sind).
    - Ergänzung (2026-09-17): Ein Sonderfall der Zuordenbarkeit ist bislang nicht abgedeckt: Der Spielercharakter existiert als eigene vorgeschlagene Figur nur, wenn er im Story-Text explizit genannt/erwähnt wurde; wurde er nicht explizit genannt, gibt es zum Zeitpunkt des Reviews noch keine Figur-Entity für den Spieler, der ein Gegenstand zugeordnet werden könnte. Ohne Sonderbehandlung würde ein Gegenstand, der eigentlich dem Spieler gehören soll, in diesem Fall zwangsläufig unzugeordnet bleiben (und die neue Warnung auslösen), obwohl der Nutzer inhaltlich weiß, wem er gehört. Zu klären: ob/wie eine "Spieler"-Zuordnungsoption auch dann angeboten wird, wenn (noch) keine explizite Spielerfigur im Vorschlag existiert (z. B. durch implizites Anlegen der Spielerfigur bei Bedarf, oder durch eine generische "gehört dem Spieler"-Option unabhängig von der Figurenliste).
  - Completion criteria: `ItemDecision` (Frontend und Backend) trägt zusätzlich zu `removed` eine optionale Besitzer-Entity-ID; die Wizard-UI bietet pro Gegenstand eine Auswahl aus den nicht entfernten Figuren, analog zu den Chips der Charakter-Zuordnung. `ConfirmGameRunProposal` übernimmt die gewählte Zuordnung als `POSSESSES`-Beziehung im persistierten WorldState (siehe `RelationKind.POSSESSES` in [value_objects.py:88](Backend/src/story_game/domain/value_objects.py:88)); eine fehlende Zuordnung bleibt zulässig (Gegenstand ohne Besitzer bleibt möglich), löst aber die neue Warnung aus. Die Warnung erscheint nachweislich (Test) nicht, solange noch nicht jede Figur eine Spieler/NPC-Rolle zugewiesen bekommen hat, und erscheint danach für jeden noch nicht zugeordneten Gegenstand. Tests belegen Zuordnung, Warnung-Timing und die Übernahme der Besitzbeziehung im WorldState. Zusätzlich entschieden und getestet: Eine Zuordnung zum Spieler ist auch dann möglich, wenn der Spielercharakter im Vorschlag nicht als explizit genannte Figur vorkommt (kein Gegenstand bleibt allein aus diesem Grund zwangsweise unzugeordnet).

- `TASK-032` **Zusammenfassung als Kette statt rollierendem Ersatz**
  - Type: Task.
  - Status: Completed.
  - Parent: None.
  - Created: 2026-09-14.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-023`.
  - Goal: Die in `TASK-023` eingeführte "rollierende Zusammenfassung" ersetzt nach jedem Zug die bisherige Zusammenfassung vollständig durch eine neu erzeugte (siehe `StoryState`, das nur die *eine aktuelle* Zusammenfassung hält, und die in `b4ff9d4` neu verdrahtete Chronik-Anzeige in [Play.tsx](Frontend-Web/src/routes/Play/Play.tsx), die genau dieses eine `story.summary` zeigt). Das soll sich ändern: Statt die eine bestehende Zusammenfassung durch eine neu geschriebene zu überschreiben, soll je Zug (oder Zug-Batch) ein neuer, eigenständiger Zusammenfassungs-Abschnitt entstehen, der zu den bisherigen Abschnitten hinzukommt, statt sie zu ersetzen. Aneinandergereiht ergeben diese Abschnitte der Reihe nach die bisher gespielte Geschichte — explizit **keine** vom Modell laufend umgeschriebene Gesamtzusammenfassung, sondern eine fortlaufende Kette bereits fertiger, unveränderter Abschnitte.
  - Completion criteria: `StoryState` (oder ein neues Modell) hält eine geordnete Folge von Zusammenfassungs-Abschnitten statt einer einzelnen Zusammenfassung; ein abgeschlossener Zug hängt genau einen neuen Abschnitt an, bestehende Abschnitte werden nicht verändert. Entschieden und dokumentiert ist die Granularität (ein Abschnitt pro Zug oder pro Zug-Batch/Kapitel) und wie mit potenziell vielen Abschnitten über eine lange Spielzeit umgegangen wird (z. B. Anzeige/Prompt-Kontext-Budget), ohne dass das die Kettenstruktur selbst aufgibt. Die Chronik-Ansicht im Frontend zeigt die Abschnitte in Reihenfolge (Ersatz für die bisherige Einzeltext-Anzeige aus `b4ff9d4`). Tests belegen, dass ein neuer Zug bestehende Abschnitte unverändert lässt und dass die Abschnittsfolge in Erzeugungsreihenfolge sortiert bleibt.
  - Umsetzung (2026-09-15): `StorySummary` wurde zu `StorySummarySegment` mit `from_sequence`/`through_sequence` ([story.py](Backend/src/story_game/domain/story.py)); `StoryState.summaries: tuple[StorySummarySegment, ...]` ersetzt das Einzelfeld, `add_turn()` hängt an statt zu ersetzen, neue Invariante erzwingt eine lückenlose Abschnittsfolge. Zwei bewusst getrennte, über `configs/app.toml` (`[story_summary]`) konfigurierbare Werte: `interval` (Default 4) — alle wie viele Züge ein neuer Abschnitt entsteht; das seltene, gebatchte `SummarizeStory`, aufgerufen nur an der Intervallgrenze, bekommt ausschließlich die eigenen Fenster-Züge (nicht mehr die alte Zusammenfassung — `previous_summary` entfällt komplett), so bleibt der Aufruf unabhängig von der Spieldauer. `context_segment_count` (Default 3, `SelectionBudget.summary_segment_count`) bestimmt, wie viele der jüngsten Abschnitte der günstige Pro-Zug-Erzählkontext bekommt; die unabhängige `recent_turn_count=2` blieb unverändert. Persistenz: neue Tabelle `story_summary_segments` (Migration `005_story_summary_segments.sql`), reines Append, alte `summary_*`-Spalten auf `story_state_metadata` entfernt. API/Frontend: `summary` → `summaries`-Liste durchgängig bis zur Chronik-Ansicht in [Play.tsx](Frontend-Web/src/routes/Play/Play.tsx), die jetzt alle Abschnitte rendert. Die aktuellen Repository-Werte überschreiben die Defaults: `interval = 1` und `context_segment_count = 2` in `Backend/configs/app.toml`. 552 Backend-Tests grün (`cd Backend && pytest`; ein unabhängiger Fehlschlag in `test_llm.py` wegen einer bestehenden `configs/llm.toml`-Abweichung bleibt offen), 129 Frontend-Tests grün, Typecheck und Lint fehlerfrei. Nicht live gegen LM Studio/Postgres verifiziert.
  - Resolution: Confirmed by the project owner on 2026-09-21.

- `TASK-033` **Vorgeschlagene Fortsetzungsoptionen je Zug erzeugen (Backend/API)**
  - Type: Task.
  - Status: Completed.
  - Parent: None.
  - Created: 2026-09-15.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: Sowohl `GenerateStory`/`StoryGenerationData` (reguläre Züge, [generate_story.py](Backend/src/story_game/application/generate_story.py)) als auch `GenerateInitialStoryState`/`InitialStoryText` (Story-Initialisierung/Eröffnung, [story_initialization.py](Backend/src/story_game/application/story_initialization.py)) werden um ein neues strukturiertes Feld für 3-4 kurze, unterschiedliche Fortsetzungsvorschläge erweitert — ein Feld je bestehendem LLM-Call, kein zusätzlicher Aufruf. Die Optionen werden immer geliefert (keine Optional-Logik; die UI entscheidet über die Anzeige), sind transient (analog `ProposedChangeSet`, nicht in `StoryTurn`/`GameState`/DB persistiert — nur der letztlich gewählte/eingegebene Text landet wie bisher als `player_input`) und erscheinen bereits ab dem allerersten Zug, also inklusive der Eröffnung vor dem ersten regulären `PlayStoryTurn`. Aktuell liefern beide Contracts ([llm/contracts.py](Backend/src/story_game/application/llm/contracts.py), `StoryGenerationData` nur `text`, `InitialStoryText` nur `text`) reinen Fließtext ohne Schema, anders als die Extraktion.
  - Completion criteria: `StoryGenerationRequest`/`-Data` und `StoryInitializationRequest`/`InitialStoryText` ([llm/contracts.py](Backend/src/story_game/application/llm/contracts.py)) tragen je ein neues `continuation_options: tuple[str, ...]`-Feld. Die Prompt-Tasks `story_generation` und `story_initialization` ([story.base/1.toml](Backend/prompts/story.base/1.toml)) weisen das Modell entsprechend an. Alle drei Provider-Wires (LM Studio/`openai_compatible`, Gemini, Groq — siehe [story_generation_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_generation_wire.py)) liefern das Feld strukturiert per JSON-Schema statt es aus Fließtext zu parsen, analog `turn_extraction_wire.py`/`json_schema.py::strict_json_schema()`. `PlayedStoryTurn` ([play_story_turn.py](Backend/src/story_game/application/play_story_turn.py)) und das Ergebnis von `InitializeStory`/`ProposeGameRun` tragen die Optionen transient weiter; die API-Antwortschemas (`TurnResult` für reguläre Züge, `RunProposalModel` für die Eröffnung, [schemas/runs.py](Backend/src/story_game/api/schemas/runs.py)) exponieren sie, ohne sie in persistierten Modellen (`StoryTurnModel`, `GameState`) zu führen. Die notwendige Amendment von `.harness/architecture/llm-integration.md` §5 ("A successful Story-generation result MUST contain normalized story prose.") ist vom Projekt-Owner freigegeben, bevor der neue, transiente, nicht-kanonische Optionsvertrag umgesetzt wird. Tests belegen Schema, Wire-Mapping (Mock) und Prompt-Vertrag für beide Call-Typen (Initialisierung und regulärer Zug).
  - Umsetzung (2026-09-17): `§5`/`§5a` von `llm-integration.md` um den transienten Optionssatz ergänzt. `StoryGenerationData`/`InitialStoryText` tragen `continuation_options: tuple[str, ...]` (mindestens ein Eintrag, sonst `ValueError`). Für die Eröffnung ein neues transientes Trägerobjekt `GeneratedStoryOpening` (in [story_initialization.py](Backend/src/story_game/application/story_initialization.py), `story_state` + `continuation_options`), da `StoryState` selbst frei von nicht-kanonischen Daten bleiben muss; von dort durchgereicht über `InitializedStory` → `GameRunProposal` (nicht in `CachedGameRunProposal`, das nur bis zum Bestätigen lebt und die Optionen nie wieder braucht). Für reguläre Züge genügt ein einzelnes neues Feld auf dem bereits transienten `PlayedStoryTurn`. Beide LLM-Wires ([story_generation_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_generation_wire.py), [story_initialization_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_initialization_wire.py)) nutzen jetzt striktes JSON-Schema-Output statt Fließtext, über ein gemeinsames `WireNarrationWithOptions`-Modell (neu: [narration_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/narration_wire.py)) statt zweier identischer Klassen; das Schema wird einmalig pro Modul gebaut, nicht pro Aufruf. API-seitig bündelt ein neues gemeinsames `ContinuationModel` (`narration` + `options`) Prosa und Optionen explizit an einer Stelle in `TurnResultModel` und `RunProposalModel` ([schemas/runs.py](Backend/src/story_game/api/schemas/runs.py)) — `RunProposalModel.opening_narration` entfällt dafür bewusst (Breaking Change; das bestehende Wizard-Frontend, das dieses Feld noch liest, braucht einen eigenen Folge-Task, siehe unten). `docs/human/technical/api.md` auf das neue Antwortformat aktualisiert. 575 Backend-Tests grün (`cd Backend && pytest`; derselbe einzelne, unabhängige `test_llm.py`-Fehlschlag wie bei TASK-032 bleibt offen), inklusive neuer Wire-Level-Tests (`test_story_generation_wire.py`, `test_story_initialization_wire.py`) und aktualisierter Application-/Adapter-/API-Tests. Nicht live gegen LM Studio/Gemini/Groq verifiziert (nur automatisierte Tests mit Mocks/Doubles) — insbesondere nicht geprüft, ob jeder Provider striktes `response_format.json_schema` tatsächlich zuverlässig einhält. Offen/zu entscheiden: `continuation_options` ist aktuell hart nicht-leer validiert (passend zu "immer liefern"), was strenger ist als die Architektur-Formulierung "MAY also contain" — falls ein Modell legitim eine Erzählung ohne sinnvolle Fortsetzungsoptionen liefert (z. B. ein Enden-Beat), schlägt aktuell der ganze Aufruf fehl statt nur die Optionen leer zu lassen.
  - Resolution: Confirmed by the project owner on 2026-09-21.

- `TASK-034` **Vorgeschlagene Fortsetzungsoptionen als zweistufige Chips anzeigen (Frontend)**
  - Type: Task.
  - Status: Completed.
  - Parent: None.
  - Created: 2026-09-17.
  - Area: Web-Frontend.
  - Priority: Wichtig.
  - Dependencies: `TASK-033`.
  - Goal: Die Play-UI ([Play.tsx](Frontend-Web/src/routes/Play/Play.tsx)) zeigt die von `TASK-033` gelieferten Fortsetzungsoptionen als klickbare Chips neben dem bestehenden Freitextfeld an. Zweistufiges Klickverhalten: ein erster Klick auf eine Option übernimmt ihren Text in das Freitextfeld (weiterhin frei editierbar), ein zweiter Klick auf dieselbe, jetzt aktive Option löst das Absenden aus (wie der bestehende Absende-Button/`handleSubmitTurn`). Das ergänzt die Freitexteingabe, ersetzt sie nicht. Zusätzlich, als Vorbedingung: `TASK-033` hat `RunProposalModel.opening_narration` durch `continuation.narration` ersetzt (Breaking Change); der bestehende Wizard-Flow ([wizardSlice.ts](Frontend-Web/src/features/wizard/wizardSlice.ts), [types.ts](Frontend-Web/src/api/types.ts)) liest noch das alte flache Feld und muss auf `continuation.narration` umgestellt werden, sonst liest der Wizard nach dem Backend-Deploy `undefined` statt der Eröffnungserzählung.
  - Completion criteria: Chips (`Chip`-Komponente, [Chip.tsx](Frontend-Web/src/components/Chip/Chip.tsx)) rendern aus `continuation.options` der `playTurn`-Antwort. Ein aktiver/ausgewählter Zustand einer Option ist visuell erkennbar (`aria-pressed`). Erster Klick befüllt den `input`-State; zweiter Klick auf die aktive Option ruft `handleSubmitTurn`/`usePlayTurnMutation` auf. Klick auf eine andere Option, während bereits eine aktiv ist, ersetzt Feldinhalt und aktive Auswahl statt direkt abzusenden. Manuelles Editieren des Freitextfelds bleibt jederzeit möglich und deaktiviert eine zuvor aktive Option. Tests (Vitest/RTL) belegen das zweistufige Klickverhalten. `wizardSlice.ts`/`types.ts` (und alle weiteren Konsumenten von `RunProposalModel`/`TurnResultModel`) lesen `continuation.narration`/`continuation.options` statt des entfernten `opening_narration`; bestehende Wizard-Tests, die noch die alte Feldform fabrizieren (`apiSlice.test.ts`, `Wizard.test.tsx`), sind entsprechend angepasst. Bewusst ausgeklammert: Chips bei der allerersten Eröffnung — `GameDocument` (aus `loadRun`/`startPlaythrough`, das, was der Play-Screen beim initialen Laden erhält) liefert keine `continuation.options`; dieses Feld existiert nur in `RunProposalModel` (vor Bestätigung im Wizard) und `TurnResultModel` (nach einem gespielten Zug). Chips erscheinen daher erst ab dem ersten gespielten Zug; Eröffnungs-Chips wären ein separater Folge-Task (Backend-Erweiterung von `startPlaythrough`/`GameDocument`).
  - Resolution: Confirmed by the project owner on 2026-09-17. Scope reduced during planning: opening-turn chips deferred (see completion criteria) because `GameDocument` doesn't carry continuation options; implemented and merged into `development` (commit `17c444d`, merge commit in `development`), 133/133 frontend tests, typecheck and lint pass.

- `TASK-035` **Turn-Chronik im Zustand paginieren statt vollständig zu laden**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-17.
  - Area: API und Web-Frontend (Play).
  - Priority: Wichtig.
  - Dependencies: None.
  - Goal: `GameStateModel`/`StoryStateModel.turns` ([state.py:36-37](Backend/src/story_game/api/schemas/state.py:36)) liefert aktuell bei jedem Laden des Zustands (initiales `GET /api/v1/runs/{run_id}` sowie das im `TurnResultModel` eingebettete `state` nach `POST /api/v1/runs/{run_id}/turns`, [runs.py:134-148](Backend/src/story_game/api/schemas/runs.py:134)) die vollständige Turn-Liste seit Spielbeginn. Das soll durch dynamisches Nachladen ersetzt werden: standardmäßig nur die letzten N Turns (z. B. 3), mit einer Möglichkeit für die Play-Chronik-Ansicht ([Play.tsx](Frontend-Web/src/routes/Play/Play.tsx)), beim Scrollen ältere Turns zusätzlich nachzuladen. Zu klären ist außerdem, ob `POST .../turns` weiterhin den vollständigen `state` zurückgeben soll oder nur noch Erfolg/Fehler meldet, woraufhin das Frontend den (dann paginierten) Zustand separat über den GET-Pfad nachlädt — das würde das Nachladen beim Scrollen und das initiale Laden auf denselben Mechanismus vereinheitlichen, ändert aber das bestehende `TurnResultModel`-Vertrag und dessen Konsumenten.
  - Completion criteria: Entschieden und dokumentiert ist, (1) ob und wie ein Turn-Pagination-Parameter am GET-Endpunkt aussieht (Cursor oder Offset, Seitengröße, Sortierrichtung), (2) ob `POST .../turns` weiterhin den vollständigen `state` liefert oder auf Erfolg/Fehler reduziert wird, und (3) wie das mit der bereits abschnittsweisen `story.summaries`-Kette aus `TASK-032` zusammenspielt (Zusammenfassungsabschnitte sind bereits kompakt und müssten von einer Turn-Pagination nicht zwingend betroffen sein). Nach Umsetzung: Ein Laden des Zustands überträgt nicht mehr sämtliche Turns seit Spielbeginn; die Play-Chronik kann ältere Turns bei Bedarf nachladen (z. B. beim Scrollen ans obere Ende); bestehende Turn-Reihenfolge und lückenlose Sequenznummern bleiben für den Client nachvollziehbar. Tests belegen Pagination-Verhalten (Grenzen, leere/kurze Chronik, Nachladen) sowohl API- als auch frontendseitig.

- `TASK-036` **Leere `continuation_options` zulassen statt den ganzen LLM-Call scheitern zu lassen**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-21.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-033`.
  - Goal: `TASK-033` validiert `continuation_options` in `StoryGenerationData` und `InitialStoryText` ([llm/contracts.py](Backend/src/story_game/application/llm/contracts.py)) hart als nicht-leer (`ValueError` bei leerem Tupel). Das ist strenger als die zugehörige Architekturregel in `.harness/architecture/llm-integration.md` §5/§5a, die den Optionssatz nur als "MAY also contain" führt. Liefert ein Modell legitim eine Erzählung ohne sinnvolle Fortsetzungsoptionen — etwa einen Ende-Beat oder eine Szene ohne echte Handlungsalternativen —, scheitert dadurch der gesamte Zug, statt lediglich ohne Optionen auszukommen. Zu entscheiden und umzusetzen ist, ob ein leerer Optionssatz auf Contract-Ebene zulässig wird und wie sich API und Play-UI ([Play.tsx](Frontend-Web/src/routes/Play/Play.tsx), Chip-Anzeige aus `TASK-034`) in diesem Fall verhalten.
  - Completion criteria: Entschieden und dokumentiert ist, ob `continuation_options` leer sein darf und ob Contract und Architekturregel (§5/§5a) danach übereinstimmen. Falls leer zulässig: Die Validierung in den Contracts und den Provider-Wires ([narration_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/narration_wire.py)) lässt ein leeres Tupel zu, ohne den Erzähl-Call fehlschlagen zu lassen; die API-Schemas (`ContinuationModel` in [schemas/runs.py](Backend/src/story_game/api/schemas/runs.py)) übertragen eine leere Liste; die Play-UI rendert in diesem Fall schlicht keine Chips und bleibt über das Freitextfeld voll bedienbar. Tests belegen den leeren Fall auf Contract-, Wire-, API- und Frontend-Ebene.

- `TASK-037` **Strikte JSON-Schema-Ausgabe der Erzähl-Calls live gegen alle drei Provider verifizieren**
  - Type: Task.
  - Status: Open.
  - Parent: None.
  - Created: 2026-09-21.
  - Area: Story-Workflow und LLM-Integration.
  - Priority: Wichtig.
  - Dependencies: `TASK-033`.
  - Goal: `TASK-033` hat `story_generation` und `story_initialization` von Fließtext auf striktes `response_format.json_schema` umgestellt ([narration_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/narration_wire.py), [story_generation_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_generation_wire.py), [story_initialization_wire.py](Backend/src/story_game/infrastructure/llm/openai_compatible/story_initialization_wire.py)). Verifiziert wurde das bisher ausschließlich mit Mocks und Doubles — ob LM Studio (`openai_compatible`), Gemini und Groq das strikte Schema real zuverlässig einhalten, ist offen. Gerade bei Groq und Gemini ist die Schema-Treue erfahrungsgemäß das Risiko, und ein Verstoß träfe jeden Zug, nicht nur Randfälle.
  - Completion criteria: Für alle drei Provider ist mit echten Aufrufen belegt, dass Erzählung und `continuation_options` schemakonform zurückkommen; abweichendes Verhalten je Provider ist dokumentiert und, wo nötig, im jeweiligen Wire behandelt (z. B. Fallback oder provider-spezifische Schema-Formulierung). Die Live-Prüfung ist als ausführbarer, standardmäßig übersprungener Test hinterlegt, analog zu den bestehenden `--run-lmstudio-live`-Tests.
