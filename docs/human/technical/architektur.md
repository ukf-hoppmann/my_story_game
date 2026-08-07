# Wie wir die Anwendung aufbauen

Eine grobe Übersicht ist als editierbares [Draw.io-Diagramm](architektur.drawio)
verfügbar. Der zweite Tab `Domain – konkret` zeigt den Aufbau des kanonischen
Spielzustands und die wichtigsten Zustandsinvarianten. Der dritte Tab
`Application – konkret` zeigt Use Cases, Abläufe, Fehler-Mapping und Ports.

Unser Ziel ist kein möglichst kompliziertes Architekturmuster. Unser Ziel ist,
dass eine Änderung möglichst wenige Stellen berührt und dass jeder Baustein
für sich verständlich und testbar bleibt.

## Fachliche Bereiche statt großer Sammelklassen

Die Anwendung wird nach fachlichen Aufgabenbereichen gegliedert, zum Beispiel
Story-Erzeugung, World-Extraction oder Verwaltung des GameState. Innerhalb
eines Bereichs gibt es kleine Operationen mit einem klaren Auftrag. Eine
Operation lädt beispielsweise einen Spielstand, bereitet einen Prompt vor oder
wertet eine Extraktion aus.

Kleine Operationen sind kein Selbstzweck. Ein einfacher Hilfsschritt braucht
nicht automatisch eine eigene Klasse und ein eigenes Interface. Getrennt wird
dann, wenn Teile unabhängig geändert, ersetzt oder getestet werden sollen.

## Einheitlicher Aufruf, konkrete Daten

Ausführbare Operationen besitzen die einheitliche Methode `apply`. Was sie als
Eingabe erhalten und als Ergebnis liefern, bleibt trotzdem konkret typisiert.
Eine Ladeoperation verarbeitet also andere Daten als eine Prompt-Operation.

Ein erwartetes Ergebnis ist entweder erfolgreich und enthält die passenden
Daten oder es ist fehlgeschlagen und enthält einen konkreten Fehler. Dadurch
gibt es keinen allgemeinen Antwortbeutel mit vielen optionalen Feldern, dessen
gültige Zustände niemand mehr überblickt.

## Große Abläufe werden sichtbar zusammengesetzt

Ein Spielzug darf mehrere kleine Use Cases nacheinander ausführen. Dabei haben
vier Begriffe unterschiedliche Aufgaben:

- Die Composition Root verbindet konkrete Implementierungen miteinander.
- Eine Policy entscheidet, wann etwas fachlich passieren soll, etwa eine
  World-Extraction nach jedem zweiten Zug.
- Ein Workflow legt die sichtbare Reihenfolge fest.
- Eine Operation erledigt genau ihren konkreten Schritt.

Die Verdrahtung soll deshalb nicht unbemerkt zum Gehirn der Anwendung werden.
Fachliche Entscheidungen gehören in Policies und die Reihenfolge in einen
lesbaren Workflow.

## Infrastruktur bleibt austauschbar

Die Anwendung beschreibt über schmale Verträge, was sie benötigt: zum Beispiel
einen Spielstand lesen, speichern oder ein Modell aufrufen. Datenbank-, Datei-
oder Modelladapter erfüllen diese Verträge. Die Anwendung kennt dadurch nicht
die technischen Einzelheiten der konkreten Infrastruktur.

Wir verwenden bewusst kein universelles `IDataSource`. Ein Datenbankzugriff und
ein LLM-Aufruf haben unterschiedliche Möglichkeiten, Fehler und Garantien. Ein
passender, kleiner Vertrag macht diese Unterschiede sichtbar und verhindert,
dass Typinformationen in allgemeinen Datenobjekten verloren gehen.

## Was die Regeln verhindern sollen

Die Struktur soll insbesondere verhindern, dass wieder eine God-Klasse
entsteht, die Laden, Speichern, Prompt-Aufbau, Modellaufruf, Fehlerbehandlung
und Ablaufsteuerung gleichzeitig übernimmt. Sie soll außerdem verhindern, dass
HTTP- oder Datenbankdetails in die fachliche Logik gelangen.

Die Architektur ist trotzdem veränderbar. Passt eine neue Anforderung nicht
sinnvoll hinein, wird sie nicht heimlich umgangen. Dann wird zuerst beschrieben,
welche Regel nicht passt und wie der Architekturvertrag erweitert werden soll.
Erst nach einer bewussten Entscheidung wird implementiert.

Die verbindlichen, technisch genaueren Regeln stehen in
[`architecture-rules.md`](../../../.harness/architecture-rules.md). Dieses
Dokument erklärt ihren Sinn und ist nicht selbst die normative Regelquelle.
