# Native UUIDs für interne StableIds

Status: Umgesetzt und am 11.08.2026 verifiziert. Dieses Dokument hält die
Entscheidungen und den ausgeführten Umstellungsumfang fest.

## Ausgangslage

Vor der Umstellung erzeugte `StableId.new()` UUIDv4-Werte, der Konstruktor
akzeptierte jedoch auch beliebigen nicht leeren Text. PostgreSQL speicherte
interne IDs in `TEXT`-Spalten. Dieser inkonsistente Ausgangszustand ist
aufgehoben.

Die Initial-Extraction besitzt bereits die richtige fachliche Trennung: Das
Modell liefert nur kurzlebige `local_ref`, `source_ref`, `target_ref` und
`subject_ref`. Erst die Application löst diese Referenzen auf und erzeugt
StableIds. Dieser Vertrag bleibt erhalten.

Kanonische Evidenz ist nicht Teil dieses Vorhabens. Sie wurde aus `Fact`,
`WorldRule`, API und PostgreSQL entfernt. Ausschließlich `ProposalEvidence`
bleibt als transiente Reviewinformation bestehen.

## Zielbild und Entscheidungsregel

Eine UUID identifiziert ein Objekt, dessen Lebenszyklus das Storygame selbst
besitzt. Fremde, konfigurationsgebundene oder nur lokal innerhalb eines
Requests gültige Referenzen bleiben Text. Dass ein Wert in PostgreSQL
gespeichert wird, macht ihn allein noch nicht zu einer internen Identität.

`StableId` ist ein Domain-Wrapper um `uuid.UUID`. `StableId.new()` erzeugt
UUIDv4; eine explizite Parse-Funktion akzeptiert UUID-Objekte oder kanonische
UUID-Strings und weist andere Werte als Domainfehler ab. `str(stable_id)`
liefert weiterhin die normale Bindestrichschreibweise für Logs, URLs und JSON.
Eigene ID-Klassen pro Entity-Art bleiben außerhalb dieser Umstellung, solange
konkrete Verwechslungen nicht zeigen, dass diese zusätzliche Typtrennung den
Aufwand rechtfertigt.

## ID-Klassifikation

### Interne UUID-Identitäten

| Besitzer | Identität und interne Referenzen |
| --- | --- |
| GameRun | `GameRun.id`, alle `run_id` |
| WorldEntity | `entity_id`, `player_entity_id`, `source_id`, `target_id`, `subject_id`, `actor_id`, `visibility_actor_id`, Goal-Entity-Referenzen |
| EntityLink | `link_id` |
| Fact | `fact_id` und Knowledge-Referenzen darauf |
| WorldRule | `rule_id` |
| Goal | `goal_id` |
| StoryTurn | `turn_id` |

Dieselbe fachliche Identität behält in allen State-Revisionen dieselbe UUID.
Revisionen erzeugen keine neuen IDs für unveränderte Objekte.

`ProposedChangeSet.id`, `ProposedChange.id` und
`ApprovedChangeSet.proposal_id` sind backend-eigene Korrelationsidentitäten
und sind ebenfalls UUIDs, obwohl sie aktuell nicht persistiert werden.
`ProposalEvidence.reference` ist dagegen Text: Seine Bedeutung ist nicht auf
ein kanonisches Storygame-Objekt begrenzt und darf den UUID-Vertrag nicht
verwässern.

### Textuelle Fremd- und Konfigurationsreferenzen

Folgende Werte bleiben ausdrücklich Text:

- Keycloak `issuer` und `subject`;
- logische Modellreferenzen aus `configs/llm.toml`;
- `provider_id` und die vom Provider bestimmte `model_id`;
- Prompt-Paket-ID und -Version;
- Prompt-Task-, Kategorie-, Option- und Directive-IDs;
- die gespeicherten Promptauswahlen `genre`, `tone`, `prose_style`,
  `perspective`, `pacing`, `control_mode`, `player_agency`, `consequence`,
  `challenge` und `content_profile`;
