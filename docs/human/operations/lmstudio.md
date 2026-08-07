# Lokaler LM-Studio-Smoke-Test

LM Studio muss als lokaler Server laufen und ein Textmodell bereitstellen.
Der Test ist ein verpflichtender Abnahmeschritt für die Provider-Anbindung,
aber kein Teil der normalen Offline-Verifikation.

```text
STORY_GAME_LMSTUDIO_LIVE=1
STORY_GAME_LMSTUDIO_BASE_URL=http://localhost:1234/v1
STORY_GAME_LMSTUDIO_MODEL_ID=<verfügbares Textmodell>
```

Anschließend wird ausschließlich der Infrastruktur-Smoke-Test ausgeführt:

```text
python -m pytest tests/infrastructure/llm/lmstudio/test_live.py -m lmstudio_live
```

Der Test verwendet einen kleinen synthetischen Story-Grenzen-Request, fordert
`LMSTUDIO_SMOKE_OK` an und prüft die normalisierte Antwort. Er lädt keine
Modelle herunter, persistiert keine Antwort und verändert keinen GameState.

Wenn der Test aus einem Container läuft, muss die URL typischerweise
`http://host.docker.internal:1234/v1` verwenden.
