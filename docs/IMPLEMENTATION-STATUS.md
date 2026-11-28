# État d'implémentation — DiddiSupport

- Plan : `IMPLEMENTATION_PLAN_2026-11-28_CORRELATION_BACKOFFICE_AUTH.md`
- Branche : `codex/diddi-support-2026-11-28`
- Statut : correctif local terminé ; redéploiement staging nécessaire
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
- P2 : terminé ; authentification duale, audit de raison et tests de routes livrés
- P3 : terminé ; contrats, OpenAPI et non-régression livrés
- P4 : P4-A terminé ; P4-B test staging exécuté, échec 500 diagnostiqué et corrigé

## Vérifications de déploiement en attente

- Redéployer la branche contenant le correctif `b4cfc63` via le workflow Portainer
  existant ; la configuration active contient déjà `BACKOFFICE_SERVICE_CLIENT_IDS`
  avec `backoffice-staging-diddisupport`.
- Déployer via le workflow Portainer existant, puis vérifier `support-migrate`
  en `Exited (0)`, l'API healthy et le worker healthy.
- Depuis le BFF DiddiAdmin, appeler `GET /support/v1/backoffice/cases` avec un
  token service valide, `X-Client-ID` autorisé et `X-Backoffice-Actor` UUID.
- Vérifier une lecture et une écriture avec et sans `X-Backoffice-Reason`, puis
  confirmer l'audit de la raison lorsqu'elle est fournie.
- Vérifier le même `X-Request-ID` dans la réponse Support, le BFF et le proxy.
- Vérifier qu'un JWT utilisateur Backoffice existant reste accepté.

## Blocages

- Test staging effectué : le token DiddiFreeID est valide et contient les
  scopes `read`, `write`, `assign`, `reply`, `sos-operate` et
  `attachments-read`.
- La configuration Portainer active contient bien
  `BACKOFFICE_SERVICE_CLIENT_IDS=backoffice-staging-diddisupport`.
- L'appel autorisé atteint l'API mais renvoie `500`. La cause racine dans les
  logs est un `ValueError` lors du reset d'un `ContextVar` créé dans un autre
  contexte d'exécution (`request_id_middleware`). Le correctif est `b4cfc63`.
- Sur cet appel, le proxy n'a pas renvoyé `X-Request-ID` car l'exception est
  survenue pendant la finalisation du middleware ; la vérification doit être
  rejouée après redéploiement.
