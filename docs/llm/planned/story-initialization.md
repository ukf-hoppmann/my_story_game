# Story-Initialisierung: Vertrag und konkreter Umsetzungsplan

Status: `GenerateInitialStoryState` ist ohne Spielercharakter- und Modusregeln
implementiert. Die folgende Planung erweitert STORY-008 um diese Regeln und
setzt anschließend STORY-009 als initiale WorldState-Extraction um. Persistenz,
HTTP-API und der erste reguläre Spielzug bleiben außerhalb dieses Increments.

## Verbindliche Entscheidungen

- Story-Erzeugung und WorldState-Extraction bleiben getrennte, task-spezifische
  Modellprozesse unter einer übergeordneten Application-Orchestrierung.
- Player Mode besitzt genau einen vom User angelegten Spielercharakter.
- Director Mode besitzt keinen Spielercharakter und dirigiert Szene oder Cast.
- First und Second Person sind mit Director Mode ungültig.
- Third Person mit Player Mode ist weiterhin Singleplayer; Multiplayer bleibt
  eine spätere eigene Kontrollzuordnung.
- `player_agency` wirkt nur im Player Mode.
- Das Modell darf in jeder Perspektive null bis beliebig viele weitere
  Charaktere extrahieren, aber niemals den Spielercharakter selbst.
- Eröffnungsprosa ist der Goldstandard für die initiale Extraction. Der
  ursprüngliche Initialprompt und Story-Kategorien wie Genre oder Ton werden
  nicht an den Extraction-Aufruf gegeben.
- Initiale Modellkandidaten enthalten nur Entitäten, Beziehungen und Fakten.
- Knowledge, Weltregeln und Goals bleiben leer. Sichtbarkeit wird nicht vom
  Modell bestimmt.
- Evidenz darf später transient einen Review unterstützen, wird aber aus
  kanonischen Facts, WorldRules, API und Persistenz entfernt.
- Die Übernahme ist all-or-nothing, ohne automatischen Retry oder Persistenz.
- Extraction verwendet zunächst `temperature = 0.1` und
  `max_output_tokens = None`.

## Zielablauf

```text
InitializeStory.apply(request)
    -> Initialisierungsregeln validieren
    -> GenerateInitialStoryState.apply(request)
        -> StoryInitializationPort.generate(call)
        -> StoryState
    -> ExtractInitialWorldState.apply(story_state, configuration, player_character)
        -> InitialWorldExtractionPort.extract(call)
        -> WorldInitializationCandidate
        -> lokale Referenzen und Domain-Invarianten validieren
        -> WorldState
    -> InitializedStory(story_state, world_state)
```

Jeder Fehler beendet den Ablauf. Es entsteht kein teilweise zurückgegebenes
Gesamtergebnis und keine Persistenz.

## Geplante Application-Verträge

Die endgültige Benennung darf sich bei der Implementierung nur ändern, wenn die
Verantwortung unverändert bleibt.

```text
PlayerCharacterSeed
    name: str
    description: str = ""

InitializeStoryRequest
    configuration: GameConfiguration
    initial_prompt: str
    player_character: PlayerCharacterSeed | None

InitializedStory
    story_state: StoryState
    world_state: WorldState

GenerateInitialStoryStateRequest
    configuration: GameConfiguration
    initial_prompt: str
    player_character: PlayerCharacterSeed | None

ExtractInitialWorldStateRequest
    configuration: GameConfiguration
    story_state: StoryState
    player_character: PlayerCharacterSeed | None
```

Ein gemeinsamer, Application-eigener Initialisierungsfehler unterscheidet
mindestens:

```text
invalid_configuration
missing_player_character
unexpected_player_character
model_failure
invalid_model_response
invalid_candidate_reference
domain_rejection
```

Ein `model_failure` behält den ursprünglichen providerneutralen `LLMError` als
Cause, damit Timeouts, Unerreichbarkeit oder abgeschnittene Antworten nicht
verschleiert werden.

## Perspective-/Control-Policy

Die Policy wird vor jedem Modellaufruf geprüft:

```text
control_mode == player
    -> genau ein PlayerCharacterSeed

control_mode == director
    -> kein PlayerCharacterSeed

perspective in {first_person, second_person}
    -> control_mode muss player sein

perspective in {third_person_limited, third_person_omniscient}
    -> player oder director
```

Unbekannte Option-IDs bleiben Fehler des bestehenden Promptpaket-Resolvers.
Eine ungültige bekannte Kombination löst einen Initialisierungsfehler aus und
ruft weder Story- noch Extraction-Modell auf.

Die gespeicherte GameConfiguration behält vorerst ein vollständiges
`player_agency`-Feld. Die aufgabenspezifische Promptprojektion lässt diese
Kategorie im Director Mode aus. Derselbe Filter muss für Story-Initialisierung
und spätere reguläre Story Generation gelten, damit ihre Semantik nicht
auseinanderläuft.

## Story-Initialisierungsrequest

Der bestehende Request wird um den vom User festgelegten Charakterkontext
erweitert:

```text
StoryInitializationRequest
    system_prompts
    configuration
    initial_prompt
    player_character: prepared character context | None
```

Der Adapter rendert den Charakter in einer eigenen benannten Sektion. Er darf
keinen Charakter aus dem Initialprompt ableiten. Der Story-Prompt muss den Namen
und die optionale Beschreibung respektieren und darf sie nicht eigenmächtig
ersetzen.

## Initial-Extraction-Request

```text
InitialWorldExtractionRequest
    system_prompts
    opening_narration
    language
    perspective
    control_mode
    player_character: known character context | None
```

Nicht vorhanden sind:

- ursprünglicher Initialprompt;
- vorhandener WorldState;
- Story-Promptprofil außer den ausdrücklich benötigten Moduswerten;
- Genre, Ton, Prosa-Stil und narrative Konventionen;
- persistierte IDs.

Der Adapter ergänzt das technische JSON-Response-Schema. Die Application-
Datentypen definieren dessen fachliche Bedeutung; providerabhängige
`response_format`-Darstellung bleibt im LM-Studio-Adapter und -Client.

## Candidate-Schema

```text
WorldInitializationCandidate
    entities: tuple[CandidateEntity, ...]
    links: tuple[CandidateLink, ...]
    facts: tuple[CandidateFact, ...]

CandidateEntity
    local_ref: str
    kind: EntityKind
    label: str
    description: str = ""
    conditions: tuple[CandidateCondition, ...] = ()
    aliases: tuple[str, ...] = ()

CandidateLink
    source_ref: str
    target_ref: str
    kind: RelationKind
    quantity: int | None = None
    description: str = ""

CandidateFact
    statement: str
    subject_ref: str | None = None
```

Das Schema enthält bewusst keine Felder für:

- StableIds;
- ActorRole;
- Spielercharakter;
- Visibility;
- Evidence;
- KnowledgeEntry;
- WorldRule;
- Goal;
- Confidence oder Uncertainty.

Eine Entität vom Typ `character` wird durch die Application zu einem neutralen
Akteur. Andere Entitätstypen erhalten in diesem Increment kein ActorProfile.

## Lokale Referenzen und ID-Erzeugung

`player_character` ist eine reservierte lokale Referenz und existiert nur im
Player Mode. Links und Facts dürfen sie verwenden; das Candidate-Entity-Array
darf sie nicht definieren.

Die Application:

1. normalisiert und prüft alle lokalen Entity-Referenzen auf Eindeutigkeit;
2. weist die reservierte Referenz im Director Mode zurück;
3. weist eine exakte, case-insensitive Namens- oder Aliasduplikation des
   Spielercharakters zurück;
4. erzeugt die Spielerentität im Player Mode selbst;
5. erzeugt StableIds über eine injizierbare ID-Factory;
6. löst Source-, Target- und Subject-Referenzen vollständig auf;
7. baut erst danach `WorldEntity`, `EntityLink`, `Fact` und `WorldState`.

Ein unbekannter oder mehrdeutiger Verweis verwirft den gesamten Candidate. Es
gibt keinen partiellen Fallback. Eine semantische Spielerduplikation unter
völlig anderer Bezeichnung bleibt ein bekanntes, im Live-Test zu beobachtendes
Modellrisiko.

