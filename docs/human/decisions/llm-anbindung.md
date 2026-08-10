# Entscheidung: Anbieterunabhängige Modellanbindung

Status: Grundarchitektur, LM-Studio-Adapter und zweistufige Story-
Initialisierung umgesetzt; regulärer StoryTurn-Workflow bleibt offen.
Datum: 2026-08-07.

Die spätere Entscheidung
[`Promptprofil und aktuelle Modellwahl`](promptprofil-und-modellwahl.md)
konkretisiert, wie Promptoptionen vor dem Adapter aufgelöst und die aktuell
konfigurierten Modelle je Aufgabe in einen Call übernommen werden. Die hier
festgelegten aufgabenspezifischen Ports und Verantwortungsgrenzen bleiben
unverändert.

Die verbindlichen Regeln stehen in
[`.harness/architecture/llm-integration.md`](../../../.harness/architecture/llm-integration.md).
Dieses Dokument erklärt die Entscheidung verständlich und ist keine zweite
Regelquelle.

## Ausgangslage

Das Storygame soll zunächst ein lokales Modell über LM Studio verwenden können.
Später sollen auch externe Anbieter wie OpenAI oder Groq möglich sein. In der UI
konnte die Modellanbindung bereits als lokale oder API-basierte Variante gedacht
werden. Das Backend darf diese Konfiguration kennen, die Spiellogik soll daraus
aber keine Sonderfälle je Provider ableiten.

Provider und Modelle unterscheiden sich sowohl beim Aufruf als auch bei ihren
Antworten. Manche liefern den eigentlichen Inhalt direkt, andere verschachteln
ihn in anbieterspezifischen Feldern. Einzelne Modelle benötigen außerdem eine
besondere Promptdarstellung oder Ausgabeaufbereitung. Diese Unterschiede dürfen
nicht in Story-, Extraction- oder WorldState-Logik gelangen.

## Entscheidung

Jede Modellaufgabe erhält einen fachlich benannten, typisierten Vertrag. Eine
gemeinsame Hülle transportiert Modellauswahl, später konkretisierbare technische
Optionen und den jeweiligen Aufgaben-Request. Request und erfolgreicher
Datentyp bleiben trotzdem je Aufgabe verschieden.

```text
gemeinsamer Generation-Call
├── bekannte Modellauswahl
├── vorgesehene technische Optionen
└── fachlicher Request

Ergebnis
├── Erfolg mit aufgabenspezifischen Daten
└── normierter Fehler
```

Story-Erzeugung liefert Prosa. Extraction liefert strukturierte Kandidaten für
Weltänderungen. Ein späterer Bildgenerator darf ein eigenes Bildresultat
besitzen. Die gemeinsame Hülle ist kein universeller Dienst mit beliebigen
Daten.

## Verantwortungen

### Application

Die Application entscheidet:

- welche Domaininformationen für einen Aufruf relevant sind;
- wie Systemanweisungen, Kontext und aktuelle Eingabe fachlich gegliedert sind;
- welche Aufgabe ausgeführt wird und welches Ergebnis erwartet wird;
- ob Extraction gemeinsam oder in mehreren fokussierten Aufrufen erfolgt;
- ob extrahierte Kandidaten plausibel und fachlich erlaubt sind;
- welche freigegebenen Änderungen in den nächsten GameState eingehen.

Sie darf vollständige States oder vollständige Elemente daraus auswählen. Sie
erzeugt keine halb gefüllten Domainobjekte als Prompt-Abkürzung.

### Adapter

Ein Adapter übersetzt den stabilen Vertrag in die Darstellung, die Provider und
Modell benötigen. Er darf beispielsweise JSON, benannte Textabschnitte oder
mehrere Modellnachrichten erzeugen. Er extrahiert den eigentlichen Inhalt aus
der Providerantwort, prüft die technische Struktur und normalisiert erwartbare
Fehler.

Ein Adapter entscheidet nicht, welche Weltdaten wichtig sind, ob eine Geschichte
plausibel ist oder ob ein Änderungsvorschlag übernommen wird. Ein Modell erhält
nur dann eine eigene Normalisierung, wenn Tests einen tatsächlichen Bedarf
zeigen.

### Provider-Client

