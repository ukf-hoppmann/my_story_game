# TASK-049 — Wissen und Sichtbarkeit im Backend befüllen

## 2026-10-14 — Befund bei der Welt-Ansicht (Frontend)

### Discussed

- Domäne, Persistenz und API kennen KnowledgeEntry (learned_at/forgotten_at) und Visibility (inkl. actor_known mit actor_id).
- GrantKnowledge wird nirgends erzeugt; eine Vergessen-Operation existiert nicht; initial_world_extraction.py und approve_story_turn_changes.py legen Fakten ohne Sichtbarkeit an (Default public).

### Decided

- Die Welt-Ansicht im Frontend wird trotzdem vollständig gebaut; Wissensteile zeigen bis dahin einen Leer-Hinweis.
- Sichtbarkeit wird in der UI nur angezeigt, nicht gefiltert. Ein Spieler-/Spielleitungsmodus ist eine spätere Entscheidung.

### Open

- Wie die Extraktion Wissen, Vergessen und Sichtbarkeit zuverlässig ableitet (Prompt/Schema), ist zu klären.
- Bezug zu TASK-018 (verdecktes Wissen im Story-Prompt).
