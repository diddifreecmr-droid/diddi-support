# Journal P3-B — Contrats et non-régression

- Statut : TERMINÉ
- `python -m pytest -q` : 66 passed, 1 warning FastAPI/httpx.
- `python scripts/generate_openapi.py` : passe.
- `docker compose config --quiet` : passe.
- `docker build -t diddi-support:local .` : passe après autorisation Docker.
- `ruff check .` : reste en échec uniquement sur les 3 E501 préexistants de
  `tests/test_context.py`, documentés en P0 ; le lint ciblé des fichiers du run
  passe.
