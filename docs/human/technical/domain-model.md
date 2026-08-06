# Domainmodell des Storygames

Die Domain-Schicht beschreibt den dauerhaft gültigen Spielstand. Sie kennt
weder HTTP und PostgreSQL noch Keycloak oder einen konkreten LLM-Anbieter.

## Gesamtstruktur

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
        ├── aktuelle Zusammenfassung
        └── aktuelle Zugnummer
```

`GameRun` ist die konkrete Spielpartie. Er hält den Status `draft`, `active`,
`paused` oder `completed`, die Mitglieder und den Verweis auf die aktuelle
Revision. Ein Mitglied wird durch `issuer` und `subject` aus Keycloak erkannt,
hat die Spielrolle `owner` oder `player` und kann einer Spielfigur im
WorldState zugeordnet sein. Passwörter werden nicht im Storygame gespeichert.

`GameState` ist ein unveränderlicher, revisionierter Stand innerhalb dieses
Laufs. Er enthält genau die Konfiguration, die strukturierte Welt und die
konkrete bisher erzählte Geschichte. Eine vollständig gespeicherte Revision
reicht aus, um das Spiel fortzusetzen.

## GameConfiguration

Die `GameConfiguration` hält die für diese Partie aufgelösten Einstellungen:

- Sprache, Erzählstil, Perspektive und Steuerungsmodus;
- erzählerische Grenzen;
- semantische Modell-IDs für Story, Extraktion und Zusammenfassung;
- ID und Version des verwendeten Prompt-Pakets.

Provider-URLs, Zugangsdaten, Rohprompts und laufende Modellaufrufe gehören
nicht in diesen Zustand. Globale Kataloge werden später über austauschbare
Infrastructure-Adapter angebunden.

## WorldState

Der `WorldState` ist die strukturierte Wahrheit des Spiels. Er enthält
Entitäten wie Figuren, Orte und Gegenstände sowie ihre Beziehungen, bestätigte
Fakten, Wissen einzelner Akteure und Weltregeln. Inventar und Aufenthaltsort
werden aus Beziehungen abgeleitet und nicht doppelt geführt.

`Goal` gehört ausschließlich hierher. Ein Ziel enthält eine stabile ID, die Art
`main` oder `side`, Titel, Beschreibung, den Status `open`, `completed` oder
`failed` und optionale Verweise auf beteiligte WorldEntities. Prozentwerte,
Meilensteine und verschachtelte Teilziele gibt es zunächst nicht.

## StoryState

Der `StoryState` ist die konkrete Prosa-Chronologie. Er enthält nur:

- vollständig abgeschlossene `StoryTurn`-Werte;
- eine aktuelle rollierende Textzusammenfassung;
- die Nummer des letzten abgeschlossenen Zugs.

Ein `StoryTurn` verbindet `player_input` und Erzählung mit seiner fortlaufenden
Sequenz, der Basisrevision, der resultierenden Revision und dem
Abschlusszeitpunkt. Ein Turn ist erst dann Teil der Domain-Historie, wenn er
vollständig abgeschlossen wurde.

Goals, Chapters, Scenes, StoryThreads und ein zusätzliches allgemeines
StoryEvent sind bewusst nicht Teil des StoryState. Strukturierte Tatsachen wie
Ort, Besitz oder eine geöffnete Tür bleiben im WorldState.

## Zustandsänderungen

Ein LLM darf den Zustand nicht direkt verändern. Ein unbestätigter
`ProposedChangeSet` ist ein vorübergehender Application-Wert. Erst die
Anwendung prüft den Vorschlag und erzeugt daraus einen `ApprovedChangeSet` mit
typisierten Domain-Operationen.

Die Domain akzeptiert nur diesen freigegebenen Änderungssatz auf der erwarteten
Revision. Beim Abschluss eines Zugs werden World-Änderungen, StoryTurn,
Zusammenfassung und neue Revision gemeinsam gebildet. Persistiert werden sie
anschließend in einer Datenbanktransaktion.

Prompt-Aufbau, Modellaufruf, Rohantwort, Extraktion, Vorschlag und
Validierungsergebnis bleiben außerhalb des persistierten Domainzustands.
