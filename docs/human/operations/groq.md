# Groq als Provider einrichten

Groq ist ein zweiter, optionaler Provider neben LM Studio (siehe
[`lmstudio.md`](lmstudio.md)). Beide sind gleichzeitig konfiguriert; welcher
Provider für welchen Task (`story`, `extraction`, `summary`) tatsächlich
läuft, entscheidet allein `task_models` in `configs/llm.toml` — pro Task frei
mischbar, z.B. `story`/`summary` weiter über LM Studio, `extraction` über
Groq.

## API-Key einrichten

Der Groq-API-Key gehört **nicht** in die versionierte `configs/llm.toml`.
Stattdessen:

1. `Backend/configs/llm.secrets.toml.example` nach
   `Backend/configs/llm.secrets.toml` kopieren (diese Datei ist in
   `.gitignore` eingetragen und wird nie committet).
2. Den echten Key eintragen:

   ```toml
   [providers.groq]
   api_key = "gsk_..."
   ```

Ohne gültigen Key schlägt nur ein tatsächlicher Aufruf über Groq fehl (als
sauberer, typisierter `authentication`-Fehler) — der Server startet auch ohne
diese Datei ganz normal, solange kein Task aktiv auf `provider_id = "groq"`
zeigt.

## Provider pro Task wählen

`configs/llm.toml` enthält bereits einen Katalogeintrag für Groq-Extraction
(`model.extraction.groq`, Modell `openai/gpt-oss-120b`). Um Extraction auf
Groq umzustellen:

```toml
[task_models]
extraction = "model.extraction.groq"   # statt "model.extraction.default"
```

Änderungen an `configs/llm.toml` und `configs/llm.secrets.toml` werden bei
jedem Aufruf neu eingelesen — ein Neustart des Backends ist dafür nicht
nötig.

## Weitere Groq-Modelle

Weitere `[[models]]`-Einträge mit `provider_id = "groq"` und einer anderen
`model_id` (z.B. `gpt-oss-120b`, `qwen3.6-27b` je nach Groq-Katalog) lassen
sich unabhängig von diesem Eintrag ergänzen und über `task_models` aktivieren.
