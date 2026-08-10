# Zentrale LLM-Konfiguration

Status: Umgesetzt am 2026-08-10.

## Umfang

Die Provider- und Modellauswahl wird aus der einzigen Projektdatei
`configs/llm.toml` geladen. Sie enthält:

- Providerverbindungen mit Base-URL und Timeout;
- eine aktive logische Modellreferenz für Story, Extraction und Summary;
- je einen direkt definierten Modelleintrag für diese drei Aufgaben;
- konkrete Provider-Modell-IDs, die erst zur Laufzeit in `ModelSelection`
  aufgelöst werden.

Weitere Modelle können später als zusätzliche `[[models]]`-Einträge ergänzt
werden. Die `task_models`-Tabelle bestimmt, welcher Eintrag je Aufgabe aktiv
ist.

`GameConfiguration` bleibt davon getrennt. Sie speichert die logischen
Modellreferenzen eines gestarteten Spiels als persistierten Snapshot. Ein
Story-Workflow, der diese Werte beim Spielstart übernimmt, ist noch nicht
implementiert.

## Live-Smoke-Test

Der Test liest Provider und Story-Modell aus derselben TOML-Konfiguration und
wird ausschließlich mit dieser expliziten Option aktiviert:

```text
python -m pytest tests/infrastructure/llm/lmstudio/test_live.py \
  -m lmstudio_live --run-lmstudio-live
```

Ohne die Option wird der Test übersprungen. Standardtests greifen nicht auf
LM Studio oder andere externe Dienste zu.

## Grenzen

Secrets, lokale Overrides, Fallback-Modelle, Streaming und die Integration in
`application/story_generation` bleiben spätere Aufgaben.