## Persistierter WorldState-Vertrag

Evidenz wird vor der Candidate-Übernahme geschlossen aus dem kanonischen
Vertrag entfernt:

- `Fact` und `WorldRule` besitzen kein Evidence-Feld mehr;
- API-Modelle und Mapper führen kein Evidence-Feld mehr;
- die bestehende PostgreSQL-Initialmigration wird direkt ohne Evidence-Spalten
  definiert;
- es gibt in der frühen Entwicklungsphase keine Upgrade-Migration und keine
  Rückwärtskompatibilität für bereits angelegte Entwicklungsdatenbanken;
- vorhandene Entwicklungsdatenbanken müssen bewusst neu angelegt werden;
- transiente Review-Evidenz erhält einen Application-eigenen Typ und bleibt
  außerhalb des GameState.

Die Implementierung darf keine bestehende User-Datenbank automatisch löschen.
Das notwendige Neuerstellen einer lokalen Entwicklungsdatenbank bleibt eine
separate, ausdrücklich auszulösende Operation.

Visibility bleibt dagegen im Domain-, API- und Persistenzvertrag erhalten. Die
Initial-Extraction gibt sie nicht aus; der Builder verwendet
`Visibility.public()`. Knowledge, Rules und Goals bleiben als bestehende
WorldState-Fähigkeiten erhalten, werden initial aber leer aufgebaut.

## LM-Studio-Structured-Output

Der vorhandene Transport kennt bisher nur Textantworten. Die Umsetzung ergänzt:

- einen optionalen, typisierten JSON-Schema-Teil im internen
  `LmStudioChatRequest`;
- OpenAI-kompatibles `response_format` im technischen Client-Payload;
- ein strikt geschlossenes Schema für den Initial-Candidate;
- JSON-Parsing und strukturelle Validierung im Initial-Extraction-Adapter;
- Mapping in Application-Candidate-Dataclasses;
- unveränderte Fehlerübersetzung für Transportprobleme;
- `INVALID_RESPONSE` für leeres, abgeschnittenes, nicht parsebares oder nicht
  schema-konformes Modelloutput.

Story-Textadapter bleiben unverändert textbasiert. Die Structured-Output-
Erweiterung darf nicht zu einem untypisierten Universal-LLM-Service führen.

## Kleine Umsetzungs-Subtasks

### 1. PlayerCharacterSeed und Modusvertrag ergänzen

- Ziel: STORY-008 akzeptiert nur fachlich gültige Perspective-/Control-
  Kombinationen und gibt dem Story-Modell den vom User angelegten Charakter.
- Scope: Application-Input und Fehler, Promptprojektion, Director-Prompt,
  StoryInitializationRequest, LM-Studio-Initialisierungsadapter und Tests.
- Nicht-Ziele: Keine WorldState-Extraction, keine Persistenz und keine UI.
- Kontext: Player Mode hat genau eine Spielerfigur; Director Mode keine;
  `player_agency` gilt nur im Player Mode.
- Abhängigkeiten: Bestehendes STORY-008 und Promptpaket.
- Akzeptanz: Ungültige Kombinationen und fehlende beziehungsweise unerwartete
  Seeds scheitern vor dem Modellaufruf; gültige Player-Aufrufe enthalten den
  Seed; Director-Aufrufe enthalten weder Seed noch Player-Agency-Anweisung.
- Verifikation: Application-Parametertests für alle acht Kombinationen,
  Promptresolver- und Adaptertests sowie angepasster Live-Test-Input.
- Abschluss: STORY-008 kann keinen gültigen Player-Start ohne Usercharakter und
  keinen Director-Start mit Spielercharakter erzeugen.

### 2. Kanonische Evidenz entfernen

- Ziel: Persistierte Facts und WorldRules enthalten keine ungenutzte
  Herkunftsinformation; Review-Evidenz bleibt ausschließlich transient.
- Scope: Domainwerte und Exporte, ProposedChange-Typ, API-Schemas und Mapper,
  PostgreSQL-Migration, Reader/Writer/Row-Mapping, Fixtures und Dokumentation.
