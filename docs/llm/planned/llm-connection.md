# Geplante LLM-Anbindung

Status: In Diskussion; der allgemeine Rahmen und der Story-Vertrag sind
fachlich geklärt, Extraction ist der nächste Planungsabschnitt.

Verbindlichkeit: Nicht aktiv; dieses Dokument beschreibt den gemeinsam
bestätigten Planungsstand und noch keine implementierte Schnittstelle.

Das Dokument bewahrt zwei Detailebenen. Der allgemeine Vertrag enthält die
bereits bestätigten, für alle Modellaufgaben geltenden Grenzen. Die Abschnitte
der einzelnen Aufgaben halten zusätzlich ihre bestätigten Besonderheiten und
bereits besprochene Konkretisierungspunkte fest. Ein Konkretisierungspunkt wird
nicht allein dadurch verbindlich, dass er als Merkhilfe dokumentiert ist.

## Ziel

Das Storygame soll unterschiedliche Modellaufgaben ausführen können, ohne die
Business-Logik an LM Studio, OpenAI, Groq oder einen bestimmten Modelltyp zu
binden. Die UI darf später lokale oder externe Anbindungen, Provider und Modelle
konfigurieren. Das Backend kennt diese Auswahl, behandelt Provider in seinen
fachlichen Abläufen aber nicht unterschiedlich.

Ein Anbieter- oder Modellwechsel soll auf die technische Konfiguration und die
passende Adapterkette begrenzt bleiben. Dafür besitzen alle Modellaufrufe eine
gemeinsame technische Hülle und je Aufgabe einen eigenen fachlichen Request und
ein eigenes fachliches Ergebnis.

## Allgemeiner Vertrag für Modellaufrufe

Der vollständige allgemeine Vertrag verbindet einen aufgabenspezifischen
Request-Typ mit seinem aufgabenspezifischen Erfolgstyp:

```text
LLMGenerationContract[RequestT, DataT]
├── input: LLMGenerationCall[RequestT]
└── output: OperationResult[DataT, LLMError]
```

Das ist zunächst die fachliche Beschreibung der Ein- und Ausgabegrenze und
nicht zwingend eine eigene spätere Python-Klasse. Die konkrete Schnittstelle
bindet die zusammengehörenden Request- und Datentypen.

### Gemeinsame Hülle

Ein typisierter `LLMGenerationCall[RequestT]` trennt die technische
Modellauswahl vom fachlichen Request:

```text
LLMGenerationCall[RequestT]
├── model_selection
├── generation_options
└── request: RequestT
```

`model_selection` repräsentiert die vom Backend bekannte Konfiguration. Sie
kann später lokale oder API-basierte Ausführung, Provider, Modell und die dafür
benötigte technische Zuordnung abbilden. Zugangsdaten bleiben außerhalb des
fachlichen Vertrags und werden durch die Laufzeitumgebung bereitgestellt.

`generation_options` ist als Platz für technische Erzeugungsoptionen vorgesehen.
Welche Optionen benötigt werden, welche davon anbieterunabhängig sind und ob
sie aus dem Modellkatalog oder pro Aufruf kommen, wird erst bei der konkreten
Schnittstellenausarbeitung entschieden.

`RequestT` bleibt immer aufgabenspezifisch und typisiert, beispielsweise:

- `StoryGenerationRequest`;
- `ExtractionGenerationRequest`;
- später `ImageDescriptionGenerationRequest`.

Die gemeinsame Hülle darf nicht zu einem untypisierten Request mit beliebigen
Feldern werden.

### Gemeinsames Ergebnisprinzip

Der bereits vorhandene Application-Vertrag
`OperationResult[DataT, ErrorT] = Success[DataT] | Failure[ErrorT]` wird für
Modellaufrufe wiederverwendet. Jede Aufgabe bestimmt ihren konkreten
Erfolgstyp; erwartbare Modell- und Providerfehler werden als normierte
`LLMError`-Werte zurückgegeben.

```text
Success
└── aufgabenspezifische Daten

oder

Failure
└── LLMError oder später ein klar getrennter fachlicher Fehler
```

Eine leere oder nur teilweise erzeugte Antwort darf einen Fehler nicht als
Erfolg tarnen.

### Gemeinsame LLM-Fehlerfamilie

`LLMError` ist die anbieterunabhängige Fehlerfamilie für Story-Erzeugung,
Extraction und weitere Modellaufgaben. Von Beginn an sind mindestens folgende
Fehlergruppen zu erwarten:

- Verbindung oder Provider nicht verfügbar;
- Zeitüberschreitung;
- Authentifizierung oder Berechtigung fehlgeschlagen;
- Ratenbegrenzung;
- Modell unbekannt oder nicht verfügbar;
- Anfrage ungültig oder vom Provider abgelehnt;
- Kontext- oder Ausgabelimit überschritten;
- Erzeugung abgebrochen oder unvollständig;
- Modellantwort leer oder ungültig;
- technische Konfiguration fehlerhaft.

Die konkrete Zahl der Fehlertypen und die Reaktion des Backends werden anhand
der tatsächlichen Provider- und Modellfehler festgelegt. Fachliche Fehler einer
Extraction oder einer späteren Domainvalidierung sind keine `LLMError`-Werte.

## Adapter und Provider-Clients

Adapter liegen logisch zwischen Application und konkreter Modelltechnik, gehören
aber zur Infrastruktur. Dort bleiben zwei Verantwortungen getrennt:

- Ein Adapter erfüllt den Application-eigenen Vertrag, bereitet den stabilen
  Request für Provider und Modell auf und normalisiert Antwort und Fehler.
- Ein Provider-Client übernimmt den technischen Zugriff auf LM Studio, OpenAI,
  Groq oder einen anderen Dienst.

Ein Modell erhält nur dann eine eigene Normalisierung, wenn seine Ausgabe vom
Standard abweicht. Modelle mit passender Ausgabe benötigen keinen
Sonderadapter. Die Composition Root wählt Provider-Client, Provideradapter und
optionale Modellnormalisierung, ohne dass die Business-Logik diese Kombination
kennen muss.

Der stabile Vertrag legt die Bedeutung der Daten fest, nicht ihre Darstellung
für ein konkretes Modell. Ein Adapter darf dieselben strukturierten Daten daher
als JSON, benannte Textabschnitte, einzelne Nachrichten oder einen flachen
Prompt darstellen.

## Story-Erzeugung

Status: Vertrag auf Architekturebene geklärt.

### Aufgabe

Die Story-Erzeugung liefert ausschließlich die Prosa des nächsten
Story-Elements. Der `StoryState` bildet die erzählte Chronologie ab, während der
`WorldState` die strukturierte Wahrheit der Spielwelt enthält. Die
Story-Erzeugung schreibt keinen Zustand und liefert keine verbindlichen
Weltänderungen.

### Aufruf

```text
LLMGenerationCall[StoryGenerationRequest]
├── model_selection
├── generation_options
└── request
    ├── system_prompts
    ├── configuration
    ├── world_state
    ├── story_state
    └── user_prompt
```

Die Kategorien haben feste Bedeutungen:

- `system_prompts`: Systemanweisungen für die Story-Erzeugung;
- `configuration`: relevante Spiel- und Erzählvorgaben;
- `world_state`: relevante strukturierte Weltinformationen;
- `story_state`: relevante bisherige Prosa, mindestens soweit sie für eine
  Fortsetzung benötigt wird;
- `user_prompt`: aktuelle Eingabe beziehungsweise Handlung des Spielers.

Die Application zieht die benötigten Daten zusammen. `configuration`,
`world_state` und `story_state` dürfen den vollständigen jeweiligen State oder
ausgewählte vollständige Elemente daraus enthalten. Ein ausgewähltes
Domainobjekt bleibt in sich gültig und wird nicht künstlich halb gefüllt. Wie
diese Auswahl später typisiert wird, gehört zur konkreten
Schnittstellenausarbeitung.

Der Request ist ein typisiertes Objekt mit einer JSON-artigen festen Struktur,
aber nicht zwingend bereits ein JSON-Text. Erst der Adapter erzeugt daraus die
für Provider und Modell geeignete Darstellung.

### Ergebnis

```text
OperationResult[StoryGenerationData, LLMError]

Success
└── StoryGenerationData
    └── text: string

oder

Failure
└── konkreter LLMError
```

Die Business-Logik erhält weder die rohe Providerantwort noch Felder wie
`data`, `return` oder anbieterspezifisch verschachtelte Inhalte. Der Adapter
extrahiert und normalisiert den Storytext oder liefert einen normierten Fehler.

### Stellung im Storyzug

```text
Prompts und relevante Daten zusammenstellen
    ↓
nächstes Story-Element erzeugen
    ↓
WorldState aus der Prosa extrahieren
    ↓
extrahierte Änderungen fachlich prüfen
    ↓
Story und resultierenden WorldState gemeinsam speichern
    ↓
Benutzeroberfläche aktualisieren
```

Prompt, Modellaufruf, Rohantwort, Extraction und ungeprüfte
Änderungsvorschläge bleiben transient. Persistiert wird erst ein vollständig
abgeschlossener `StoryTurn` zusammen mit der resultierenden
`GameState`-Revision.

