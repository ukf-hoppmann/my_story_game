# Geplante Story-Erzeugung über austauschbare Modelle

Status: Der Provider-Anschluss und die technische Story-Grenze sind
implementiert; der Story-Workflow ist noch nicht implementiert.
Grundlage: [Entscheidung zur LLM-Anbindung](../../decisions/llm-anbindung.md) und
der verbindliche
[LLM-Architekturvertrag](../../../../.harness/architecture/llm-integration.md).

## Aktueller Stand

Das Domain- und Persistenzmodell kennt bereits `GameConfiguration`,
`WorldState`, `StoryState`, abgeschlossene `StoryTurn`-Werte und die atomare
Turn-Commit-Grenze. Modell- und Promptkataloge, tatsächliche Modellaufrufe,
Die LM-Studio-Infrastruktur kann die definierte Story-Grenze bereits live
aufrufen und normalisierte Prosa oder einen `LLMError` liefern. Modell- und
Promptkataloge, die Story-Operation und WorldState-Extraction sind noch nicht
implementiert.

`GameConfiguration` speichert bereits semantische Modellreferenzen und die
Version des Promptpakets. Provider-URLs, Zugangsdaten, Rohprompts und laufende
Aufrufe gehören weiterhin nicht in den GameState.

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
- `configuration` enthält relevante Sprache, Stil, Perspektive und
  Erzählvorgaben.
- `world_state` enthält den vollständigen WorldState oder ausgewählte
  vollständige Werte, die für den nächsten Text relevant sind.
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
- Promptpaket und Modellreferenz aus der Konfiguration auflösen lassen;
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

## Offene Entscheidungen vor der Implementierung

- konkrete Python-Typen und Modulpfade;
- genaue Struktur der Kontextprojektionen;
- erste verbindliche `LLMError`-Varianten und Retryregeln;
- Auflösung von Modell- und Promptkatalogen;
- LM-Studio-Endpoint und dessen Providerformat;
- tatsächlich benötigte Generierungsoptionen;
- Streaming ja oder nein;
- Auswahl der ersten Extraction-Variante für den vollständigen Storyzug;
- Grenze und Freigabe für einen optionalen Live-Test mit lokalem LM Studio.

## Dokumentationsfolgen

Mit der Implementierung müssen aktuelle technische Dokumentation,
Konfigurationsbeschreibung, Betriebsanleitung und API-Verhalten aktualisiert
werden. Dieses Dokument bleibt bis dahin ein Zielbild und darf nicht als
implementierter Stand beschrieben werden.
