# Persistenz

PostgreSQL speichert abgeschlossene `GameRun`- und `GameState`-Daten. Der
frühere JSON-Persistenzadapter wurde entfernt. Die Application verwendet nur
schmale Ports und bemerkt daher keine PostgreSQL-Details.

## Gespeichertes Modell

Die wichtigsten Tabellen sind:

| Tabelle | Inhalt |
| --- | --- |
| `game_runs` | UUID, Anzeigename, Status, aktuelle Revision und Zeitpunkte |
| `game_run_members` | Keycloak-Identität und Rolle |
| `game_run_member_controlled_entities` | geordnete, gesteuerte Figuren je Mitgliedschaft (0..n) |
| `game_state_revisions` | unveränderliche Revisionsfolge |
| `game_state_configurations` | Konfiguration je Revision |
| `world_*` | Entitäten, Beziehungen, Fakten, Wissen und Regeln je Revision |
| `world_goals` | Haupt- und Nebenziele je Revision |
| `world_goal_related_entities` | geordnete Goal-Verweise auf Entities derselben Revision |
| `world_scene_locations` | geordnete Schauplätze der Erzählung je Revision |
| `story_state_metadata` | Eröffnungsdaten und Zugnummer je Revision |
| `story_summary_segments` | unveränderliche Summary-Segmente mit Zugfenster und Revision |
| `story_turns` | jeder abgeschlossene Zug genau einmal |

Die WorldState-Daten werden je Revision als verständlicher relationaler
Snapshot abgelegt. Die vollständigen Turntexte und Summary-Segmente werden
dagegen nicht in jeder Revision kopiert. Beim Laden setzt der Adapter den
StoryState aus den bis zur gewählten Revision sichtbaren StoryTurns,
`story_summary_segments` und den Metadaten dieser Revision zusammen.

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

`game_run_member_controlled_entities.entity_id` ist ebenfalls UUID, besitzt
jedoch keinen Foreign Key auf `world_entities`: Eine Mitgliedschaft ist nicht
revisioniert, eine Entity-Zeile dagegen immer Teil eines konkreten
Snapshots. Die Domain prüft die Zuordnung. Ein Datenbank-FK würde zuerst
eine separate, unveränderliche Entity-Registry erfordern. Eine Mitgliedschaft
kann null, eine oder mehrere Figuren steuern (geordnet über `position`) —
ursprünglich eine einzelne optionale Spalte `game_run_members.player_entity_id`,
bewusst zu dieser n:m-Tabelle verallgemeinert
(`003_controllable_characters.sql`).

Text bleiben insbesondere Keycloak `issuer`/`subject`, Prompt-Paket-ID und
-Version sowie die gespeicherten Promptprofil-Optionen. PostgreSQL speichert
diese Werte, besitzt aber nicht ihre Identität.

## Szenenbilder

Die Tabelle `scene_images` (`006_scene_images.sql`) hält je Bild Lauf,
Zugnummer, Status (`pending`/`ready`/`failed`), die gewählten Optionen
(Modell, Refine, Seed, Größe), die Prompts, die Fehlermeldung und die
Bilddaten (`bytea`) samt Content-Type. Sie gehört nicht zum kanonischen
GameState: kein Revisionsbezug, kein Eintrag im Spielzustand. `ON DELETE
CASCADE` am Lauf. Check-Constraints erzwingen, dass nur `ready` Bilddaten und
nur `failed` eine Fehlermeldung hat. Lesen joint immer `game_run_members`, ein
Nicht-Mitglied sieht dasselbe wie bei einem fehlenden Bild. Der Adapter ist
`PostgresSceneImageStore`.

## System-Prompts

Die Tabelle `system_prompts` (`007_system_prompts.sql`) ersetzt zur Laufzeit
die TOML-Dateien unter `Backend/prompts/` als Quelle der Prompts. Je Zeile
eine Version eines Eintrags: `version_id` (UUID), `package_id`,
`package_version`, `entry_kind` (`task`, `option`, `directive`), `entry_key`
(spiegelt die TOML-Struktur: Task-ID, `<kategorie>/<option>`, Direktiven-ID),
`entry_text`, `sort_position`, `is_default` (Standardoption einer Kategorie),
`task_ids` (Aufgaben einer Direktive), `source`, `created_at`, `created_by`
(Benutzername des Bearbeiters, ersatzweise sein Subject; bei `toml_seed` leer) und `is_active`.

