# Frontend-Web

Web-Frontend des Story-Spiels: React 19 + Redux Toolkit (inkl. RTK Query) +
React Router + TypeScript, gebaut mit Vite.

Dies ist der Neuaufbau, der das ursprüngliche MVP-Frontend abgelöst hat (das
alte Frontend liegt zur Referenz unter `../Frontend-Web-old`, siehe dessen
README). Entstanden Stück für Stück nach Plan
`die-app-war-ein-glistening-steele.md`.

## Stack

- React 19 + Vite + TypeScript
- Redux Toolkit + react-redux + RTK Query für State-Management/API-Anbindung
- React Router für Routing (inkl. routenbasiertem Auth-Gate, siehe unten)
- Keycloak (`keycloak-js`) für Login
- Vitest + React Testing Library für Tests

## Entwicklung

```bash
npm install
npm run dev      # Dev-Server
npm run build    # Typecheck + Build
npm run test     # Vitest
npm run lint     # oxlint
```

`.env.development` setzt `VITE_API_BASE_URL` (Backend-Basis-URL). Keycloak-
Variablen (`VITE_KEYCLOAK_URL`/`VITE_KEYCLOAK_REALM`/`VITE_KEYCLOAK_CLIENT_ID`)
haben sinnvolle Defaults für die lokale Docker-Compose-Umgebung (siehe
`src/api/auth.ts`).

Läuft im Docker-Compose-Stack (`../compose.yaml`, Service `frontend`) hinter
nginx unter `storygame.localhost`.

## Struktur

- `src/api/` — typisierter Fetch-Client (`client.ts`), Domain-Typen
  (`types.ts`), Keycloak-Anbindung (`auth.ts`), RTK-Query-Slice
  (`apiSlice.ts`).
- `src/app/` — Redux-Store, typisierte Hooks, `RequireAuth`-Routen-Gate.
- `src/components/` — geteilte UI-Bausteine (Button, Chip, Panel, ImageSlot,
  Paragraphs).
- `src/features/wizard/` — Redux-Slice für den mehrstufigen
  Story-Erstellungs-Assistenten.
- `src/routes/` — die Screens (Landing, Library, Wizard, Play) plus die
  Routentabelle.
- `src/styles/tokens.css` — Design-Tokens (Bordeaux/Pergament-Theme).

## Auth

`/` (Landing) ist ohne Login erreichbar. Alle anderen Routen sind über die
`RequireAuth`-Layout-Route geschützt, die den Keycloak-Login-Redirect erst
beim Betreten einer geschützten Route auslöst (nicht beim App-Start).

## Design

Bordeaux/Pergament-Theme als Default (`dark_fantasy`-Genre), als CSS-Tokens
angelegt, damit ein späteres zweites Genre-Theme ohne Strukturumbau möglich
ist — aktuell ist aber nur dieses eine Theme ausimplementiert. Genre/Ton und
alle weiteren Story-Optionen im Wizard kommen live vom Backend
(`GET /api/v1/prompt-profile`), nicht hartkodiert.
