# Geplante Story-Erzeugung über austauschbare Modelle

Status: Ein vollständiger Storyzug ist implementiert — Kontextauswahl,
Story-Erzeugung, Turn-Extraction, Freigabe, rollierende Zusammenfassung und
atomarer Commit — und über einen Live-Checkpoint gegen echtes LM Studio prüfbar
(`TestStoryTurnHuman.test_full_turn`, opt-in mit `--run-lmstudio-live`). Noch
nicht implementiert sind die Verdrahtung des Providers im Composition Root und
ein HTTP-Endpunkt.
Grundlage: [Entscheidung zur LLM-Anbindung](../../decisions/llm-anbindung.md),
die [Entscheidung zu Promptprofil und Modellwahl](../../decisions/promptprofil-und-modellwahl.md)
und der verbindliche
[LLM-Architekturvertrag](../../../../.harness/architecture/llm-integration.md).

## Aktueller Stand

Das Domain- und Persistenzmodell kennt bereits `GameConfiguration`,
`WorldState`, `StoryState`, abgeschlossene `StoryTurn`-Werte und die atomare
Turn-Commit-Grenze. Die zentrale Laufzeitkonfiguration unter
`configs/llm.toml` definiert je ein Modell für Story, Extraction und Summary.
Die LM-Studio-Infrastruktur kann die definierte Story-Grenze live aufrufen und
normalisierte Prosa oder einen `LLMError` liefern. Das versionierte
Ein-Datei-Promptpaket und der validierende dateibasierte Catalog sind umgesetzt;
Story-Operation, Story-API und WorldState-Extraction-Workflow bleiben noch
nicht implementiert.

`GameConfiguration` speichert ein vollständiges explizites Promptprofil,
erzählerische Grenzen sowie Paket-ID und -version. Die drei Modellreferenzen
liegen ausschließlich in der zentralen Laufzeitkonfiguration. Provider-URLs,
Zugangsdaten, Rohprompts und laufende Aufrufe gehören weiterhin nicht in den
GameState.

Das Paket `story.base`/`1` enthält getrennte Tasks für Story- und WorldState-
Initialisierung sowie reguläre Story Generation und spätere Extraction. Es
enthält außerdem alle vereinbarten Auswahlkategorien samt Defaults und
die nicht auswählbare Directive `narrative_boundaries`. Die Auswahlfelder für
Genre, Tone, Pacing, Player Agency, Consequence, Challenge und Content Profile
sind Teil von `GameConfiguration`. Das Profil enthält außerdem Prose Style,
Perspective und Control Mode. Die Application validiert und löst diese Auswahl
vor dem Adapter gegen das referenzierte Paket auf; der Loader trifft keine
fachliche Auswahl.

Die zentrale LLM-Laufzeitkonfiguration bleibt maßgeblich für das aktive Story-,
Extraction- und Summary-Modell. Sie löst die zum Auftrag gehörende logische
Referenz in eine konkrete `ModelSelection` auf. Diese Auswahl wird nicht mehr
in der Partie eingefroren.

## Ziel

Die erste Umsetzung soll über LM Studio Story-Prosa erzeugen können, ohne die
Application an LM Studio zu binden. Ein späterer Wechsel zu einem API-Provider
soll durch Konfiguration, Provider-Client und Adapter erfolgen, nicht durch eine
Änderung der Story-Operation.

Diese Planung behandelt nur die Story-Erzeugungsgrenze und ihre direkte
Einordnung in den Storyzug. Extraction wird separat konkretisiert, verwendet
aber anschließend denselben allgemeinen Modellaufruf.

## Nicht-Ziele der ersten Umsetzung

- keine vollständige UI zur Provider- und Modellverwaltung;
- kein ScenePicGenerator;
- keine Implementierung beider Extraction-Varianten;
- keine persistierten Rohprompts, Modellantworten oder halbfertigen Workflows;
- keine automatische Fortsetzung eines nach einem Modellaufruf abgestürzten
  Storyzugs;
- keine vorsorgliche Unterstützung aller Provideroptionen.

## Geplanter Ablauf

```text
aktuellen GameState und Userprompt laden
    ↓
relevante Story-, World- und Konfigurationsdaten auswählen
    ↓
versionierte Systemprompts laden
    ↓
Promptprofil-IDs zu verständlichen Story-Anweisungen auflösen
    ↓
aktives Story-Modell aus der zentralen Konfiguration übernehmen
    ↓
StoryGenerationRequest erstellen
    ↓
konfiguriertes Modell über den Story-Port aufrufen
    ↓
Story-Prosa oder normierten Fehler erhalten
    ↓
WorldState-Extraction ausführen und fachlich prüfen
    ↓
StoryTurn und neue GameState-Revision atomar speichern
    ↓
UI mit dem abgeschlossenen Zustand aktualisieren
```

