# État d'implémentation — DiddiSupport

- Plan : `IMPLEMENTATION_PLAN_2026-11-28_CORRELATION_BACKOFFICE_AUTH.md`
- Branche : `codex/diddi-support-2026-11-28`
- Statut : en cours — P0 et P1 terminés
- Dernière mise à jour : 2026-11-28

## Vérifications du projet

Les commandes identifiées dans `README.md` et `pyproject.toml` sont :

```powershell
python -m pytest
ruff check .
docker compose config
docker build -t diddi-support:local .
python scripts/generate_openapi.py
```

La suite ciblée peut être exécutée avec `python -m pytest -q`.

## Progression

- P0 : terminé ; 55 tests passent, lint bloqué par 3 E501 préexistants
- P1 : terminé ; middleware global et tests contractuels livrés
- P2 : en attente
- P3 : en attente
- P4 : en attente

## Vérifications de déploiement en attente

- Parcours DiddiAdmin BFF → DiddiSupport avec token de service valide.
- Conservation de `X-Request-ID` par l'application et le proxy.
- État healthy des conteneurs API/worker et migration terminée dans Portainer.

## Blocages

- Aucun blocage connu.
