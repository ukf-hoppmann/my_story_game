# Domainmodell des Storygames

Die Domain-Schicht beschreibt den dauerhaft gültigen Spielstand. Sie kennt
weder HTTP und PostgreSQL noch Keycloak oder einen konkreten LLM-Anbieter.

## Gesamtstruktur

```text
GameRun
├── UUID und Anzeigename
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

`GameRun` ist die konkrete Spielpartie. Er besitzt eine technische UUID und
einen davon getrennten, nicht eindeutigen Anzeigenamen. Er hält den Status
`draft`, `active`, `paused` oder `completed`, die Mitglieder und den Verweis auf
die aktuelle Revision. Ein Mitglied wird durch `issuer` und `subject` aus
Keycloak erkannt, hat die Spielrolle `owner` oder `player` und kann einer
Spielfigur im WorldState zugeordnet sein. Passwörter werden nicht im Storygame
gespeichert.

Alle vom Storygame kontrollierten kanonischen Identitäten werden durch
`StableId` als `uuid.UUID` modelliert. Dazu gehören GameRuns, WorldEntities,
EntityLinks, Facts, WorldRules, Goals, StoryTurns und ihre internen
Referenzen. Neue Werte entstehen mit UUIDv4 vor dem Persistenzadapter; eine
lesbare Bezeichnung liegt stattdessen in `GameRun.name`, `WorldEntity.label`,
`Goal.title` oder den jeweiligen Beschreibungsfeldern.

Keycloak-Identitäten, Prompt-Paket-, Provider- und Modellkennungen,
Promptprofil-Optionen sowie lokale Referenzen aus einem LLM-Candidate bleiben
Text. Sie gehören fremden Systemen oder versionierten Konfigurationen und sind
keine vom Storygame besessenen Identitäten.

`GameState` ist ein unveränderlicher, revisionierter Stand innerhalb dieses
Laufs. Er enthält genau die Konfiguration, die strukturierte Welt und die
konkrete bisher erzählte Geschichte. Eine vollständig gespeicherte Revision
reicht aus, um das Spiel fortzusetzen.

## GameConfiguration

Die `GameConfiguration` hält die für diese Partie aufgelösten Einstellungen:

- Sprache;
- ein vollständiges `PromptProfile` mit Genre, Ton, Prosa-Stil, Perspektive,
  Tempo, Steuerungsmodus, Spielerautonomie, Konsequenz, Herausforderung und
  Inhaltsprofil;
- erzählerische Grenzen;
- ID und Version des verwendeten Prompt-Pakets.

Die zehn lokalen Options-IDs werden vollständig je Revision gespeichert und
vor dem Schreiben gegen das referenzierte Paket validiert. Globale aktive
Modelle für Story, Extraction und Summary gehören dagegen zu
`configs/llm.toml`, nicht zu einer Partie.

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

### Szenenzeiger

`scene_location_ids` ist eine geordnete Liste von Orts-IDs und benennt, wo die
Erzählung gerade spielt. Der erste Eintrag ist der Hauptschauplatz; weitere
Einträge erlauben es, zwischen Handlungssträngen zu schneiden. Jede ID muss auf
eine vorhandene Entität vom Typ `location` zeigen, Duplikate sind unzulässig.
`primary_scene_location()` liefert den Hauptschauplatz oder `None`.

Das ist bewusst **keine** Dopplung der `located_in`-Beziehungen. Beide Angaben
beantworten verschiedene Fragen:

- `located_in` sagt, **wo eine Entität ist**.
- `scene_location_ids` sagt, **wohin die Erzählung blickt**.

Im Director Mode fallen beide legitim auseinander, weil eine Szene erzählt
werden kann, in der die gesteuerte Figur gar nicht vorkommt. Genau deshalb
lässt sich der Schauplatz nicht zuverlässig aus den Aufenthaltsorten ableiten
und braucht eine eigene Aussage. Der Zeiger darf deshalb nicht als redundanter
Zustand entfernt werden.

Den ersten Wert setzt die initiale WorldState-Extraktion aus der
Eröffnungsprosa. Für reguläre Züge stehen `SetSceneLocations` und `RemoveFact`
als freigegebene Zustandsoperationen zur Verfügung; die Turn-Extraction kann
damit Schauplätze fortschreiben und nicht mehr geltende Fakten entfernen.

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

Prompt-Auflösung, Modellaufruf, Rohantwort, Extraktion, Vorschlag und
Validierungsergebnis bleiben außerhalb des persistierten Domainzustands.

Die unterstützten Operationen sind: Entität anlegen und aktualisieren,
Beziehung hinzufügen und entfernen, Tatsache hinzufügen und entfernen, Wissen
gewähren, Ziel anlegen und aktualisieren sowie den Schauplatz setzen.

`RemoveFact` gibt es, weil Tatsachen sonst nur wachsen könnten. Eine im Spiel
aufgeschlossene Tür würde sonst dauerhaft als verschlossen im Weltzustand
stehen und jedem weiteren Prompt widersprechen. Wird eine Tatsache entfernt,
verschwindet das Wissen darüber mit ihr: ein Akteur kann nichts wissen, das die
Welt nicht mehr enthält.

`SetSceneLocations` bewegt den Szenenzeiger weiter. Ohne diese Operation bliebe
der Schauplatz dauerhaft beim Eröffnungsort. Eine leere Liste löscht die Szene.