- die lokalen Referenzen eines LLM-Candidates.

Diese Werte sind lesbare Schlüssel versionierter Dateien oder Identitäten
fremder Systeme. PostgreSQL speichert einige von ihnen als Teil eines
reproduzierbaren GameState-Snapshots, besitzt ihren Lebenszyklus aber nicht.

### Werte ohne Identitätscharakter

`StateRevision`, `StorySequence`, Tabellenpositionen, Schema- und
Migrationsversionen bleiben Zahlen beziehungsweise Versionswerte. Status,
Rollen, Arten und Sichtbarkeit bleiben Enums oder textuelle Enumwerte.

## Menschlich lesbare Benennung

Technische UUIDs werden nicht als UI-Namen verwendet. Vorhandene Fachfelder
bleiben verantwortlich:

- `WorldEntity.label` und `aliases`;
- `Goal.title`;
- `Fact.statement` und `WorldRule.statement`;
- Link-Art, Labels der beiden Endpunkte und optionale `description`;
- Sequenz und Abschlusszeitpunkt eines StoryTurns;
- `PlayerCharacterSeed.name`.

`GameRun` besitzt nun `GameRun.name` als erforderlichen, getrimmten Text sowie
`game_runs.name` und das entsprechende API-Feld. Namen müssen nicht eindeutig
sein; die UUID bleibt die einzige technische Identität.

## PostgreSQL-Zielschema

Folgende Spalten sind nativ `UUID`:

- `game_runs.run_id`;
- `game_run_members.run_id` und `player_entity_id`;
- `game_state_revisions.run_id`;
- `game_state_configurations.run_id`;
- `world_entities.run_id` und `entity_id`;
- `world_links.run_id`, `link_id`, `source_id`, `target_id` und
  `visibility_actor_id`;
- `world_facts.run_id`, `fact_id`, `subject_id` und `visibility_actor_id`;
- `world_knowledge.run_id`, `actor_id` und `fact_id`;
- `world_rules.run_id`, `rule_id` und `visibility_actor_id`;
- `world_goals.run_id` und `goal_id`;
- `story_state_metadata.run_id`;
- `story_turns.run_id` und `turn_id`.

`world_goals.related_entity_ids` kann in JSONB keine nativen UUID-Werte
enthalten. Es wurde durch eine geordnete Relation ersetzt:

```text
world_goal_related_entities
├── run_id UUID
├── revision BIGINT
├── goal_id UUID
├── position INTEGER
└── entity_id UUID
```

Ein eindeutiger Positionsschlüssel erhält die Domain-Reihenfolge. Composite
Foreign Keys verbinden die Zuordnung mit Goal und Entity derselben Revision.
Snapshotinterne Link-, Fact-, Knowledge- und Sichtbarkeitsreferenzen sind
ebenfalls durch passende Composite Foreign Keys abgesichert. Die bestehende
Schreibreihenfolge der atomaren Snapshot-Transaktion bleibt erhalten.

`game_run_members.player_entity_id` kann nicht direkt auf
`world_entities` zeigen: Die Mitgliedschaft ist revisionsunabhängig, die
Entity-Zeile dagegen Teil eines revisionierten Snapshots. Die Spalte ist UUID,
bleibt aber zunächst durch die vorhandene Domainprüfung statt durch einen
irreführenden Datenbank-FK abgesichert. Ein unveränderliches Entity-Registry-
Modell wäre eine eigenständige spätere Architekturentscheidung.

## Erzeugung und API-Vertrag

UUIDs werden vor dem Persistenzadapter erzeugt; PostgreSQL ist nicht die
einzige ID-Quelle.

- Application-Workflows verwenden `StableId.new()`, wenn das Backend ein
  kanonisches Objekt anlegt. Die vorhandene Initial-Extraction bleibt ein
  Referenzbeispiel dafür.
