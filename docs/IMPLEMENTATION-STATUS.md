# État d'implémentation — DiddiSupport

- Plan : `IMPLEMENTATION_PLAN_2026-11-28_CORRELATION_BACKOFFICE_AUTH.md`
- Branche : `codex/diddi-support-2026-11-28`
- Statut : implémentation locale terminée ; vérification externe en attente
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
- P4 : P4-A terminé ; P4-B EN ATTENTE, aucun déploiement exécuté

## Vérifications de déploiement en attente

- Configurer `BACKOFFICE_SERVICE_CLIENT_IDS` avec
  `backoffice-staging-diddisupport`, sans versionner de secret.
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
- L'API staging répond `401 BACKOFFICE_CLIENT_ID_FORBIDDEN` pour
  `backoffice-staging-diddisupport` : la variable
  `BACKOFFICE_SERVICE_CLIENT_IDS` n'est pas encore configurée dans le
  déploiement actif de DiddiSupport.
- Le même `X-Request-ID` a été reçu dans la réponse, donc la corrélation
  application/proxy est vérifiée sur cet appel.
