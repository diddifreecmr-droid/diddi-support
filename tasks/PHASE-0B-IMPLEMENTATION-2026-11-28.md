# Journal P0-B — Baseline

- Statut : TERMINÉ avec remarque lint
- `python -m pytest -q` : 55 passed, 1 warning.
- `docker compose config --quiet` : passe ; Docker signale seulement un refus
  d'accès au fichier global de configuration utilisateur.
- `python scripts/generate_openapi.py` : passe, sans différence de fichier.
- `ruff check .` : échec préexistant sur trois lignes de `tests/test_context.py`
  (E501, lignes 29, 40 et 68). Aucun test n'est désactivé ni affaibli.
- Cause hors plan : formatage de tests existants dépassant 100 caractères.
