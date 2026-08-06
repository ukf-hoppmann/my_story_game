# Geplante LLM-Anbindung

Status: In Diskussion  
Verbindlichkeit: Nicht aktiv; dieses Dokument hält den gemeinsam erarbeiteten
Planungsstand fest.

## Ziel

Das Storygame soll unterschiedliche LLM-Aufgaben nutzen können, ohne seine
fachliche Logik an einen bestimmten Anbieter zu binden. Die Anforderungen
werden schrittweise geklärt. Den Anfang macht die Story-Erzeugung; danach folgen
unter anderem die Extraktion von Spieldaten und später die Erzeugung von
Bildbeschreibungen.

Das Dokument unterscheidet bewusst zwischen bestätigten Entscheidungen,
Arbeitsannahmen und offenen Fragen. Ein Vorschlag wird erst als Entscheidung
festgehalten, nachdem er gemeinsam bestätigt wurde.

## Bestätigte Entscheidungen

### Aufgaben werden fachlich getrennt

Die Anwendung fordert eine konkrete Fähigkeit an, beispielsweise:

- eine Geschichte fortsetzen;
- Gegenstände oder andere Spieldaten aus einem Text extrahieren;
- eine Beschreibung für eine spätere Bilderzeugung erstellen.

Die einzelnen Aufgaben dürfen unterschiedliche Eingaben und Ergebnisse haben.
Es gibt deshalb keinen universellen Datenbeutel, dessen Inhalt je nach Aufgabe
eine andere Bedeutung besitzt.

### Anbieter bleiben außerhalb der Spiellogik

Die Spiellogik kennt weder das Format noch die Besonderheiten eines konkreten
LLM-Anbieters. Ein Adapter übersetzt die fachliche Anfrage in das Format des
jeweiligen Anbieters und dessen Antwort zurück in das vereinbarte Ergebnis.

Die Spiellogik soll dadurch nicht geändert werden müssen, wenn ein Anbieter
oder Modell ausgetauscht wird.

### Ergebnisse richten sich nach der Aufgabe

Eine Story-Anfrage liefert einen Story-Text. Eine Extraktion liefert dagegen
klar strukturierte und überprüfbare Daten. Das Ergebnis ist nicht lediglich
"Text oder beliebiges JSON", sondern wird passend zur jeweiligen Aufgabe
festgelegt.

### Modellinformationen sind eine eigene Fähigkeit

Das Abfragen verfügbarer Modelle wird getrennt vom Ausführen einer fachlichen
LLM-Aufgabe betrachtet. Welche Modellinformationen benötigt werden und wer ein
Modell auswählt, ist noch offen.

## Reihenfolge der weiteren Klärung

1. Story-Erzeugung
2. Extraktion von Spieldaten
3. Weitere aktuell benötigte LLM-Aufgaben
4. Bildbeschreibung für Text-zu-Bild, sobald sie konkret relevant wird
5. Gemeinsame technische und betriebliche Anforderungen

Die Reihenfolge darf angepasst werden, wenn Abhängigkeiten sichtbar werden.

## Story-Erzeugung

### Bisheriger gemeinsamer Rahmen

Die Story-Erzeugung erhält die Informationen, die sie benötigt, um die
Geschichte passend zur aktuellen Spielsituation fortzusetzen. Sie liefert
zunächst einen Story-Text zurück. Welche Informationen zwingend erforderlich
sind und wie viel Verantwortung das LLM bei der Fortschreibung der Welt erhält,
ist noch nicht entschieden.

### Offene Fragen

- Welche Informationen muss jede Story-Anfrage enthalten?
- Was davon ist dauerhafter Weltzustand, bisherige Geschichte oder aktuelle
  Spielerhandlung?
- Darf das LLM neue Fakten über die Welt erfinden, und wenn ja, in welchen
  Grenzen?
- Soll das Ergebnis ausschließlich erzählender Text sein oder zusätzliche
  strukturierte Angaben enthalten?
- Welche Fehler oder unvollständigen Antworten muss die Anwendung erkennen und
  behandeln?

## Noch nicht entschieden

- konkrete Schnittstellen, Klassen und Dateistruktur;
- genaue Prompt-Texte und Prompt-Verwaltung;
- konkrete Anbieter und Modelle;
- Modellparameter und Auswahlregeln;
- genaue Datenformate für Extraktionen;
- Wiederholungen, Ausweichmodelle und Verhalten bei Ausfällen;
- Speicherung von Anfragen, Antworten, Kosten oder Nutzungsinformationen.