Der Provider-Client übernimmt die technische Kommunikation mit LM Studio,
OpenAI, Groq oder einem anderen Dienst. Dazu gehören Transport, Authentifizierung
des Aufrufs, Zeitüberschreitungen und rohe Providerformate. Die Business-Logik
sieht diese Details nicht.

## Story-Grenze

Der Story-Aufruf unterscheidet:

- Systemprompts;
- relevante Spiel- und Erzählkonfiguration;
- relevante WorldState-Daten;
- relevante StoryState-Daten;
- den aktuellen Userprompt.

Die Rückgabe ist entweder normalisierte Story-Prosa oder ein normierter
LLM-Fehler. Die Story-Erzeugung verändert keinen GameState.

## Extraction-Grenze

Extraction erhält mindestens:

- Systemprompts;
- den zuletzt erzeugten, noch transienten Storytext;
- den relevanten aktuellen WorldState zum Abgleich.

Die Rückgabe besteht aus strukturierten, noch ungeprüften Kandidaten, etwa für
Gegenstände, Figuren, Orte, Beziehungen, Fakten, Wissen oder Ziele. Technisch
gültiges JSON ist noch keine fachlich richtige Änderung. Referenzen, Domainregeln
und die tatsächliche Freigabe werden anschließend geprüft.

Ein großer Extraction-Aufruf und mehrere fokussierte Aufrufe sind zwei mögliche
Application-Abläufe innerhalb desselben Vertrags. Sie unterscheiden sich vor
allem durch Systemprompts, ausgewählte Eingaben, Ergebnisumfang, Aggregation und
Fehlerbehandlung. Validierung und Persistenz werden nicht doppelt implementiert.

## Fehlergrenze

Providerfehler werden in eine gemeinsame, anbieterunabhängige LLM-Fehlerfamilie
übersetzt. Erwartbar sind insbesondere Nichterreichbarkeit, Timeout,
Authentifizierungsfehler, Ratenbegrenzung, unbekannte Modelle, abgelehnte
Anfragen, überschrittene Limits, abgebrochene Erzeugung und ungültige Antworten.

Die genaue Zahl der Fehlerklassen und die Reaktionen des Backends werden erst
bei der Schnittstellenimplementierung festgelegt. Fachliche Ablehnung bleibt von
technischen LLM-Fehlern getrennt.

## Betrachtete Alternativen

### Ein universeller LLM-Service

Verworfen wurde ein Dienst, der beliebige Dictionaries annimmt und je nach
Aufgabe Text oder irgendein JSON zurückgibt. Er würde Typinformation verlieren
und mit jeder neuen Aufgabe weitere Sonderfälle sammeln.

### Providerlogik in den Use Cases

Verworfen wurden fachliche Verzweigungen für LM Studio, OpenAI oder andere
Provider. Sie würden die versprochene Austauschbarkeit aufheben.

### Adapter als fachliches Gehirn

Verworfen wurde, Relevanzauswahl, Promptbedeutung oder Domainprüfung in Adapter
zu verlagern. Dadurch müssten fachliche Regeln je Provider wiederholt werden.

### Nur eine Extraction-Form zulassen

Nicht festgelegt wird, dass Extraction zwingend gemeinsam oder spezialisiert
laufen muss. Beide Ausführungsformen passen in denselben Vertrag. Für die erste
Implementierung soll anhand praktischer Modelltests eine Variante gewählt
werden, statt beide vorsorglich vollständig zu bauen.

## Folgen und Risiken

Die Grenze erleichtert Providerwechsel und fokussierte Tests. Sie verlangt aber
Disziplin: Der gemeinsame Call darf nicht zum universellen Service wachsen und
Adapter dürfen keine fachlichen Entscheidungen übernehmen.

Die Auswahl relevanter Promptdaten bleibt eine anspruchsvolle
Application-Aufgabe. Vollständige States können später zu groß werden;
unvollständiger Kontext kann falsche Erzählungen oder Extraktionen verursachen.
Strukturierte Ausgabe reduziert diese Risiken nicht automatisch und benötigt
fachliche Validierung.

## Erweiterungspfad

Ein späterer ScenePicGenerator wird nicht implementiert, aber auch nicht
verbaut. Das gemeinsame Muster darf deshalb nicht annehmen, dass erfolgreiche
Daten immer Text oder JSON sind. Bilderzeugung darf später eigene Requests,
Ergebnisse, Fehler und Ports erhalten und geeignete generische Bausteine
wiederverwenden.
