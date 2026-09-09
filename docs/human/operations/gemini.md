# Gemini als Provider einrichten

Gemini ist ein dritter, optionaler Provider neben LM Studio (siehe
[`lmstudio.md`](lmstudio.md)) und Groq (siehe [`groq.md`](groq.md)). Alle drei
sind gleichzeitig konfiguriert; welcher Provider für welchen Task (`story`,
`extraction`, `summary`) tatsächlich läuft, entscheidet allein `task_models`
in `configs/llm.toml` — pro Task frei mischbar.

Gemini spricht über seinen OpenAI-Kompatibilitäts-Endpunkt
(`https://generativelanguage.googleapis.com/v1beta/openai`) dasselbe
Wire-Format wie LM Studio und Groq — technisch derselbe Adapter-Zuschnitt,
siehe `infrastructure/llm/openai_compatible/`.

## API-Key einrichten

Der Gemini-API-Key gehört **nicht** in die versionierte `configs/llm.toml`.
Stattdessen:

1. Kostenlosen Key bei [Google AI Studio](https://aistudio.google.com)
   anlegen (keine Kreditkarte nötig).
2. `Backend/configs/llm.secrets.toml.example` nach
   `Backend/configs/llm.secrets.toml` kopieren (diese Datei ist in
   `.gitignore` eingetragen und wird nie committet).
3. Den echten Key eintragen:

   ```toml
   [providers.gemini]
   api_key = "..."
   ```

Ohne gültigen Key schlägt nur ein tatsächlicher Aufruf über Gemini fehl (als
sauberer, typisierter `authentication`-Fehler) — der Server startet auch ohne
diese Datei ganz normal, solange kein Task aktiv auf `provider_id = "gemini"`
zeigt.

## Provider pro Task wählen

`configs/llm.toml` enthält bereits einen Katalogeintrag für Gemini-Extraction
(`model.extraction.gemini`, Modell `gemini-3.5-flash-lite`). Um Extraction auf
Gemini umzustellen:

```toml
[task_models]
extraction = "model.extraction.gemini"   # statt "model.extraction.groq"
```

Änderungen an `configs/llm.toml` und `configs/llm.secrets.toml` werden bei
jedem Aufruf neu eingelesen — ein Neustart des Backends ist dafür nicht
nötig.

## Rate-Limits (kostenlose Stufe, Stand der letzten Recherche)

| Modell | RPM | RPD | TPM |
|---|---|---|---|
| `gemini-3.5-flash-lite` / `gemini-2.5-flash-lite` | 15 | 1.000 | 250.000 |
| `gemini-2.5-flash` | 10 | 250 | 250.000 |
| `gemini-2.5-pro` | 5 | 100 | 250.000 |

Diese Zahlen ändern sich bei Google öfter — vor dem produktiven Einsatz in
der Google-AI-Studio-Konsole gegenchecken.

## Weitere Gemini-Modelle

Weitere `[[models]]`-Einträge mit `provider_id = "gemini"` und einer anderen
`model_id` (z.B. `gemini-2.5-flash`, `gemini-2.5-pro`) lassen sich unabhängig
von diesem Eintrag ergänzen und über `task_models` aktivieren. Modellnamen
ändern sich bei Google gelegentlich (z.B. wurde `gemini-2.5-flash-lite`
zwischenzeitlich durch `gemini-3.5-flash-lite` abgelöst) — bei einem
`model_unavailable`-Fehler lohnt sich ein Blick in die aktuelle
Google-AI-Studio-Modellliste.
