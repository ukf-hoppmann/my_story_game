import { useEffect, useState } from "react";
import { checkHealth } from "./api/client";
import { currentUsername, logout } from "./api/auth";
import { RunsListScreen } from "./screens/RunsListScreen";
import { StartDraftScreen } from "./screens/StartDraftScreen";
import { PlayScreen } from "./screens/PlayScreen";
import type { RunSummary } from "./api/types";

type View = { name: "list" } | { name: "start" } | { name: "play"; runId: string };

function ApiHealthBanner() {
  const [status, setStatus] = useState<"checking" | "ok" | "unreachable">("checking");

  useEffect(() => {
    checkHealth()
      .then(() => setStatus("ok"))
      .catch(() => setStatus("unreachable"));
  }, []);

  if (status !== "unreachable") return null;
  return (
    <div className="error-banner">
      Backend nicht erreichbar. Läuft <code>./story-starter</code>?
    </div>
  );
}

function CurrentUserBadge() {
  const username = currentUsername();
  if (!username) return null;
  return (
    <div className="current-user-badge">
      Angemeldet als <strong>{username}</strong>{" "}
      <button onClick={() => logout()}>Abmelden</button>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<View>({ name: "list" });

  return (
    <>
      <CurrentUserBadge />
      <ApiHealthBanner />
      {view.name === "list" && (
        <RunsListScreen
          onStartNew={() => setView({ name: "start" })}
          onSelectDraft={(run: RunSummary) => setView({ name: "play", runId: run.id })}
          onSelectActive={(run: RunSummary) => setView({ name: "play", runId: run.id })}
        />
      )}
      {view.name === "start" && (
        <StartDraftScreen
          onBack={() => setView({ name: "list" })}
          onPlaythroughStarted={(runId) => setView({ name: "play", runId })}
        />
      )}
      {view.name === "play" && (
        <PlayScreen runId={view.runId} onBack={() => setView({ name: "list" })} />
      )}
    </>
  );
}
