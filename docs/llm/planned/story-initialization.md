# Story-Initialisierung: LLM-Vertrag und Umsetzungsplan

Status: Geplant. Phase 1 erzeugt ausschließlich einen transienten StoryState.
WorldState-Extraction, Persistenz und API bleiben separate Folgearbeiten.

## Architekturvertrag

Der verbindliche Vertrag steht in
[`/.harness/architecture/llm-integration.md`](../../../.harness/architecture/llm-integration.md).
Die Initialisierung besitzt einen eigenen, task-spezifischen Port. Sie darf
den regulären `StoryGenerationRequest` nicht durch optionale oder erfundene
WorldState- und StoryState-Felder aufweichen.

## Zielablauf für Phase 1

```text
GenerateInitialStoryState.apply(request)
    -> GenerationConfigurationResolver.resolve(story)
    -> StoryInitializationPromptResolver.resolve(configuration)
    -> StoryInitializationRequest bauen
    -> StoryInitializationPort.generate(call)
    -> InitialStoryText erhalten
    -> StoryInitialization und StoryState bauen
    -> Success[StoryState] oder typed Failure zurückgeben
```

Der anwendungsnahe Live-Test ruft diese Operation mit realem, ausdrücklich
aktiviertem LM Studio auf. Er prüft das Ergebnis und druckt den StoryState als
JSON über `pytest -s`. Produktionscode enthält keine Diagnoseausgabe.

## Geplante Typen und Verantwortungen

```text
Domain
StoryInitialization
    prompt
    narration
    completed_at

StoryState
    initialization: StoryInitialization | None
    turns: ()
    summary: None
    current_turn_sequence: 0

Application LLM contract
StoryInitializationRequest
    system_prompts
    configuration
    initial_prompt

InitialStoryText
    text

StoryInitializationPort
    generate(LLMGenerationCall[StoryInitializationRequest])

Application operation
GenerateInitialStoryState
    apply(GenerateInitialStoryStateRequest)
    -> Success[StoryState] | Failure[StoryInitializationError]
```

`InitialStoryText` ist die Rückgabe des Modellports. Die Application ergänzt
Initialprompt und Zeitpunkt und erzeugt erst dann den Domainwert
`StoryInitialization` und den vollständigen `StoryState`.

## Prompt- und Modellkonfiguration

Das Promptpaket erhält einen neuen Task `story_initialization`. Sein Text
fordert die Eröffnungsprosa aus Initialprompt, aufgelöstem Promptprofil,
Sprache und narrativen Grenzen an. Er verlangt weder vorhandene Weltfakten
noch eine bestehende Chronologie.

Die zentrale LLM-Konfiguration liefert pro Aufruf eine atomare Kombination
aus `ModelSelection` und `GenerationOptions`. Der Application-Vertrag kennt
eine aufgabenorientierte Auflösung für `story`, `extraction` und `summary`,
ohne TOML oder Provider zu importieren. Für Phase 1 gilt:

```text
task = story
temperature = 0.5
max_output_tokens = None
```

TOML setzt für `None` kein Feld. `max_output_tokens` bleibt daher im
Konfigurationsdokument ausgelassen.

## Kleine Umsetzungs-Subtasks

### 1. Domainwert für die Eröffnung

- Ziel: Einen `StoryState` mit `StoryInitialization` ausdrücken, ohne bestehende
  persistierte Draft-Zustände zu brechen.
- Scope: Domainwerte, Mapping und vorhandene Fixtures, die einen StoryState
  bauen.
- Nicht-Ziele: Keine LLM-Aufrufe, keine Datenbankmigration und keine
  Extraction.
- Kontext: Ein Initialprompt ist keine Spieleraktion; der erste `StoryTurn`
  bleibt Sequenz 1.
- Abhängigkeiten: Keine.
- Akzeptanz: Ein initialisierter StoryState ohne Turns ist gültig;
  `GenerateInitialStoryState` liefert bei Erfolg stets eine vorhandene
  Initialisierung. Die verpflichtende Persistenzinvariante folgt in
  `STORY-010`.
