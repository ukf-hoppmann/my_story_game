# Frontend-Web

React + Vite + TypeScript. Spricht gegen die `Backend`-API unter
`/api/v1/runs` (siehe [`../docs/human/technical/api.md`](../docs/human/technical/api.md)).

## Lokal starten

Backend zuerst separat starten (aus dem Repo-Root):

```bash
./story-starter
```

Dann in diesem Verzeichnis:

```bash
npm install
npm run dev
```

Die App läuft unter `http://localhost:5173` und ruft die API standardmäßig
unter `http://localhost:8000` auf (`.env.development`,
`VITE_API_BASE_URL`). Das Backend erlaubt diesen Ursprung per CORS
(`STORY_GAME_CORS_ALLOWED_ORIGINS`, Default `http://localhost:5173`).

## Struktur

```
src/
  api/
    client.ts        Fetch-Wrapper, Fehler-Envelope-Mapping, Auth-Injection-Point
    types.ts          Handgeschriebene Typen passend zu den Backend-Schemas
    useApiRequest.ts   Kleiner Hook für Lade-/Erfolg-/Fehlerzustände
  screens/
    RunsListScreen.tsx     Eigene Vorlagen (DRAFT) und aktive Spiele (ACTIVE)
    StartDraftScreen.tsx    Neue Vorlage erzeugen + sofort als Spiel abzweigen
    PlayScreen.tsx           Laden, ggf. Spiel starten, Züge spielen
```

Kein Router (nur drei Screens, linearer Fluss), kein OpenAPI-Codegen
(Typen von Hand gepflegt) — Begründung siehe Projektplan. Noch kein eigenes
Dockerfile/Compose-Service; produktionsreifer Build folgt später.

## Bekannte Lücken (MVP)

- Kein visuelles Design (nur funktionale Basis-Styles in `src/index.css`).
- Kein Turn-Historie-Scroll-/Paginierungsverhalten für lange Läufe.
- Kein Umgang mit `PAUSED`/`COMPLETED`-Status (Backend setzt diese nie).
