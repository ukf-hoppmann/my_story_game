# Frontend-Next

Neuaufbau des Web-Frontends (React + Redux Toolkit + React Router), siehe
Plan `die-app-war-ein-glistening-steele.md`. Arbeitsname bis zur Ablösung von
`../Frontend-Web` (Schritt 12 der Roadmap).

## Stack

- React 19 + Vite + TypeScript (gleiche Grundkonventionen wie `Frontend-Web`)
- Redux Toolkit + react-redux für State-Management/API-Anbindung
- React Router für echtes Routing
- Vitest + React Testing Library für Tests

## Entwicklung

```bash
npm install
npm run dev      # Dev-Server
npm run build    # Typecheck + Build
npm run test     # Vitest
npm run lint     # oxlint
```

`.env.development` setzt `VITE_API_BASE_URL` (Backend-Basis-URL). Weitere
Umgebungsvariablen (Keycloak) kommen in Schritt 2 der Roadmap dazu.

## Stand

Aktuell nur das Grundgerüst (Schritt 0 der Roadmap): leerer Redux-Store,
leeres Routing, Test-Setup. Alle Screens/Design-Tokens/Features folgen in den
weiteren Schritten.