- Ein Frontend darf für ausdrücklich dafür vorgesehene Create-Verträge mit
  `crypto.randomUUID()` eine ID vorab erzeugen, etwa für Offline-Erstellung oder
  Idempotenz. Das Backend validiert sie trotzdem als UUID.
- Produktive Create-Endpunkte sollten standardmäßig keine ID verlangen und
  die erzeugte UUID zurückgeben. Der bestehende vollständige `GameDocument`-
  Import bleibt eine technische Testgrenze und akzeptiert nur valide UUIDs.
- Das LLM erzeugt niemals StableIds. Seine lokalen Textreferenzen werden nur
  innerhalb eines Candidates aufgelöst und verlassen diese Grenze nicht.

Die Pydantic-Modelle verwenden `UUID` für alle internen IDs. OpenAPI weist sie
als Strings mit `format: uuid` aus. Pfadparameter werden vor der Application
validiert. JSON-Antworten bleiben interoperable UUID-Strings. Psycopg erhält
und liefert native UUID-Objekte; Textkonvertierungen im Row-Mapping werden auf
Transport- und Ausgabestellen begrenzt.

Die Umstellung ist ein Breaking Change für Clients, die sprechende IDs senden.
Die aktuelle API ist als Testgrenze dokumentiert und wurde direkt ohne
Legacy-Alias-Schicht umgestellt.

## Daten- und Migrationsstrategie

Das Projekt verwendet derzeit ein bewusst ersetzbares Basisschema und fordert
bei inkompatiblen Schemaänderungen den manuellen Neuaufbau der
Entwicklungsdatenbank. Unter dieser bestätigten Annahme wurde
`001_initial.sql` angepasst und keine Upgrade-Migration für bestehende Slugs
angelegt. Die Implementierung hat keine Datenbank und kein Volume automatisch
gelöscht.

Sobald eine erhaltenswerte Umgebung existiert, ist stattdessen eine additive
Migration erforderlich. Sie muss zuerst alle Nicht-UUID-Werte inventarisieren und eine
einheitliche Zuordnung von Altwert zu UUID über alle Revisionen und
Referenztabellen anwenden. Ein direktes `TEXT::UUID` ist für die heutigen
Slug-Fixtures unzulässig.

## Umsetzungsschritte

### 1. Domainvertrag und Benennung

- Ziel: `StableId` streng auf UUID begrenzen und `GameRun.name` einführen.
- Umfang: Domainwerte, Konstruktion, Validierung und Exporte.
- Nicht enthalten: per-Entity ID-Klassen und Datenbankänderungen.
- Abhängigkeiten: keine.
- Abnahme: UUID-Erzeugung und Parsing sind kanonisch; Slugs werden abgelehnt;
  Anzeigenamen bleiben von IDs getrennt.
- Verifikation: fokussierte Domain-Tests.
- Fertig, wenn: alle Domainkonstruktionen den neuen Vertrag verwenden und
  keine kanonische StableId mehr beliebigen Text enthält.

### 2. Application-Erzeugung und transiente Referenzen

- Ziel: Backend-Erzeugung und LLM-lokale Referenzauflösung explizit sichern.
- Umfang: Create-Requests, Proposal-Identitäten und Initial-Extraction.
- Nicht enthalten: neue LLM-Schemas oder persistierte Evidence.
- Abhängigkeiten: Domainvertrag.
- Abnahme: interne Objekte erhalten UUIDs; Candidate-Referenzen bleiben Text;
  `ProposalEvidence.reference` verwendet `StableId` nicht mehr unpräzise.
- Verifikation: Application-Tests mit injizierbarer, deterministischer
  ID-Erzeugung sowie unbekannten und doppelten lokalen Referenzen.
- Fertig, wenn: kein LLM- oder TOML-Schlüssel als StableId interpretiert wird.

### 3. API-Vertrag und Mapper