Modellaufruf und Extraction bleiben außerhalb der Datenbanktransaktion. Bei
einem Fehler vor dem finalen Commit bleibt die vorherige Revision gültig.

## Geplante Verträge

Die folgenden Namen sind Arbeitsnamen für die spätere konkrete
Schnittstellenplanung.

### Gemeinsame Call-Hülle

```text
LLMGenerationCall[StoryGenerationRequest]
├── model_selection
├── generation_options
└── request
```

`model_selection` muss die vom Backend bekannte Modellkonfiguration bis zum
LLM-Gateway transportieren können. Die Story-Operation darf daraus keine
Provider-Sonderfälle ableiten.

Die Auswahl wird vor dem Modellport anhand des Auftrags aus der zentralen
Konfiguration aufgelöst. Adapter und Provider-Client erhalten bereits die
konkrete `ModelSelection` und wählen kein Modell erneut aus.

`generation_options` ist als Erweiterungspunkt vorgesehen. Bei der späteren
Ausarbeitung werden nur tatsächlich benötigte Optionen mit klarer Semantik
aufgenommen. Bereits als mögliche Kandidaten notiert sind `temperature`,
`max_output_tokens`, `top_p`, `seed`, `stop_sequences` und `streaming`. Noch ist
keine dieser Optionen Bestandteil einer implementierten Schnittstelle.

### StoryGenerationRequest

```text
StoryGenerationRequest
├── system_prompts
├── configuration
├── world_state
├── story_state
└── user_prompt
```

- `system_prompts` enthält die geladenen fachlichen Story-Anweisungen.
- `configuration` enthält Sprache, erzählerische Grenzen und die bereits aus
  dem Promptprofil aufgelösten verständlichen Erzählvorgaben. Technische
  Options-IDs werden nicht erst im Adapter interpretiert.
- `world_state` enthält den vollständigen WorldState oder ausgewählte
  vollständige Werte, die für den nächsten Text relevant sind. Der Ausschnitt
  wird durch eine eigene deterministische Kontextauswahl bestimmt, siehe
  unten.
- `story_state` enthält den vollständigen StoryState oder die relevante
  Zusammenfassung und ausgewählte abgeschlossene Turns.
- `user_prompt` enthält die aktuelle Spielerhandlung.

Die Application verantwortet Auswahl und Bedeutung. Die spätere Typisierung
muss verhindern, dass teilweise gefüllte kanonische Domainobjekte als
Promptkontext ausgegeben werden.

### Story-Ergebnis

```text
OperationResult[StoryGenerationData, LLMError]

Success
└── StoryGenerationData
    └── story: string

oder

Failure
└── konkreter LLMError
```

Ob das Feld im Code `story`, `text` oder passend zum bestehenden Domainbegriff
`narration` heißt, wird bei der Schnittstellendefinition entschieden. Es enthält
immer ausschließlich normalisierte Story-Prosa.

## Geplante Verantwortungen

### Application

- relevante Daten bestimmen;
- Promptpaket aus der GameConfiguration laden und die Story-Auswahloptionen zu
  verständlichen Anweisungen auflösen;
- das aktive Story-Modell aus der zentralen Laufzeitkonfiguration übernehmen;
- den fachlichen Request bilden;
- Story-Erzeugung in den Turn-Workflow einordnen;
- normierte Fehler in sichtbares Workflowverhalten übersetzen;
- Story-Prosa an Extraction weitergeben;
- nur einen vollständig validierten Turn committen.

### Story-Adapter

- den vorbereiteten Request für Provider und Modell darstellen;
- den Provider-Client aufrufen;
- die Story-Prosa aus der Rohantwort extrahieren;
- technisch leere, abgebrochene oder ungültige Antworten ablehnen;
- Providerfehler in die Application-eigene LLM-Fehlerfamilie übersetzen;
- eine optionale Modellnormalisierung nur bei nachgewiesenem Bedarf anwenden.

### Provider-Client

- technische LM-Studio-Kommunikation kapseln;
- Request- und Responseformate des verwendeten Endpoints besitzen;
- Transportfehler und Rohantworten ausschließlich an den Adapter geben.

## Fehlerverhalten

