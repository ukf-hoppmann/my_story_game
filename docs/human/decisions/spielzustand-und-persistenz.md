# Entscheidung: Spielzustand und Persistenz

Status: Beschlossen. Domain- und Persistenzmodell umgesetzt am 2026-08-06.

Dieses Dokument erklärt die gemeinsam getroffenen fachlichen Entscheidungen.
Das beschriebene Domain- und PostgreSQL-Modell, der Promptkatalog, die
fachliche LLM-Integration und der reguläre Story-Workflow sind umgesetzt. Die
zentrale Provider- und Modellkonfiguration liegt separat unter
`configs/llm.toml`; spätere UI- und Provider-Erweiterungen bleiben außerhalb
dieser Entscheidung.

## Warum wir das Modell ändern

Das Spiel braucht zwei unterschiedliche Arten von Informationen:

- eine strukturierte Wahrheit darüber, wie die Spielwelt gerade aussieht;
- die konkrete fortlaufende Geschichte, die der Spieler erlebt hat.

Zusätzlich braucht jede Spielpartie Einstellungen, mit denen sie später unter
denselben Bedingungen fortgesetzt werden kann. Die technische Verarbeitung
eines laufenden Modellaufrufs muss dagegen keinen Backend-Neustart überleben.

Das Ziel ist deshalb ein kleines Modell, das nur abgeschlossene und wirklich
benötigte Daten dauerhaft speichert.

## Beschlossene Grundstruktur

```text
GameRun
├── Status
├── Mitglieder
├── aktuelle Revision
└── GameState
    ├── GameConfiguration
    ├── WorldState
    │   └── Goals
    └── StoryState
        ├── StoryTurns
        ├── Summary-Segmentkette
        └── aktuelle Zugnummer
```

## GameRun

Ein `GameRun` ist eine konkrete Spielpartie. Er ist der Rahmen um den jeweils
aktuellen Spielstand.

Gespeichert werden:

- die ID der Spielpartie;
- der Status `draft`, `active`, `paused` oder `completed`;
- die beteiligten Mitglieder;
- die aktuelle GameState-Revision;
- Erstellungs- und Änderungszeitpunkte.

Der bisherige Datenbankbegriff `story_runs` soll deshalb durch `game_runs`
ersetzt werden.

Ein GameRun speichert nicht, ob gerade ein Modellaufruf oder eine Extraktion
läuft. Das sind vorübergehende Verarbeitungsschritte.

## GameState

Der `GameState` ist der vollständige Stand nach dem zuletzt erfolgreich
abgeschlossenen Spielzug. Er enthält alles, was benötigt wird, um genau dort
weiterzuspielen:

- `GameConfiguration`: Wie diese Partie gespielt und erzählt wird.
- `WorldState`: Welche strukturierte Spielrealität aktuell gilt.
- `StoryState`: Welche konkrete Geschichte bisher erzählt wurde.

Jeder erfolgreich abgeschlossene Zug erzeugt eine neue Revision.

## GameConfiguration

Die `GameConfiguration` gehört zum GameState, weil ihre Werte für genau diese
Spielpartie gelten und beim Fortsetzen erhalten bleiben müssen.

Die spätere Entscheidung
[`Promptprofil und aktuelle Modellwahl`](promptprofil-und-modellwahl.md)
konkretisiert die inzwischen umgesetzte Feldaufteilung: Die Erzählvorgaben
werden als explizites Promptprofil gespeichert, während die aktive Modellwahl
eine globale Systemeinstellung je Aufgabe bleibt.

Sie enthält:

- Sprache;
- ein vollständiges `PromptProfile` mit Erzählstil, Perspektive und
  Steuerungsmodus;
- erzählerische Grenzen und feste Vorgaben;
- ausgewähltes Prompt-Paket und dessen Version.

API-Schlüssel, Anbieter-URLs und laufende Modellaufrufe gehören nicht hinein.

## WorldState

Der `WorldState` ist die strukturierte Wahrheit des Spiels. Dazu gehören:

- Figuren, Orte und Gegenstände;
- Beziehungen und Besitzverhältnisse;
- bestätigte Fakten;
- Wissen einzelner Figuren;
- Regeln und aktuelle Zustände der Welt;
- Haupt- und Nebenziele.

Beispiele sind:

- Almas befindet sich im Dungeon.
- Die Tür zur Schatzkammer ist geschlossen.
- Das magische Schwert liegt auf dem Altar.
- Almas besitzt den eisernen Schlüssel.

## Goals

Ein `Goal` ist ein strukturiertes Ziel des Spiels und gehört ausschließlich in
den WorldState. Es gehört nicht in den StoryState und ist kein Kapitel.

Ein Goal enthält zunächst:

- eine stabile ID;
- die Art `main` oder `side`;
- einen Titel;
- eine Beschreibung;
- den Status `open`, `completed` oder `failed`;
- Verweise auf beteiligte Figuren, Orte oder Gegenstände.

Beispiel:

```text
Hauptziel: Finde das magische Schwert.
Status: open
```

Findet Almas das Schwert, werden beide fachlichen Folgen gespeichert:

- Im WorldState besitzt Almas anschließend das Schwert.
- Das Ziel „Finde das magische Schwert“ erhält den Status `completed`.

Wie dieser Moment erlebt und erzählt wurde, steht dagegen im StoryState.

Prozentwerte, Meilensteine und verschachtelte Teilziele werden zunächst nicht
umgesetzt. Sie sind bewusst zurückgestellt und keine ungeklärte Voraussetzung.

## StoryState

Der `StoryState` enthält ausschließlich die konkrete fortlaufende Geschichte.
Er besteht zunächst aus:

