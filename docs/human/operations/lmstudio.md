# Lokaler LM-Studio-Smoke-Test

LM Studio muss als lokaler Server laufen und ein Textmodell bereitstellen.
Provider und Modelle werden aus der einzigen Projektkonfiguration
`configs/llm.toml` gelesen. Für Story, Extraction und Summary ist jeweils ein
logischer Katalogeintrag definiert. Die drei Einträge dürfen zunächst dieselbe
konkrete LM-Studio-Modell-ID verwenden.

Die Task-Zuordnung sieht beispielsweise so aus:

```toml
[task_models]
story = "model.story.default"
extraction = "model.extraction.default"
summary = "model.summary.default"
```

Der Live-Test wird ausdrücklich über die Pytest-Option aktiviert:

```text
python -m pytest tests/infrastructure/llm/lmstudio/test_live.py \
  -m lmstudio_live --run-lmstudio-live
```

Ohne `--run-lmstudio-live` wird der Test übersprungen. Der normale Offline-
Testlauf kontaktiert LM Studio nicht. Der Smoke-Test verwendet einen kleinen
synthetischen Story-Grenzen-Request, fordert `LMSTUDIO_SMOKE_OK` an und
persistiert keine Antwort.

Wenn der Test aus einem Container läuft, muss die URL typischerweise
`http://host.docker.internal:1234/v1` verwenden.