- Nicht-Ziele: Keine Entfernung von Visibility, Knowledge, Rules oder Goals und
  kein Review-Workflow.
- Kontext: Der Initial-Candidate wird ohne Evidence erzeugt; die
  Initialmigration wird direkt geändert und bestehende Entwicklungsdatenbanken
  werden nicht automatisch migriert.
- Abhängigkeiten: Bestehende Domain-, API- und PostgreSQL-Verträge.
- Akzeptanz: Facts und Rules können ohne Evidence erstellt, über API gemappt und
  über PostgreSQL round-trip geladen werden; ProposedChange kann weiterhin eine
  transiente Application-Evidenz tragen; das Endschema enthält keine
  Evidence-Spalten.
- Verifikation: Domain-, API-, Mapper-, Migrations- und PostgreSQL-
  Integrationstests einschließlich Schema-Assertion.
- Abschluss: Kein kanonischer oder persistierter Pfad verlangt oder liefert
  Evidence.

### 3. Typisierten Initial-Extraction-Port und Structured Output implementieren

- Ziel: Ein providerneutraler Port liefert ausschließlich einen strukturell
  validierten `WorldInitializationCandidate`.
- Scope: Candidate-Dataclasses, InitialWorldExtractionRequest und Port,
  Extraction-Promptauswahl, JSON-Schema, LM-Studio-Wiremodell, Client und
  Adapter.
- Nicht-Ziele: Noch kein WorldState-Build, keine fachliche Referenzprüfung und
  kein Retry.
- Kontext: Adapter verantwortet Providerformat, JSON-Parsing und Schema;
  Application-Vertrag verantwortet die fachliche Ergebnisform.
- Abhängigkeiten: Subtask 1 für Modus-/Charakterkontext.
- Akzeptanz: Der Request enthält keine verbotenen Storyfelder; das Schema
  erlaubt nur Entities, Links und Facts; technisch ungültige Antworten werden
  als sichtbarer `INVALID_RESPONSE` zurückgegeben; Rohantworten überschreiten
  den Port nicht.
- Verifikation: Contract-, Client- und Adaptertests für Payload, Erfolg,
  unbekannte Felder, falsche Typen, ungültige Enums, leeres JSON, Text statt
  JSON, Abbruch und Providerfehler.
- Abschluss: Der Port ist mit Testdouble vollständig ohne echten Provider
  testbar.

### 4. Candidate all-or-nothing in WorldState überführen

- Ziel: Aus dem typisierten Candidate und dem vertrauenswürdigen
  PlayerCharacterSeed genau einen vollständigen transienten WorldState bauen.
- Scope: `ExtractInitialWorldState`, ID-Factory, Referenzauflösung,
  Spielerentität, neutrale Charaktere, Domain-Mapping und Application-Fehler.
- Nicht-Ziele: Keine Orchestrierung mit Story-Erzeugung, keine Persistenz und
  keine semantische Zweitbewertung durch ein Modell.
- Kontext: `player_character` ist reserviert; Visibility nutzt den technischen
  Public-Default; Knowledge, Rules und Goals bleiben leer.
- Abhängigkeiten: Subtasks 2 und 3.
- Akzeptanz: Leere Candidates sind im Director Mode gültig; Player Mode enthält
  immer die Application-erzeugte Spielerentität; optionale Nichtspielerfiguren
  funktionieren auch in First Person; jede ungültige Referenz, Duplikation oder
  Domain-Invariante verwirft den gesamten Candidate.
- Verifikation: Deterministische Application-Tests mit injizierten IDs für
  erfolgreiche Minimalzustände, alle Referenzarten, reservierte Referenz,
  exakte Spielerduplikation, Link-Invarianten und leere Zusatzbereiche.
- Abschluss: Erfolg liefert einen validen WorldState; kein Fehlerpfad liefert
  einen partiellen Zustand.

### 5. Übergeordnete Story-Initialisierung orchestrieren

- Ziel: StoryState und WorldState als zwei getrennte Prozesse unter einer
  sichtbaren Application-Operation gemeinsam erzeugen.
