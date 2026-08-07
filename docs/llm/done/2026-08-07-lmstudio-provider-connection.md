# LM-Studio-Provider-Anbindung

Status: Umgesetzt am 2026-08-07.

## Umfang

Die erste austauschbare Provider-Anbindung verwendet LM Studios OpenAI-
kompatiblen Endpoint `POST /v1/chat/completions`. Die Application kennt weder
HTTP, LM-Studio-Responseobjekte noch Providerfehler.

Implementiert wurden:

- ein minimaler Application-Vertrag für die Story-Grenze;
- `ModelSelection`, `GenerationOptions`, `LLMGenerationCall` und `LLMError`;
- ein LM-Studio-HTTP-Client mit Laufzeitkonfiguration, Timeout und optionalem
  API-Token;
- ein Adapter, der Systemprompts, Konfiguration, WorldState, StoryState und
  Userprompt in eine LM-Studio-Anfrage überführt;
- die Normalisierung von erfolgreicher Prosa und technischen Fehlern;
- HTTP-Testdouble- und Adaptertests;
- ein ausdrücklich aktivierter Live-Smoke-Test mit einem lokalen LM-Studio-
  Modell.

`application/story_generation`, Kontextauswahl, Extraction, Persistenz und ein
vollständiger Storyzug sind nicht Teil dieser Umsetzung.

## Lokaler Live-Test

LM Studio muss als lokaler Server laufen. Die benötigte Konfiguration ist:

```text
STORY_GAME_LMSTUDIO_LIVE=1
STORY_GAME_LMSTUDIO_BASE_URL=http://localhost:1234/v1
STORY_GAME_LMSTUDIO_MODEL_ID=<verfügbares Textmodell>
```

Der Test fordert den Marker `LMSTUDIO_SMOKE_OK` an und prüft eine nichtleere
normalisierte Antwort. Er lädt keine Modelle herunter und schreibt keinen
Spielzustand.

Bei einer Ausführung aus einem Docker-Container muss die Base-URL auf den Host
zeigen, zum Beispiel `http://host.docker.internal:1234/v1`.

## Grenzen

Reasoning-Inhalte werden nicht als Story-Prosa verwendet. Wenn ein Modell sein
Ausgabelimit vor dem eigentlichen `message.content` erreicht, liefert der
Adapter bewusst `LLMErrorKind.INCOMPLETE` beziehungsweise
`INVALID_RESPONSE`. Retry, Fallback-Modelle, Streaming und katalogbasierte
Providerauflösung bleiben spätere Aufgaben.