- Verifikation: Deterministische Domain- und Mapper-Tests.
- Abschluss: Alle betroffenen bestehenden Konstruktionen verwenden eine
  fachlich vollständige Initialisierung.

### 2. Initialisierungs-Prompt und dynamische Generationseinstellungen

- Ziel: Initialisierung als eigene Modellaufgabe und zentral aufgelöste
  Laufzeitkonfiguration ausdrücken.
- Scope: Promptpaket, Application-Ports, LLM-Konfigurationsloader und deren
  Tests.
- Nicht-Ziele: Kein konkreter StoryState-Aufbau und kein LM-Studio-Live-Aufruf.
- Kontext: Jede Auflösung liefert Modellwahl und GenerationOptions gemeinsam;
  Änderungen gelten für den nächsten Aufruf.
- Abhängigkeiten: Subtask 1 kann parallel vorbereitet werden.
- Akzeptanz: Der Init-Task besitzt eindeutige Systemanweisungen;
  `temperature=0.5` wird aufgelöst; fehlendes `max_output_tokens` wird als
  `None` dargestellt; Konfigurationsfehler verhindern den Aufruf.
- Verifikation: Unit-Tests für Promptkatalog und Konfigurationsloader.
- Abschluss: Application-Code kann die konkrete Konfiguration ausschließlich
  über seinen Port erhalten.

### 3. Initialen StoryState erzeugen

- Ziel: Aus Konfiguration und Initialprompt einen transienten StoryState über
  einen providerneutralen Port erzeugen.
- Scope: Application-Operation, reine Request- und State-Builder,
  LM-Studio-Adapter und fokussierte Tests.
- Nicht-Ziele: Kein WorldState, keine Persistenz, kein HTTP-Endpunkt und keine
  automatische Wiederholung.
- Kontext: Adapter formt nur den vorbereiteten Request und normalisiert
  technische Antworten und Fehler.
- Abhängigkeiten: Subtasks 1 und 2.
- Akzeptanz: Der Request enthält keine WorldState- oder StoryState-Felder;
  Erfolg ergibt einen vollständigen StoryState; leere, abgeschnittene und
  erwartete Providerfehler bleiben typed Failures; keine Datenbank wird
  angesprochen.
- Verifikation: Application-Workflowtests mit Testdouble, Adaptertests und
  Architekturtest.
- Abschluss: Die Operation ist unabhängig von LM Studio testbar.

### 4. Expliziter Live-Test mit JSON-Ausgabe

- Ziel: Die Story-Initialisierung mit einem lokalen Modell manuell prüfen,
  ohne Produktverhalten zu erweitern.
- Scope: Markierter Live-Test und testlokaler stabiler JSON-Debug-Mapper.
- Nicht-Ziele: Kein Diagnoserunner, keine Standardprüfung und keine
  automatische Neu-Generierung.
- Kontext: Pytest druckt nur bei `-s`; der Test darf keine Persistenz auslösen.
- Abhängigkeiten: Subtask 3 und ein bewusst bereitgestelltes lokales LM Studio.
- Akzeptanz: Der Test ist ohne explizite Live-Aktivierung übersprungen,
  erzeugt bei Aktivierung genau einen Modellaufruf, prüft den StoryState und
  gibt ihn als JSON aus.
- Verifikation: Manuell aktivierter Live-Test; Standardprofil bleibt offline.
- Abschluss: Menschliche Beurteilung der Ausgabe ist möglich, ohne dass ein
  GameRun entsteht.

## Spätere Abhängigkeiten

`ExtractInitialWorldState` wird als eigene Operation nach Subtask 4 geplant.
Sie erhält den StoryState fachlich als Eingabe, projiziert daraus Initialprompt
und Narration und liefert einen transienten WorldState. Erst danach darf ein
separater Workflow GameRun und GameState in Revision 1 atomar anlegen.
