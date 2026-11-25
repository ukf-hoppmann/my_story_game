# Architektur

<!-- Nur der aktuelle Stand. Historie gehört in die Tagesberichte, Begründungen in die Backlog-Notizen. Verbindliche Regeln: docs/development/architecture.md -->

## Überblick

Die Anwendung ist ein Textabenteuer mit einem Sprachmodell als Erzähler. Ein
Zug besteht aus Erzählung, Extraktion von Zustandsänderungen und deren
fachlicher Freigabe; die Anwendung besitzt den kanonischen Spielzustand, das
Modell schlägt nur vor. Hauptteile sind ein Python-Backend (FastAPI), ein
React-Frontend, PostgreSQL, Keycloak für die Anmeldung und optional Modal für
Szenenbilder. Ein editierbares Übersichtsdiagramm liegt als
[Draw.io-Datei](architecture.drawio) vor: Tabs für Überblick, Domain,
Application, den zeitlichen Ablauf eines Zugs und die LLM-Architektur.

## Leitgedanken

Das Ziel ist kein möglichst kompliziertes Architekturmuster, sondern dass eine
Änderung möglichst wenige Stellen berührt und jeder Baustein für sich
verständlich und testbar bleibt.

- **Fachliche Bereiche statt Sammelklassen:** Die Application ist nach
  Aufgaben gegliedert (Zustandsverwaltung, Zug spielen, Extraktion, …), jeweils
  mit kleinen Operationen. Getrennt wird, wenn Teile unabhängig geändert,
  ersetzt oder getestet werden sollen, nicht um des Musters willen.
- **Einheitlicher Aufruf, konkrete Daten:** Jede Operation hat `apply`; Eingabe
  und Ergebnis sind konkret typisiert. Ein erwartetes Ergebnis ist entweder
  `Success` mit Daten oder `Failure` mit einem konkreten Fehler, nie ein
  Antwortbeutel mit optionalen Feldern
  ([Kompositionsbegriffe](../development/interfaces/application-composition.md)).
- **Sichtbar zusammengesetzte Abläufe:** Die Composition Root verdrahtet
  konkrete Implementierungen, eine Policy entscheidet, *wann* etwas fachlich
  passiert, ein Workflow legt die Reihenfolge fest, eine Operation erledigt
  genau einen Schritt. Die Verdrahtung wird nicht zum Gehirn der Anwendung.
- **Austauschbare Infrastruktur:** Die Application beschreibt über schmale
  Ports, was sie braucht (Spielstand lesen, speichern, Modell aufrufen);
  Datenbank-, Datei- und Modelladapter erfüllen sie. Es gibt bewusst kein
  universelles `IDataSource`.
- **Architektur bleibt veränderbar:** Passt eine Anforderung nicht in die
  Regeln, wird sie nicht umgangen; zuerst wird beschrieben, welche Regel nicht
  passt und wie der Vertrag erweitert werden soll, und der Projekteigner
  entscheidet.

Domainmodell und Persistenz im Detail:
[domain-model.md](../development/interfaces/domain-model.md),
[persistence.md](../development/interfaces/persistence.md).

## Komponenten

| Komponente | Verantwortung | Ort |
|---|---|---|
| Domain | Spielzustand (`WorldState`, `StoryState`, `GameConfiguration`), Invarianten, Vorschlags- und Freigabegrenze | `Backend/src/story_game/domain` |
| Application | Kleine Operationen mit `apply` und Ports: Vorschlag/Bestätigung, Zug spielen, Extraktion, Zusammenfassung, Szenenbild, Prompt- und Modellverwaltung | `Backend/src/story_game/application` |
| API | HTTP-Adapter: Router, Schemas, Fehler-Mapping, Token-Prüfung, Rolle `admin` | `Backend/src/story_game/api` |
| Infrastruktur | Postgres-Adapter und Migrationen, LLM-Adapter (LM Studio, Groq, Gemini), Modal-Bildadapter, Konfiguration, Logging | `Backend/src/story_game/infrastructure` |
| Prompts | Prompt-Paket `story.base`/`1` als TOML; Quelle für den ersten Import in die Datenbank | `Backend/prompts` |
| Web-Frontend | React, Redux Toolkit (RTK Query), react-router; Routen Landing, Bibliothek, Wizard, Play, Einstellungen | `Frontend-Web/src` |
| Keycloak | Anmeldung (OIDC) und Realm-Rolle `admin`; Realm-Import | `configs/keycloak` |
| nginx | Lokaler Proxy: `storygame.localhost` (Frontend), `backend.storygame.localhost` (API), `auth.storygame.localhost` (Keycloak) | `configs/nginx` |
| Story-Starter | CLI für den lokalen Compose-Stack | `story-starter`, `compose.yaml` |

## Datenfluss