- **Append-only:** Texte werden nie überschrieben. Eine Änderung oder ein
  Reset deaktiviert die aktive Zeile und fügt in derselben Transaktion eine
  neue aktive ein; ein partieller Unique-Index erzwingt genau eine aktive
  Version je Eintrag.
- **Seed:** Beim Start importiert die API jedes Paket unter
  `STORY_GAME_PROMPT_ROOT`, zu dem die Datenbank noch keine Version hat
  (`source = toml_seed`). Danach überschreibt ein Neustart nie Änderungen.
  Eine neue Datenbank oder ein geleerter Bestand liest wieder die TOML.
- **Reset:** `toml_reset` spielt den Originaltext aus der TOML als neue
  Version ein; die Bearbeitungen bleiben im Verlauf.
- **Struktur** (Kategorien, Standardoptionen, Direktiven-Zuordnung) wird beim
  Seed aus der TOML übernommen und nicht über die UI geändert.

## Modellwahl je Task

Die Tabelle `llm_task_settings` (`008_llm_task_settings.sql`) hält die
Modellwahl nach demselben Muster wie `system_prompts`: je Zeile eine Version
eines Tasks (`story`, `extraction`, `summary`, `scene_image`) mit `version_id`
(UUID), `model_ref` (logische ID eines Modells aus dem Katalog in
`configs/llm.toml`), `temperature`, `max_output_tokens` (beide optional),
`source` (`toml_seed`, `ui`, `toml_reset`), `created_at`, `created_by`
(Benutzername) und `is_active`.

- **Append-only** mit genau einer aktiven Version je Task (partieller
  Unique-Index); eine Änderung deaktiviert die aktive Zeile und fügt in
  derselben Transaktion eine neue ein.
- **Seed:** Beim Start wird für jeden Task ohne gespeicherte Version die
  Vorgabe aus `[task_models]` und `[generation_options]` übernommen. Danach
  überschreibt ein Neustart nie eine Wahl aus der UI.
- **Nicht in der Datenbank:** Provider, URLs, Secrets und der Modellkatalog.
  Der Laufzeit-Resolver liest bei jedem Aufruf die aktive Zeile und löst
  `model_ref` gegen den frisch gelesenen Katalog auf; fehlt das Modell dort
  inzwischen, scheitert der Aufruf mit einem Konfigurationsfehler.

## Schreibgrenzen

Die Application besitzt getrennte Operationen für:

- `ProposeGameRun`/`ConfirmGameRunProposal`: Story- und
  WorldState-Initialisierung ausführen (`ProposeGameRun`, persistiert
  nichts, nur transient im `InitialProposalStore` gehalten) und den vom
  Aufrufer entschiedenen Vorschlag danach als neuen GameRun mit
  vollständiger Revision 1 atomar anlegen (`ConfirmGameRunProposal`). Der
  Run startet als `DRAFT`; die Initiator-Identität wird als `OWNER`
  gespeichert. Jede vom Aufrufer als `player` entschiedene Figur wird über
  ihre UUID in `game_run_member_controlled_entities` gebunden — null, eine
  oder mehrere, je nach Entscheidung.
- `StartPlaythrough`: eine `DRAFT`-Vorlage laden und als neuen, unabhängigen
  GameRun im Status `ACTIVE` (eigene `run_id`, wieder Revision 1) atomar
  anlegen — über denselben `CreateGameRun`-Port wie `ConfirmGameRunProposal`. Die
  Quell-Vorlage bleibt unverändert und kann beliebig oft erneut abgezweigt
  werden. Nur `DRAFT`-Läufe können Quelle eines Abzweigs sein, und nur durch
  eine Identität, die bereits Mitglied der Quell-Vorlage ist (geprüft von
  `LoadGame`, siehe unten).
- `CreateGameRun`: den bereits erzeugten Run-State über den Persistenzport
  validieren und schreiben;
- GameRun und aktuellen oder historischen GameState laden — nur für eine
  aufrufende Identität, die Mitglied dieses GameRuns ist (`LoadGame` prüft
  das zentral, für alle Aufrufer: direktes Laden, Zug spielen, Abzweigen);
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
Ein Summary-Segment entsteht nur an einer konfigurierten Summary-Grenze und
wird einmalig eingefügt; bereits vorhandene Segmente werden nicht aktualisiert.

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