Die erste konkrete Fehlerausarbeitung soll mindestens Verbindungsausfall,
Timeout, fehlerhafte Konfiguration, unbekanntes Modell, abgelehnte Anfrage,
überschrittenes Limit, abgebrochene Erzeugung sowie leere oder ungültige Antwort
unterscheiden.

Für jeden Fehler muss entschieden werden, ob derselbe Aufruf wiederholt werden
darf, ein anderes Modell gewählt werden kann oder der Storyzug sichtbar
abbricht. Providerdetails dürfen für Diagnosezwecke erhalten bleiben, aber nicht
als Providerobjekt die Application-Grenze überschreiten.

## Testplanung

### Application-Tests

- Der Request enthält genau die von der Application ausgewählten Daten.
- Providerwahl erzeugt keine fachlichen Sonderpfade.
- Erfolg liefert normalisierte Prosa an den folgenden Workflow.
- Jeder normierte Fehler führt zum vorgesehenen Abbruch- oder
  Wiederholungsverhalten.
- Ohne erfolgreiche Extraction und Validierung wird kein Turn persistiert.

### Adapter-Tests

- Systemprompts, Kontext und Userprompt werden korrekt abgebildet.
- Unterschiedliche Providerhüllen ergeben denselben Story-Erfolgstyp.
- Leere, unvollständige und formal ungültige Antworten werden nicht als Erfolg
  akzeptiert.
- Relevante Providerfehler werden vollständig und ohne Rohobjekt-Leakage
  normalisiert.
- Modellnormalisierung ist standardmäßig nicht aktiv und wird nur konfiguriert,
  wenn ein konkreter Modelltest sie verlangt.

### Workflow- und Integrationstests

- Die sichtbare Reihenfolge von Story-Erzeugung, Extraction, Validierung und
  Commit bleibt erhalten.
- Ein Fehler vor dem Commit lässt GameState und StoryTurn unverändert.
- StoryTurn und resultierende GameState-Revision werden weiterhin atomar
  gespeichert.
- Ein LM-Studio-Testprofil bleibt von standardmäßigen Offline-Tests getrennt,
  solange es auf einen nicht Harness-eigenen lokalen Dienst zugreift.

## Abnahmekriterien

- Eine Story-Operation kann mit einem Testdouble unabhängig vom Provider
  getestet werden.
- Ein LM-Studio-Adapter kann denselben Application-Vertrag erfüllen, ohne dass
  Story-Code LM-Studio-Typen importiert.
- Ein erfolgreicher Aufruf liefert ausschließlich normalisierte Prosa.
- Erwartbare technische Fehlschläge liefern einen konkreten normierten Fehler.
- Relevanzauswahl und Promptbedeutung bleiben in der Application.
- Adapter und Provider-Client enthalten keine Domainfreigabe oder
  Persistenzlogik.
- Der bestehende atomare Turn-Abschluss bleibt unverändert.
- Architekturtests sichern die neue Abhängigkeitsrichtung.

## Kontextauswahl für einen Zug

`SelectStoryTurnContext` bestimmt den relevanten Ausschnitt vor dem
Modellaufruf. Die Operation ist deterministisch, führt keinen Modellaufruf aus,
speichert nichts und lässt den übergebenen GameState unverändert. Sie delegiert
in sichtbarer Reihenfolge an sechs einzeln testbare Schritte:

1. `SelectAlwaysIncluded` — Zusammenfassung, letzte Züge, Weltregeln, offene
   Hauptziele, die gesteuerte Figur sowie Sprache, Perspektive, Steuerungsmodus
   und erzählerische Grenzen. Dieser Rahmen wird von der Budgetierung nie
   gekappt. Die gesteuerte Figur ist auch dann enthalten, wenn die Erzählung
   sie nie beim Namen nennt, etwa bei Du-Erzählung.
2. `ResolveMentionedEntities` — bekannte Bezeichnungen in Spielereingabe und
   jüngster Prosa. Treffer in der Eingabe wiegen schwerer als solche in der
   Prosa. Gesucht wird nach ganzen Wörtern, groß- und kleinschreibungsneutral,
   mit Toleranz für deutsche Endungen und vorangestellte Artikel, damit
   `Marens Schwert` und `dem Wirt` treffen, `kann` aber nicht `Ann`. Mehrdeutige
   Nennungen werden nicht aufgelöst; alle Kandidaten bleiben erhalten.
3. `PopulateSceneLocations` — bevölkert die Orte aus `scene_location_ids` und
   danach im Text genannte Nebenschauplätze. Der Zeiger ist die primäre
   Wahrheit und trägt auch einen Zug, dessen Prosa gar keinen Ort nennt;
   Nebenschauplätze verdrängen ihn nie.