- den vollständig abgeschlossenen StoryTurns;
- einer geordneten Folge unveränderlicher Summary-Segmente;
- optional der persistierten Eröffnungsprosa mit Initialprompt und Zeitpunkt;
- der Nummer des zuletzt abgeschlossenen Zuges.

Die Summary-Segmente decken feste Zugfenster ab und werden append-only an die
Kette angehängt. Die ursprünglich beschlossene rollierende Zusammenfassung
wurde mit TASK-032 durch dieses Segmentmodell ersetzt; die ältere Planung
bleibt im Backlog als historische Vorgeschichte sichtbar.

Nicht enthalten sind:

- Goals;
- Chapters;
- Scenes;
- StoryThreads;
- ein zusätzliches allgemeines StoryEvent;
- strukturierte Weltzustände.

Chapters, Scenes und StoryThreads werden in der ersten Umsetzung bewusst nicht
übernommen. Falls später ein konkreter Bedarf entsteht, können Chapters oder
Scenes StoryTurns gruppieren. Sie dürfen dann keine Informationen aus dem
WorldState doppelt speichern.

## StoryTurn

Ein `StoryTurn` ist ein vollständig abgeschlossener Spielzug. Er enthält:

- ID und fortlaufende Zugnummer;
- `player_input`;
- die erzeugte Erzählung;
- die vorherige GameState-Revision;
- die daraus entstandene GameState-Revision;
- den Abschlusszeitpunkt.

Ein gerade erzeugter oder nur teilweise verarbeiteter Zug ist noch kein
persistierter StoryTurn.

## Was dauerhaft gespeichert wird

Dauerhaft gespeichert werden:

- GameRuns und ihre Mitglieder;
- abgeschlossene GameState-Revisionen;
- die GameConfiguration der Revisionen;
- der WorldState einschließlich Goals;
- aktuelle Story-Zusammenfassung und Zugnummer;
- jeder abgeschlossene StoryTurn genau einmal.

Die vollständigen Turntexte sollen nicht mit jeder GameState-Revision erneut
kopiert werden. Die Persistenz setzt den benötigten StoryState aus den
Revisionsdaten und den bis dahin abgeschlossenen Turns zusammen.

## Was nur vorübergehend existiert

Während eines Spielzugs hält das Backend im Arbeitsspeicher:

```text
zusammengesetzter Prompt
laufender Modellaufruf
empfangene Rohantwort
extrahierter Änderungsvorschlag
Validierungsergebnis
```

Diese Daten werden nicht Teil der Entities und erhalten zunächst keine eigenen
Datenbanktabellen.

Das LLM darf den echten Spielzustand nicht direkt verändern. Es liefert Prosa
und Änderungsvorschläge. Die Anwendung prüft diese Vorschläge, und die Domain
wendet nur erlaubte Änderungen auf die erwartete Revision an.

## Verhalten bei einem Backend-Absturz

Der Modellaufruf und die Auswertung finden außerhalb einer
Datenbanktransaktion statt. Erst am Ende werden der abgeschlossene StoryTurn
und der daraus entstandene GameState gemeinsam gespeichert.

Stürzt das Backend vorher ab, wird der unvollständige Zug verworfen. Das Spiel
wird anschließend beim vorherigen vollständig gespeicherten Zug fortgesetzt.
Eine Wiederaufnahme halbfertiger Workflows wird zunächst bewusst nicht
unterstützt.

## Benutzer und Keycloak

Keycloak bleibt für Anmeldung und Identität verantwortlich. Unsere Datenbank
speichert keine Passwörter.

Zu einem GameRun werden Mitgliedschaften gespeichert. Ein Mitglied wird über
`issuer` und `subject` aus dem Keycloak-Token erkannt. Die Mitgliedschaft kann
zusätzlich eine Rolle im Spiel und die zugeordnete Spielfigur enthalten.

Eine vollständige eigene User-Entität wird zunächst nicht angelegt. Sie kann
später ergänzt werden, wenn die Anwendung eigene Benutzerprofile oder
Einstellungen benötigt.

## Globale Konfiguration und Prompts

Globale Anbieter-, Modell- und Standardkonfigurationen werden zunächst aus
TOML-Dateien geladen. System-Prompts werden als versionierter Dateikatalog im
Repository verwaltet.

- Das vollständige Promptpaket enthält Katalogdaten, Zuordnungen und Texte in
  einer versionierten TOML-Datei.
- Separate Prompt-Textdateien werden für dieses Paket nicht verwendet.
- JSON beschreibt weiterhin die strukturierten Ausgabeformate der
  modellbasierten Extraction-Verträge.
- Statische Einträge verwenden lesbare IDs wie `story.base`.
- Geheimnisse werden getrennt über die Laufzeitumgebung bereitgestellt.

Die Use Cases greifen nur über passende Katalog-Schnittstellen darauf zu. Ob
ein Katalog später aus Dateien oder einer Datenbank kommt, soll für sie keinen
Unterschied machen.

## Bewusst nicht Bestandteil der ersten Umsetzung

Folgende Dinge sollen nicht erneut als offene Voraussetzung behandelt werden:

- Chapters, Scenes und StoryThreads;
- ein separates StoryEvent zusätzlich zum StoryTurn;
- numerischer Goal-Fortschritt, Teilziele und Meilensteine;
- persistierte Workflows und Modellaufrufe;
- MemorySnapshot-Tabellen;
- persistierte ProposedChangeSets und Validierungsergebnisse;
- eine vollständige lokale Userverwaltung;
- Prompt- und Modellkataloge in der Datenbank.

Eine spätere Änderung dieser Entscheidungen braucht einen neuen konkreten
Anwendungsfall und eine bewusste Entscheidung.
