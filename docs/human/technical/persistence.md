# Persistenz

PostgreSQL speichert abgeschlossene `GameRun`- und `GameState`-Daten. Der
frühere JSON-Persistenzadapter wurde entfernt. Die Application verwendet nur
schmale Ports und bemerkt daher keine PostgreSQL-Details.

## Gespeichertes Modell

Die wichtigsten Tabellen sind:

| Tabelle | Inhalt |
| --- | --- |
| `game_runs` | UUID, Anzeigename, Status, aktuelle Revision und Zeitpunkte |
| `game_run_members` | Keycloak-Identität, Rolle und optionale Spielfigur |
| `game_state_revisions` | unveränderliche Revisionsfolge |
| `game_state_configurations` | Konfiguration je Revision |
| `world_*` | Entitäten, Beziehungen, Fakten, Wissen und Regeln je Revision |
| `world_goals` | Haupt- und Nebenziele je Revision |
| `world_goal_related_entities` | geordnete Goal-Verweise auf Entities derselben Revision |
| `world_scene_locations` | geordnete Schauplätze der Erzählung je Revision |
| `story_state_metadata` | aktuelle Zusammenfassung und Zugnummer je Revision |
| `story_turns` | jeder abgeschlossene Zug genau einmal |

Die WorldState-Daten werden je Revision als verständlicher relationaler
Snapshot abgelegt. Die vollständigen Turntexte werden dagegen nicht in jeder
Revision kopiert. Beim Laden setzt der Adapter den StoryState aus den bis zur
gewählten Revision sichtbaren StoryTurns und den Metadaten dieser Revision
zusammen.

`game_state_configurations` speichert `language`, die zehn expliziten
`PromptProfile`-Options-IDs, `narrative_boundaries` sowie Paket-ID und
Paketversion. Es speichert weder allgemeine Stil-IDs noch Modellreferenzen.

Es gibt bewusst keine Tabellen für laufende Workflows, Modellaufrufe,
Rohantworten, Extraktionen, MemorySnapshots, ProposedChangeSets oder
Validierungsergebnisse.

Alle internen Identitäts- und Referenzspalten verwenden den nativen
PostgreSQL-Typ `UUID`. Snapshotinterne Beziehungen sind über zusammengesetzte
Foreign Keys an dieselbe `(run_id, revision)` gebunden. Goal-Entity-Verweise
liegen deshalb nicht als String-Liste in JSONB, sondern geordnet in
`world_goal_related_entities`.

`world_scene_locations` folgt demselben Muster: die Reihenfolge liegt in
`position`, der erste Eintrag ist der Hauptschauplatz, und ein zusammengesetzter
Foreign Key bindet jeden Schauplatz an eine `world_entities`-Zeile derselben
Revision. Die Tabelle ist keine Dopplung der `located_in`-Zeilen in
`world_links`: diese halten fest, wo eine Entität ist, jene, wohin die Erzählung
blickt. Im Director Mode fallen beide legitim auseinander.

`game_run_members.player_entity_id` ist ebenfalls UUID, besitzt jedoch keinen
Foreign Key auf `world_entities`: Eine Mitgliedschaft ist nicht revisioniert,
eine Entity-Zeile dagegen immer Teil eines konkreten Snapshots. Die Domain
prüft die Zuordnung. Ein Datenbank-FK würde zuerst eine separate,
unveränderliche Entity-Registry erfordern.

Text bleiben insbesondere Keycloak `issuer`/`subject`, Prompt-Paket-ID und
-Version sowie die gespeicherten Promptprofil-Optionen. PostgreSQL speichert
diese Werte, besitzt aber nicht ihre Identität.

## Schreibgrenzen

Die Application besitzt getrennte Operationen für:

- `InitializeGameRun`: Story- und WorldState-Initialisierung ausführen und
  einen neuen GameRun mit vollständiger Revision 1 atomar anlegen. Der Run
  startet als `DRAFT`; die Initiator-Identität wird als `OWNER` gespeichert.
  Im Player Mode wird die einzige `ActorRole.PLAYER`-Entität über ihre UUID als
  `player_entity_id` gebunden. Der Director Mode erlaubt keine solche Bindung.
- `StartPlaythrough`: eine `DRAFT`-Vorlage laden und als neuen, unabhängigen
  GameRun im Status `ACTIVE` (eigene `run_id`, wieder Revision 1) atomar
  anlegen — über denselben `CreateGameRun`-Port wie `InitializeGameRun`. Die
  Quell-Vorlage bleibt unverändert und kann beliebig oft erneut abgezweigt
  werden. Nur `DRAFT`-Läufe können Quelle eines Abzweigs sein.
- `CreateGameRun`: den bereits erzeugten Run-State über den Persistenzport
  validieren und schreiben;
- GameRun und aktuellen oder historischen GameState laden;
- alle Läufe einer Identität auflisten (`ListPlayableRuns` /
  `PlayableRunLister.list_for_member`) — liest nur `game_runs` und
  `game_run_members`, nicht den vollen WorldState-Snapshot pro Lauf. Ein
  zusätzlicher Index `game_run_members_issuer_subject_idx` auf
  `(issuer, subject)` trägt diese Abfrage; der Primärschlüssel allein
  (`run_id, issuer, subject`) unterstützt sie nicht effizient;
- eine reine Konfigurationsrevision schreiben;
- einen abgeschlossenen StoryTurn mit der resultierenden Revision schreiben
  — nur gegen einen `ACTIVE`-Lauf; ein Zug gegen eine `DRAFT`-Vorlage wird
  bereits in der Application abgewiesen, bevor ein Modellaufruf stattfindet.

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