Der Browser meldet sich per Keycloak an (`keycloak-js`, stiller
`check-sso` beim Start; die Landing-Page ist ohne Login erreichbar) und ruft
die API mit dem Bearer-Token auf. Ein Zug läuft in der Application als sichtbar
zusammengesetzte Kette: Kontext auswählen → Erzählung erzeugen → Änderungen
extrahieren → fachlich prüfen und freigeben → speichern → bei Bedarf
Zusammenfassungssegment erzeugen. Der Kontext enthält Fakten, Wissen und Ziele
ohne Filter nach Sichtbarkeit; verdeckte Fakten gehen derzeit unmarkiert in den
Prompt (Kennzeichnung offen, TASK-018). Die vorgeschlagenen
Fortsetzungsoptionen eines Zugs gehen nur an den Client und werden nicht
gespeichert. Ist das globale Welt-Tracking aus (vorläufige
Ausnahme für schwache lokale Modelle, Scope `llm-integration` §6c), entfallen
Extraktion und Freigabe: Der Start baut die Welt nur aus den eingegebenen
Figuren, ein Zug speichert eine leere Änderungsmenge. Eine Policy liest die
Einstellung bei jedem Start und Zug neu. Unbekannte Referenzen im Vorschlag verwerfen
nur das betroffene Element (Übergangslösung, TASK-042); andere Verstöße
verwerfen den Zug. Alle Modellaufrufe laufen über Ports; Modell, Temperatur und
Ausgabelänge je Task löst ein Resolver bei jedem Aufruf aus der Datenbank
und dem Katalog in `llm.toml` auf. Szenenbilder laufen asynchron: die API
antwortet mit 202, ein Hintergrundschritt erzeugt über das Modell den Bildprompt,
Modal rendert das Bild, der Client fragt den Status ab.

## Zustand und Speicherung

PostgreSQL ist der einzige persistente Speicher
([persistence.md](../development/interfaces/persistence.md)):

- Spielzustand als unveränderliche Revisionen je Lauf (`game_runs`,
  `game_state_revisions`, `world_*`, `story_turns`, `story_summary_segments`).
- Szenenbilder (`scene_images`, außerhalb des Spielzustands).
- Globaler Schalter für Welt-Tracking (`world_tracking_setting`, höchstens
  eine Zeile; ohne Zeile ist Tracking an).
- System-Prompts (`system_prompts`) und Modellwahl je Task
  (`llm_task_settings`): append-only, je Eintrag genau eine aktive Version;
  beim ersten Start aus TOML übernommen, danach gilt die Datenbank.
- Migrationen liegen unter
  `Backend/src/story_game/infrastructure/persistence/postgres/migrations` und
  laufen beim Start, wenn `STORY_GAME_AUTO_MIGRATE` gesetzt ist.

Vorschläge vor der Bestätigung liegen nur im Prozessspeicher (30 Minuten).
Provider-URLs, Secrets und der Modellkatalog bleiben in Dateien
([Konfiguration](configuration.md)). Im Browser liegen nur Komfortwerte
(`localStorage`, z. B. Fließtext-/Chat-Ansicht).

## Wichtige Entscheidungen

| Entscheidung | Kurzer Grund | Verweis |
|---|---|---|
| Komponierbare Operationsarchitektur mit `apply` und typisierten Ergebnissen | Wenige Änderungsstellen, testbare Bausteine | [Architekturregeln](../development/architecture.md), TASK-006 |
| Anwendung besitzt den Zustand, das Modell schlägt nur vor | Konsistenz und Freigabegrenze | [domain-model.md](../development/interfaces/domain-model.md), [Scope story-turn](../development/architecture/story-turn.md) |
| Ein Zug wird atomar gespeichert; ein gescheiterter Zug hinterlässt nichts | Spielstand bleibt konsistent, kein Wiederaufnehmen halber Abläufe | [Scope persistence](../development/architecture/persistence.md) |
| Zusammenfassung als Kette unveränderlicher Segmente | Kosten pro Zug unabhängig vom Intervall | TASK-032 |
| Szenenbilder abschaltbar und nicht Teil des Spielzustands | Zielbetrieb erreicht Modal ggf. nicht | [Scope llm-integration §7](../development/architecture/llm-integration.md#7-extensibility-without-a-universal-model-service), STORY-012 |
| Prompts und Modellwahl in der Datenbank, Bearbeitung nur mit Rolle `admin` | Änderung zur Laufzeit ohne Neustart, mit Verlauf | [Scope llm-integration §2–3](../development/architecture/llm-integration.md#2-application-owned-prompt-meaning), STORY-013 |
| Neue Optionen nur für Genre, Ton und Prosastil | Struktur der Prompts bleibt serverbestimmt | [http-api.md](../development/interfaces/http-api.md), [Scope prompt-profile](../development/architecture/prompt-profile.md) |

## Verbindliche Regeln

Die Regeln für die KI stehen in [architecture.md](../development/architecture.md)
(Wurzelregeln) und in den Scopes darunter:

| Scope | Gegenstand |
|---|---|
| [llm-integration](../development/architecture/llm-integration.md) | Modellaufrufe, Prompt-Aufbereitung, Provider-Adapter, Extraktion, Vorschlagsbestätigung, abschaltbares Welt-Tracking |
| [story-turn](../development/architecture/story-turn.md) | Kontextauswahl, Extraktion, Freigabe und Zusammenfassung eines Zugs |
| [persistence](../development/architecture/persistence.md) | Atomarer Zug-Commit, Revisionen, nur anhängender Erzähltext |
| [prompt-profile](../development/architecture/prompt-profile.md) | Promptprofil eines Spiels, seine Prüfung und das Prompt-Paket |

Die Schnittstellenbeschreibungen und Kataloge wiederverwendbarer Bausteine
stehen im [Index](../development/interfaces.md).