- Ziel: interne IDs als UUID validieren und als JSON-Strings ausgeben.
- Umfang: Schemas, Pfadparameter, Mapper, GameRun-Name und OpenAPI.
- Nicht enthalten: allgemeiner produktiver CRUD-Ausbau.
- Abhängigkeiten: Domainvertrag.
- Abnahme: OpenAPI zeigt UUID-Formate; Nicht-UUIDs erhalten 422; Roundtrips
  bewahren UUID und Anzeigename.
- Verifikation: API-, Mapper- und OpenAPI-Tests.
- Fertig, wenn: jede kanonische API-ID exakt klassifiziert ist.

### 4. PostgreSQL-Schema und Adapter

- Ziel: interne Identitäten nativ als UUID persistieren.
- Umfang: Basisschema, Goal-Entity-Relation, Reader, Writer, Store und Mapping.
- Nicht enthalten: automatischer Reset oder Upgrade erhaltenswerter Daten.
- Abhängigkeiten: Domainvertrag und bestätigte Datenstrategie.
- Abnahme: PostgreSQL meldet für alle internen ID-Spalten `uuid`; textuelle
  Fremdreferenzen bleiben `text`; Snapshots und historische Revisionen laden
  unverändert.
- Verifikation: isolierte PostgreSQL-Integrationstests einschließlich
  Schema-Introspektion und Goal-Referenzreihenfolge.
- Fertig, wenn: keine interne persistierte ID mehr als TEXT oder ID-JSONB
  gespeichert wird.

### 5. Fixtures, Dokumentation und Gesamtintegration

- Ziel: alle Beispiele und Betriebsinformationen an den Vertrag anpassen.
- Umfang: Test-Fixtures, technische Domain-, API- und Persistenzdokumentation,
  Beispiel-JSON und relevante geplante Dokumente.
- Nicht enthalten: Umschreiben historischer Abschlussberichte.
- Abhängigkeiten: alle vorherigen Schritte.
- Abnahme: Beispiele verwenden UUIDs und getrennte Namen; experimentelle
  `new:`-Dokumente sind klar als lokale Referenzkonvention eingeordnet.
- Verifikation: `git diff --check`, selektive Tests während der Entwicklung und
  ein vollständiger Harness-Standardlauf über das integrierte Ergebnis.
- Fertig, wenn: Dokumentation und beobachtbarer Vertrag nicht widersprechen.

Die Schritte bleiben in einem Change integriert, weil Domain-, API- und
PostgreSQL-Typen gemeinsam atomar konsistent werden müssen. Ihre Reihenfolge
reduziert Kontextverlust; die gemeinsame Schlussprüfung verhindert, dass ein
einzeln erfolgreicher Teilvertrag inkompatibel integriert wird.

## Ergebnis und verbleibende Grenzen

- Die direkte Baseline-Änderung ohne Upgrade-Migration wurde bestätigt. Es
  wurde keine Datenbank und kein Volume automatisch zurückgesetzt.
- Der API-Vertrag wurde bewusst ohne Legacy-Alias-Schicht umgestellt.
- UUID-Typen allein beweisen keine fachliche Referenzgültigkeit; Domainregeln
  und geeignete Composite Foreign Keys bleiben notwendig.
- `player_entity_id` bleibt ohne separates Entity-Registry-Modell nur in der
  Domain vollständig referenziell prüfbar.
- UUIDv7 wird nicht eingeführt: UUIDv4 ist bereits vorhanden, portabel und für
  das aktuelle Volumen ausreichend. Eine spätere Sortier- oder Indexanforderung
  kann diesen Entscheid neu öffnen.

## Erfüllte Gesamt-Abnahmekriterien

Die Kriterien sind erfüllt: Alle backend-eigenen kanonischen IDs sind in Domain
und API UUID-validiert und werden in PostgreSQL nativ als UUID gespeichert.
TOML-, Keycloak-, Provider-, Modell- und LLM-lokale Referenzen bleiben Text,
GameRuns besitzen einen getrennten Anzeigenamen, historische
Snapshotbeziehungen roundtrippen korrekt und die vollständige isolierte
Harness-Verifikation ist erfolgreich.
