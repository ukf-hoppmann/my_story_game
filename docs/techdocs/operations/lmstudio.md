# Lokaler LM-Studio-Smoke-Test

LM Studio muss als lokaler Server laufen und ein Textmodell bereitstellen.
Provider und Modelle werden aus der einzigen Projektkonfiguration
`configs/llm.toml` gelesen. Für Story, Extraction, Summary und Szenenbild-Prompts (`scene_image`) ist
jeweils ein logischer Katalogeintrag definiert. Die Einträge dürfen zunächst dieselbe
konkrete LM-Studio-Modell-ID verwenden.

Die Vorgabe der Task-Zuordnung sieht beispielsweise so aus; sie wird beim
ersten Start in die Datenbank übernommen und lässt sich danach in den
Einstellungen ändern:

```toml
[task_models]
story = "model.story.default"
extraction = "model.extraction.default"
summary = "model.summary.default"
scene_image = "model.scene_image.default"
```

Der Live-Test wird ausdrücklich über die Pytest-Option aktiviert:

```text
STORY_LMSTUDIO_LIVE_BASE_URL=http://localhost:1234/v1 \
python -m pytest tests/infrastructure/llm/lmstudio/ \
  -m lmstudio_live --run-lmstudio-live
```

Ohne `--run-lmstudio-live` wird der Test übersprungen. Der normale Offline-
Testlauf kontaktiert LM Studio nicht. Der Smoke-Test verwendet einen kleinen
synthetischen Story-Grenzen-Request, fordert `LMSTUDIO_SMOKE_OK` an und
persistiert keine Antwort.

Wenn der Test aus einem Container läuft, muss die URL typischerweise
`http://host.docker.internal:1234/v1` verwenden.

Der testlokale Override ändert `configs/llm.toml` nicht. Dadurch kann die
Projektkonfiguration weiterhin die Containeradresse verwenden, während ein
bewusst auf dem Host gestarteter Live-Test LM Studio über `localhost` erreicht.