4. `ExpandOneHop` — direkt verlinkte Entitäten, jede Beziehungsart, beide
   Richtungen, genau ein Schritt.
5. `SelectReferencedFactsKnowledgeGoals` — zugehörige Fakten, Akteurswissen und
   Ziele; fehlende Zielreferenzen werden nachgezogen.
6. `ApplySelectionBudget` — kappt nach Auswahlgrund, bei Gleichstand nach der
   stabilen Weltreihenfolge, und entfernt anschließend alles, was auf eine
   gekappte Entität zeigt. `truncated` meldet, dass ein Limit gegriffen hat.

## Story-Erzeugung

`GenerateStory` bildet den ausgewählten Kontext auf die fünf Textfelder des
`StoryGenerationRequest` ab und ruft den Story-Port. Die Projektion liegt in
`story_prompt_sections.py` als reine Funktionen:

- `configuration_text` löst die Options-IDs des Promptprofils in verständliche
  Anweisungen auf. Sie wird von der Initialisierung und vom regulären Zug
  gemeinsam genutzt, weil beide dieselbe aufgelöste Auswahl hereinbekommen.
- `world_state_text` rendert Schauplatz, Entitäten, Beziehungen, Fakten, Wissen,
  Regeln und Ziele als benannte Abschnitte.
- `story_state_text` rendert die laufende Zusammenfassung und die letzten Züge.

Die `GameConfiguration` wird neben dem Kontext übergeben, weil die
Promptauflösung Paket-ID und -version braucht, die der Kontext nicht führt.

Ein leerer Weltausschnitt ist im Director Mode gültig, der Request weist leeren
Text aber ab. Die Projektion schreibt in diesem Fall einen ausdrücklichen
Platzhaltersatz, statt den Zug scheitern zu lassen.

Verdecktes Wissen wird im ersten Wurf **nicht** gekennzeichnet: `director_only`
erscheint im Prompt wie jede andere Tatsache. Ob das Modell dadurch Plotpunkte
vorzeitig ausspricht, muss beobachtet werden; die Entscheidung darüber ist als
offene Folgearbeit festgehalten.

## Turn-Extraction und Freigabe

`ExtractStoryTurnChanges` vergleicht die neu erzeugte Prosa mit dem aktuellen
Weltausschnitt und liefert einen unbestätigten Delta-Vorschlag: neue und
geänderte Entitäten, hinzugefügte und entfernte Beziehungen, hinzugefügte und
entfernte Tatsachen sowie den Schauplatz nach dem Zug. Wissen, Weltregeln und
Ziele bleiben außen vor, konsistent zur Initialisierung.

Die Spielereingabe erreicht diesen Aufruf bewusst nicht. Was geschehen ist,
sagt die Erzählung — nicht, was der Spieler versucht hat.

Bestehende Objekte spricht das Modell über kurze Handles an, die
`extraction_projection` für genau diesen einen Aufruf vergibt: `e` für
Entitäten, `l` für Beziehungen, `f` für Tatsachen. Bezeichnungen reichen nicht,
weil gleichlautende Namen erlaubt sind, und stabile IDs kosten deutlich mehr
Token und werden von lokalen Modellen verschrieben — ein falsches Zeichen würde
den ganzen Zug verwerfen. Neu Entstandenes verwendet weiterhin lokale
Referenzen wie bei der Initialisierung.

`ApproveStoryTurnChanges` löst beide Referenzformen gegen die aktuelle Revision
auf, vergibt neuen Objekten erst dabei stabile IDs, bildet daraus den
transienten `ProposedChangeSet` und gibt ihn frei. Entfernte Beziehungen werden
vor hinzugefügten eingeordnet, damit ein Ortswechsel nicht kurzzeitig zwei
Aufenthaltsorte beansprucht. Die Domain-Invarianten prüft ein Trockenlauf, der
verworfen wird — die Regeln bleiben damit an einer Stelle. Jeder Fehler
verwirft den gesamten Vorschlag.

Dieser Freigabepfad ist der gemeinsame Trichter: eine spätere Aufteilung in
mehrere gezielte Extraktionsaufrufe tauscht nur den Aufrufteil aus.

### Belege

Das Delta-Schema kann je Änderung ein wörtliches Zitat aus der Erzählung
verlangen. Ein Schalter am Extraktions-Request entscheidet darüber; der Adapter
hält zwei Schemavarianten bereit und wählt danach aus. Der Schalter ist
zunächst eingeschaltet, um zu beobachten, wie zuverlässig das Modell zitiert.

