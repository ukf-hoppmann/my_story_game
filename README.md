# my_story_game

Ein KI-gestütztes Textabenteuer. Eine Spielerin oder ein Spieler beschreibt
eine Ausgangslage, ein Sprachmodell erzählt die Geschichte Zug für Zug, und die
Anwendung hält den Spielzustand (Figuren, Orte, Fakten, Ziele) als kanonischen
Zustand selbst fest. Zu jeder Szene lässt sich optional ein Bild erzeugen.

## Voraussetzungen

- Docker mit Docker Compose
- Python 3.13 (nur für den Starter `./story-starter` und Backend-Tests)
- Node 20 (nur für Frontend-Tests außerhalb von Docker)
- Mindestens ein Sprachmodell-Anbieter: LM Studio lokal (Standard), Groq oder
  Gemini (API-Key nötig, siehe [Konfiguration](docs/techdocs/configuration.md))
- Optional für Szenenbilder: ein Modal-Zugang

## Installation

1. Repository klonen.
2. Geheimnisse anlegen: `Backend/configs/llm.secrets.toml` aus
   `llm.secrets.toml.example` kopieren (nur nötig für Groq/Gemini) und
   `Backend/configs/scene_image.secrets.toml` aus
   `scene_image.secrets.toml.example` (nur für Szenenbilder).
3. Für lokale Modelle LM Studio starten und das gewünschte Modell laden
   ([LM Studio](docs/techdocs/operations/lmstudio.md)).

## Schnellstart

```bash
./story-starter start
```

Danach ist die App unter `http://storygame.localhost/` erreichbar. Test-Logins
gibt es im lokalen Keycloak (`TestAdmin` hat zusätzlich die Rolle `admin` und
sieht die Einstellungsseite), siehe
[Keycloak](docs/techdocs/operations/keycloak.md). Weitere Befehle
(`stop`, `down`, `upgrade`, `logs`, …) beschreibt der
[Story-Starter](docs/techdocs/operations/story-starter.md).

Tests:

```bash
cd Backend && pytest
cd Frontend-Web && npm test
```

## Dokumentation

- [Architektur](docs/techdocs/architecture.md)
- [Schnittstellen](docs/techdocs/interfaces.md)
- [Konfiguration](docs/techdocs/configuration.md)
- [Betrieb](docs/techdocs/operations.md) mit den Anleitungen je Thema unter
  `docs/techdocs/operations/`
- Verbindliche Architekturregeln und Schnittstellenbeschreibungen für die KI:
  [docs/development/architecture.md](docs/development/architecture.md),
  [docs/development/interfaces.md](docs/development/interfaces.md)
