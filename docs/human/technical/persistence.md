# Persistenz

PostgreSQL speichert abgeschlossene `GameRun`- und `GameState`-Daten. Der
frühere JSON-Persistenzadapter wurde entfernt. Die Application verwendet nur
schmale Ports und bemerkt daher keine PostgreSQL-Details.

## Gespeichertes Modell

Die wichtigsten Tabellen sind:

| Tabelle | Inhalt |
| --- | --- |
| `game_runs` | Lauf, Status, aktuelle Revision und Zeitpunkte |
| `game_run_members` | Keycloak-Identität, Rolle und optionale Spielfigur |
| `game_state_revisions` | unveränderliche Revisionsfolge |
| `game_state_configurations` | Konfiguration je Revision |
| `world_*` | Entitäten, Beziehungen, Fakten, Wissen und Regeln je Revision |
| `world_goals` | Haupt- und Nebenziele je Revision |
| `story_state_metadata` | aktuelle Zusammenfassung und Zugnummer je Revision |
| `story_turns` | jeder abgeschlossene Zug genau einmal |

Die WorldState-Daten werden je Revision als verständlicher relationaler
Snapshot abgelegt. Die vollständigen Turntexte werden dagegen nicht in jeder
Revision kopiert. Beim Laden setzt der Adapter den StoryState aus den bis zur
gewählten Revision sichtbaren StoryTurns und den Metadaten dieser Revision
zusammen.

Es gibt bewusst keine Tabellen für laufende Workflows, Modellaufrufe,
Rohantworten, Extraktionen, MemorySnapshots, ProposedChangeSets oder
Validierungsergebnisse.

## Schreibgrenzen

Die Application besitzt getrennte Operationen für:

- einen neuen GameRun mit vollständiger Revision 1 anlegen;
- GameRun und aktuellen oder historischen GameState laden;
- eine reine Konfigurationsrevision schreiben;
- einen abgeschlossenen StoryTurn mit der resultierenden Revision schreiben.

Beim Turn-Abschluss sperrt PostgreSQL kurz den Kopf des GameRuns und prüft die
erwartete Basisrevision. Neue Revision, WorldState, Story-Metadaten,
StoryTurn und neuer Laufkopf werden in derselben Transaktion gespeichert. Ein
Konflikt oder Fehler rollt alles zurück. Ein LLM-Aufruf findet immer vorher und
außerhalb dieser Transaktion statt.

Revision 1 und reine Konfigurationsrevisionen benötigen keinen StoryTurn.

## Neues Basisschema statt Datenmigration

Das Projekt befindet sich noch am Anfang. Deshalb ersetzt
`001_initial.sql` das bisherige Schema vollständig; es gibt keine
Abwärtskompatibilität und keine Migration bestehender Storygame-Daten.

Eine lokale Datenbank mit dem alten Schema muss vor Verwendung dieses Stands
neu angelegt werden. Das bestehende Volume wird nicht automatisch gelöscht,
weil es eine persistente Benutzerressource ist. Für einen bewussten lokalen
Reset können die Container und das Projekt-Volume entfernt und danach neu
gestartet werden.

## Lokale PostgreSQL-Umgebung

Die Entwicklungsdatenbank wird über `compose.yaml` gestartet. Der Host-Port
ist standardmäßig `5433`:

```bash
docker compose up --detach --wait postgres
```

Danach wird das Basisschema angewendet:

```bash
export STORY_GAME_POSTGRES_DSN=postgresql://story_game:story_game_dev@localhost:5433/story_game
PYTHONPATH=src python -m story_game.infrastructure.persistence.postgres.migrate
```

Die Harness-Standardprüfung erstellt eine eigene kurzlebige PostgreSQL-
Instanz ohne Host-Port und entfernt Container, internes Netzwerk und Daten
nach dem Lauf wieder.