Eine `Scene` ist kein eigenes persistiertes Objekt. Die wahrgenommene Szene
ergibt sich aus Ort, anwesenden Figuren sowie ihren Zuständen und Beziehungen im
`WorldState`.

### Bewusst spätere Konkretisierung

Der Story-Vertrag legt noch nicht fest:

- konkrete Python-Klassen und Dateistruktur;
- Untertypen und Serialisierung der ausgewählten Kontextdaten;
- konkrete Generierungsoptionen;
- endgültige `LLMError`-Klassen und Backendreaktionen;
- genaue Prompttexte und modellbezogene Darstellungen;
- Wiederholung, Ausweichmodell, Streaming, Logging und Nutzungsmetadaten.

Diese Punkte konkretisieren den bestätigten Vertrag später, verändern aber
nicht mehr seine grundlegende Ein- und Ausgabegrenze.

### Merkliste für die spätere Story-Schnittstelle

Folgende technische Erzeugungsoptionen wurden bereits als möglicherweise
relevant benannt, sind aber noch nicht ausgewählt oder abschließend definiert:

- `temperature`;
- `max_output_tokens` beziehungsweise ein Ausgabelimit;
- `top_p`;
- `seed`;
- `stop_sequences`;
- `streaming`.

Bei der Konkretisierung ist außerdem zu entscheiden, welche Werte als Defaults
im Modellkatalog liegen und ob einzelne Werte pro Story-Aufruf überschrieben
werden dürfen. Providerunterstützung und anbieterunabhängige Semantik müssen
dabei geprüft werden. Diese Merkliste bleibt erhalten, auch solange der
allgemeine Vertrag lediglich die Existenz von `generation_options` festlegt.

## Extraction

Status: Der allgemeine Ein- und Ausgabevertrag ist bestätigt; fachliche
Extraction-Details und konkrete Schnittstellentypen bleiben zu klären.

### Bereits gesetzter Rahmen

Extraction folgt auf die erzeugte Story-Prosa. Sie ermittelt strukturierte
Änderungsvorschläge für den `WorldState`, beispielsweise für Gegenstände,
Figuren, Orte, Aufenthaltsbeziehungen, Fakten oder Ziele. Das Modell schreibt
den kanonischen Zustand nicht direkt. Die Application prüft die Vorschläge und
die Domain übernimmt ausschließlich freigegebene Änderungen auf der erwarteten
Revision.

Extraction verwendet dieselbe technische Hülle `LLMGenerationCall[RequestT]`,
das vorhandene `OperationResult` und die gemeinsame `LLMError`-Familie. Request
und Erfolgsdaten bleiben extraction-spezifisch.

Damit ist bestätigt, dass der allgemeine
`LLMGenerationContract[RequestT, DataT]` ohne Erweiterung sowohl für Story als
auch für gemeinsame und spezialisierte Extraction gilt. Die weitere Planung
konkretisiert nur noch `ExtractionGenerationRequest`, die jeweiligen
Extraction-Datentypen, Aggregation und fachliche Prüfung.

### Ergebnisgrenze der Extraction

Im Unterschied zur Story ist der erfolgreiche `data`-Wert kein Prosatext,
sondern ein strukturiertes, typisiertes Extraction-Ergebnis. Konzeptionell gilt:

```text
gemeinsame Extraction
LLMGenerationContract[WorldExtractionRequest, WorldExtractionData]

spezialisierte Extraction
LLMGenerationContract[ItemExtractionRequest, ItemExtractionData]
LLMGenerationContract[CharacterExtractionRequest, CharacterExtractionData]
LLMGenerationContract[LocationExtractionRequest, LocationExtractionData]
```

Ein gemeinsames Ergebnis kann beispielsweise mehrere Kategorien enthalten:

```text
WorldExtractionData
├── items
├── characters
├── locations
├── links
├── facts
├── knowledge
└── goals
```

Ein fokussiertes Ergebnis enthält nur seine jeweilige Kategorie. Weil keine,
eine oder mehrere Änderungen erkannt werden können, sind diese Kategorien
Sammlungen und keine einzelnen optionalen Werte.

Die Namen `ItemState` und `CharacterState` beschreiben die Idee anschaulich,
sind aber keine bestehenden Domainklassen. Im aktuellen Domainmodell sind
Gegenstände und Figuren `WorldEntity`-Werte mit unterschiedlichen
`EntityKind`-Werten. Die noch ungeprüfte LLM-Ausgabe darf außerdem nicht wie ein
bereits kanonischer State erscheinen. Die konkrete Schnittstellenplanung muss
deshalb passende Extraction- oder Kandidatentypen definieren, die vollständige
Domainwerte vorbereiten können, aber erst nach fachlicher Prüfung zu erlaubten
Änderungen werden.

