# Geplante LLM-Dokumentation

Hier liegen Entwürfe für spätere LLM-Regeln, Prompt-Verträge,
Ausgabeformate oder LLM-spezifische Arbeitsabläufe.

Ein Entwurf ist nicht bindend. Vor der Aktivierung muss geklärt werden, ob er
für das Storygame-LLM oder für den Coding-Agenten gilt. Agenten- und
Architekturregeln müssen anschließend in ihre autoritative Harness-Quelle
überführt oder von dort eindeutig referenziert werden.

Die LLM-Grundarchitektur, das versionierte Prompt-Paket und die transiente
zweistufige Story-Initialisierung sind umgesetzt. Der reguläre StoryTurn-
Workflow einschließlich späterer Extraction und Persistenz bleibt im aktiven
Zustandsvertrag als Folgearbeit abgegrenzt.
Ihre frühere vollständige Planung ist als Abschlussarchiv unter
[`../done/2026-08-06-spielzustand-und-persistenz.md`](../done/2026-08-06-spielzustand-und-persistenz.md)
erhalten. Sie ist kein Ersatz für einen konkreten zukünftigen Implementierungs-
und Prompt-Vertrag.

Aktueller Entwurf:

- [`story-initialization.md`](story-initialization.md): LLM-Vertrag und
  gestufte Umsetzung für die Eröffnung ohne bestehenden GameState.
- [`llm-connection.md`](llm-connection.md): detaillierter maschinenorientierter
  Arbeitsstand für den allgemeinen Modellvertrag, Story und Extraction.

Die verständliche Architekturentscheidung steht unter
[`../../human/decisions/llm-anbindung.md`](../../human/decisions/llm-anbindung.md).
Das konkrete technische Story-Zielbild steht unter
[`../../human/technical/planned/story-generation.md`](../../human/technical/planned/story-generation.md).