Belege kosten Ausgabetoken — lokal die langsamste, bei API-Abrechnung die
teuerste Ressource. Sie sind trotzdem sinnvoll, weil sie die einzige billige
Prüfung ermöglichen, die Erfundenes von Beobachtetem trennt, und weil sie die
Information sind, die eine spätere Anzeige braucht. Fehlt ein Beleg, wird der
Vorschlag nicht verworfen: Belege sind Diagnose, keine Bedingung.

Die Zitate landen in der `ProposalEvidence` der jeweiligen Änderung. Der
transiente Vorschlag ist im Zugergebnis lesbar, damit die Begründungen
überhaupt sichtbar werden können; persistiert wird er nicht.

## Rollierende Zusammenfassung

`SummarizeStory` schreibt nach dem Zug die laufende Zusammenfassung fort. Der
Aufruf erhält nur die bisherige Zusammenfassung und den neuen Zug, nicht die
ganze Historie — die Zusammenfassung steht bereits für alles davor, was den
Aufruf mit wachsendem Spiel klein hält.

Scheitert sie, **bricht der Zug nicht ab**. Prosa und Änderungen sind zu diesem
Zeitpunkt längst berechnet; sie wegen des Nebenprodukts zu verwerfen wäre der
schlechtere Tausch. Der Zug wird regulär persistiert, und der Fehler bleibt im
Ergebnis sichtbar, damit eine UI ihn anzeigen kann, statt still ohne
Zusammenfassung weiterzulaufen. Ein dauerhafter Logeintrag, an dem sich
wiederkehrende Fehlschläge erkennen ließen, fehlt noch — das Projekt hat
bislang kein Logging.

## Vollständiger Zug

`PlayStoryTurn` verbindet Laden, Kontextauswahl, Story-Erzeugung, Extraktion,
Freigabe und atomaren Commit in sichtbarer Reihenfolge. Die gesteuerte Figur
wird aus der Mitgliedschaft des Aufrufers aufgelöst; im Director Mode ist keine
gebunden, was gültig bleibt. Beide Modellaufrufe liegen außerhalb der
Datenbanktransaktion, sodass jeder Fehler vor dem Commit die vorherige Revision
unverändert stehen lässt.

Die Relevanzauswahl filtert bewusst **nicht** nach `Visibility`. Ein
`director_only`-Fakt wird wie ein öffentlicher ausgewählt, weil das Modell auf
verdeckte Ziele hinarbeiten können muss. `Visibility` bleibt ein UI-Belang: eine
Ansicht, die zeigt, was der Spieler weiß, filtert direkt auf dem `WorldState`
und nicht auf diesem Prompt-Ausschnitt.

Ergebnis ist `PlayedStoryTurn`, nicht roh der `GameState`: neben dem
persistierten Zustand trägt es `proposed_changes` — den transienten, nie
persistierten Vorschlag samt Modellbegründungen, siehe „Belege" — und
`summary_failure` für den in „Rollierende Zusammenfassung" beschriebenen
Sonderfall. Beide Felder sind optional und `None`, wenn nichts zu berichten
ist.

## Offene Entscheidungen vor der Implementierung

- konkrete Python-Typen und Modulpfade;
- genaue Struktur der Kontextprojektionen;
- erste verbindliche `LLMError`-Varianten und Retryregeln;
- LM-Studio-Endpoint und dessen Providerformat;
- tatsächlich benötigte Generierungsoptionen;
- Streaming ja oder nein;
- Auswahl der ersten Extraction-Variante für den vollständigen Storyzug;
- Grenze und Freigabe für einen optionalen Live-Test mit lokalem LM Studio;
- ob und wie verdecktes Wissen im Prompt gekennzeichnet wird, damit das Modell
  es für Andeutungen nutzen kann, ohne es wörtlich zu verraten — der erste Wurf
  kennzeichnet bewusst gar nicht;
- ob die Budgets zusätzlich zu Anzahlgrenzen ein Tokenbudget benötigen;
- ob der Graph-Radius über einen Hop hinaus erweitert wird;
- die Zustandsoperation, mit der die Turn-Extraction `scene_location_ids`
  fortschreibt.

## Dokumentationsfolgen

Mit der Implementierung müssen aktuelle technische Dokumentation,
Konfigurationsbeschreibung, Betriebsanleitung und API-Verhalten aktualisiert
werden. Dieses Dokument bleibt bis dahin ein Zielbild und darf nicht als
implementierter Stand beschrieben werden.