Ungültiges JSON oder eine technisch nicht passende Struktur wird als ungültige
Modellantwort normalisiert. Widersprüchliche Referenzen oder fachlich
unzulässige Änderungen werden dagegen erst in der nachfolgenden
Application-/Domainprüfung behandelt.

### Als Nächstes zu klären

- Gibt es einen gemeinsamen Extraction-Aufruf oder getrennte Aufrufe für
  Gegenstände, Figuren, Orte und weitere Bereiche?
- Welche festen Hauptkategorien benötigt ein
  `ExtractionGenerationRequest`?
- Liefert Extraction einen gemeinsamen Änderungsvorschlag oder je Bereich
  eigene strukturierte Ergebnisse?
- Wo endet technische Ausgabevalidierung und wo beginnt fachliche Prüfung?
- Wie wird ein teilweise erfolgreicher oder fehlerhafter Extraction-Ablauf im
  Storyzug behandelt?

### Gemeinsame und spezialisierte Extraction

Der bestehende allgemeine Vertrag unterstützt beide Ausführungsformen ohne
Anpassung:

```text
WorldState-Extraction
├── gemeinsame Extraction
│   └── ein Modellaufruf für alle relevanten Bereiche
└── spezialisierte Extraction
    ├── Gegenstände
    ├── Figuren
    ├── Orte und Beziehungen
    ├── Fakten und Wissen
    └── Ziele
```

Beide Wege sollen nach der Modellnormalisierung dasselbe gemeinsame fachliche
Zwischenergebnis liefern. Validierung, Freigabe, Domainänderung und Persistenz
dürfen deshalb nicht doppelt implementiert werden.

Der Unterschied liegt im Application-Workflow und nicht in der gemeinsamen
LLM-Hülle. Eine gemeinsame Extraction führt einen
`LLMGenerationCall[WorldExtractionRequest]` mit einem umfassenden Systemprompt
aus. Eine spezialisierte Extraction führt mehrere Calls mit fokussierten
Requests und Systemprompts aus. `model_selection`, `generation_options`,
`OperationResult` und `LLMError` bleiben dabei unverändert.

Die gemeinsame Extraction benötigt einen großen Request und ein gemeinsames
strukturiertes Ergebnis. Die spezialisierte Extraction benötigt mehrere
fachliche Requests, einen sichtbaren Workflow und einen Aggregationsschritt.
Sie kann einzelne fehlgeschlagene Bereiche gezielt wiederholen, muss aber
Querverweise, Duplikate und Abhängigkeiten zwischen den Teilergebnissen
auflösen.

Auch bei spezialisierten Aufrufen wird kein teilweise extrahierter Storyzug
persistiert. Teilergebnisse dürfen transient gesammelt und fehlgeschlagene
Bereiche wiederholt werden; erst das vollständige, gemeinsam geprüfte Ergebnis
darf in den atomaren Turn-Abschluss eingehen.

Welche Variante die erste Umsetzung nutzt und ob eine spätere Konfiguration
zwischen ihnen wählen kann, bleibt offen. Diese Umsetzungsentscheidung erweitert
den allgemeinen LLM-Vertrag nicht.

## Später zu betrachten

- Modellkatalog und Modellabfrage;
- konkrete UI-Konfiguration für lokale und API-basierte Modelle;
- Bildbeschreibung für Text-zu-Bild;
- tatsächliche Szenenbilderzeugung;
- weitere Modellaufgaben;
- Wiederholungs-, Fallback- und Betriebsregeln;
- Speicherung oder bewusste Nicht-Speicherung technischer Nutzungsmetadaten.

### Kompatibilität mit einem späteren ScenePicGenerator

Die aktuelle Architektur darf eine spätere tatsächliche Bilderzeugung nicht
ausschließen. Das generische Muster aus typisiertem Request, technischer
Modellauswahl, vorgesehenen Generierungsoptionen und typisiertem
`OperationResult` ist dafür grundsätzlich geeignet. Es darf deshalb keine
allgemeine Annahme geben, dass `DataT` immer Text oder JSON ist.

Ein späterer ScenePicGenerator benötigt voraussichtlich einen eigenen
`ScenePicGenerationRequest`, einen Bild-Erfolgstyp und bildspezifische Fehler.
Dann wird entschieden, ob `LLMGenerationContract` direkt wiederverwendet oder
zu einem neutraler benannten `ModelGenerationContract` angehoben wird. Die
task-spezifischen Ports bleiben in beiden Fällen erhalten; ein universeller
untypisierter Generator wird nicht eingeführt.

Die Bilderzeugung selbst ist nicht Teil der ersten Umsetzung. Diese
Kompatibilitätsanforderung schützt lediglich den Erweiterungspfad.