- Scope: `InitializeStory`, Request/Result, Fehlerweitergabe und Composition.
- Nicht-Ziele: Kein GameRun, keine Revision 1, kein Repositoryzugriff und kein
  HTTP-Endpunkt.
- Kontext: Der gleiche Seed und die gleiche validierte Konfiguration stehen
  beiden Operationen zur Verfügung; der Initialprompt geht nur an die
  Story-Erzeugung.
- Abhängigkeiten: Subtasks 1 und 4.
- Akzeptanz: Extraction startet nur nach erfolgreicher Story-Erzeugung; jeder
  Stage-Fehler identifiziert seine Ursache; Erfolg enthält genau einen
  StoryState und WorldState; kein Port persistiert.
- Verifikation: Workflowtests mit aufzeichnenden Testdoubles für Reihenfolge,
  Inputs, Short-Circuiting und erfolgreichen Gesamtoutput; Architekturtest für
  Port- und Abhängigkeitsrichtung.
- Abschluss: Der transiente zweistufige Initialisierungsworkflow ist unabhängig
  von LM Studio und PostgreSQL testbar.

### 6. Expliziten Live-Test und Gesamtintegration abschließen

- Ziel: Beide realen LM-Studio-Aufrufe nachvollziehbar manuell bewerten und das
  gesamte Increment reproduzierbar verifizieren.
- Scope: Opt-in Live-Test, ausschließlich testlokale Diagnoseausgabe,
  Extraction-Laufzeitkonfiguration, Dokumentation und vollständige Harness-
  Verifikation.
- Nicht-Ziele: Kein Diagnoserunner im Produktcode, kein automatischer Retry und
  keine Persistenz.
- Kontext: Standardtests müssen den Live-Test sicher überspringen; der aktuelle
  Zielbranch enthält einen auskommentierten Opt-in-Guard, der vor
  Standardverifikation wiederhergestellt werden muss. Danach muss der Test
  separat mit Flag tatsächlich gegen das lokale LM Studio ausgeführt werden.
- Abhängigkeiten: Subtask 5 und lokal bewusst gestartetes LM Studio für die
  manuelle Prüfung.
- Akzeptanz: Der Test verwendet einen PlayerCharacterSeed, druckt beide exakten
  Requests einschließlich Modell, Optionen und JSON-Schema, beide Antworten
  sowie StoryState und WorldState; Extraction löst `temperature=0.1` und kein
  Tokenlimit auf; ohne Flag erfolgt kein externer Aufruf.
- Verifikation: Offline-Harnessprofil für alle deterministischen Tests; separat
  aktivierter Live-Test mit `pytest -s`, der erfolgreich durchlaufen muss;
  Request, Response und eventuelle Modellmängel werden ehrlich berichtet. Ein
  Skip zählt nicht als Live-Verifikation.
- Abschluss: Deterministische Gesamtverifikation besteht und der Live-Pfad ist
  für eine bewusste menschliche Beurteilung ausführbar.

## Integrationsschritt

Nach allen Subtasks muss ein gemeinsamer Integrationslauf das ursprüngliche
Ziel prüfen:

```text
GameConfiguration + Initialprompt + optionaler/erforderlicher Seed
    -> StoryState
    -> WorldInitializationCandidate
    -> WorldState
```

Der Lauf muss bestätigen, dass weder Originalprompt noch Storyprofil in den
Extraction-Request gelangen, der Spielercharakter nicht vom Modell stammt,
Knowledge/Rules/Goals leer bleiben, Fehler keine Teilzustände erzeugen und kein
GameRun persistiert wird.

## Bewusst spätere Arbeiten

- UI-Erzwingung und Darstellung der Modusregeln;
- Multiplayer und Zuordnung mehrerer User zu Figuren;
- sichtbarkeitsabhängige UI- oder Promptlogik;
- akteursspezifisches Wissen und ein sinnvoller Initialzeitpunkt;
- Weltregeln für stärker regelorientiertes Pen-and-Paper-Spiel;
- Haupt- und Nebenquests aus späteren Turn-Extractions;
- semantische Zweitbewertung, Review-UI oder automatische Retries;
- atomare Persistenz von GameRun und GameState in STORY-010.
