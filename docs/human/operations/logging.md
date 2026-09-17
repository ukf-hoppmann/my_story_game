# Logging und Diagnose

Die Anwendung schreibt Logs nach stdout und — sofern konfiguriert — in eine
rotierende Datei. Die zentrale Konfiguration liegt in
[`Backend/configs/app.toml`](../../../Backend/configs/app.toml) unter `[logging]`.

## Profile

`prod` ist das sichere Profil für normale Ausführung. Es schreibt typisierte,
vorab begrenzte Diagnoseereignisse, aber keine ungefilterten Prompts,
Spielerprosa oder Provider-Rohantworten.

`debug` ist ausdrücklich für lokale Untersuchung gedacht. Zusätzlich zu den
Diagnoseereignissen werden detaillierte Transformationsschritte sowie in den
OpenAI-kompatiblen Provider-Clients (LM Studio, Groq und Gemini) rohe Prompts
und Providerantworten ausgegeben. Dieses Profil darf nicht gegen eine reale
spielerbezogene Umgebung verwendet werden.

Die aktuelle Repository-Konfiguration steht bewusst auf `mode = "debug"`.
Für einen sicheren normalen Lauf muss sie auf `prod` gesetzt oder per
Umgebungsvariable überschrieben werden:

```bash
export STORY_GAME_LOG_MODE=prod
export STORY_GAME_LOG_LEVEL=INFO
```

Umgebungsvariablen überschreiben die TOML-Datei; diese überschreibt den
Hardcoded-Default.

## Ausgabe und Rotation

Standardmäßig wird nach `logs/story-game.log` geschrieben. Die Datei rotiert
bei 10 MiB und behält fünf Backups. Der Pfad, die Größe und die Anzahl der
Backups können in `[logging]` angepasst werden. Im Docker-Compose-Betrieb wird
`Backend/logs` in den Backend-Container gemountet, damit die Datei Container-
Neustarts übersteht.

Das Logging ergänzt typisierte Fehler und ersetzt sie nicht. Wiederkehrende
Modellfehler, verworfene Änderungsvorschläge, Revisionskonflikte und
Zusammenfassungsfehler werden als Diagnoseereignisse sichtbar. Das Frontend
meldet nicht-401-Tooling-Fehler über
`POST /api/v1/diagnostics/frontend-errors`; der Endpoint benötigt den
bestehenden Keycloak-Bearer-Token und erzeugt `FrontendToolingError`. 401-
Fehler werden nicht gemeldet, sondern führen im Frontend zu einem Re-Login.
