# Configuration DiddiSupport

## Variables d'environnement

Les variables d'environnement configurent le déploiement et le fonctionnement
technique : URLs de services, tokens, audiences, identifiants clients,
PostgreSQL, Redis, stockage, timeouts, retries, workers et observabilité.

Chaque variable doit être documentée avec son type, son caractère obligatoire,
sa valeur par défaut éventuelle et son comportement si elle est invalide.

## Redeploiement obligatoire

Les règles suivantes ne sont pas des variables facilement modifiables :

- transitions de dossiers et de SOS ;
- permissions et scopes ;
- catégories sensibles ;
- actions métier et financières ;
- visibilité des messages ;
- codes d'erreur et événements ;
- règles de confidentialité.

Une modification de ces règles exige code ou contrat versionné, tests,
documentation, validation Docker et redeploiement.

## Contexte métier

- `CONTEXT_CONNECTORS_JSON` : mapping JSON des modules propriétaires capables
  de fournir un contexte support, par exemple
  `{ "diddigo": { "base_url": "http://diddigo:8040", "scope": "diddigo:support-context:read" } }`.
- `CONTEXT_REQUEST_TIMEOUT_SECONDS` : timeout de lecture des contextes métier.
- `CONTEXT_AUTH_TOKEN` et `CONTEXT_CLIENT_ID` : identité sortante statique de
  secours vers les modules propriétaires. Le token reste un secret.
- `DIDDIFREEID_SERVICE_TOKEN_URL` : endpoint DiddiFreeID pour le grant
  `client_credentials`.
- `DIDDISUPPORT_DIDDIGO_BASE_URL` : URL réseau de DiddiGo.
- `DIDDISUPPORT_DIDDIGO_SERVICE_CLIENT_ID` et
  `DIDDISUPPORT_DIDDIGO_SERVICE_CLIENT_SECRET` : identité de DiddiSupport
  pour interroger DiddiGo. Le secret est injecté uniquement par Portainer.
- `DIDDISUPPORT_DIDDIGO_SERVICE_AUDIENCE` et
  `DIDDISUPPORT_DIDDIGO_SERVICE_SCOPE` : audience et scope demandés au token.
- `BACKOFFICE_AUDIENCE` : audience JWT attendue pour les agents du Backoffice.
## Sécurité et pilote

Les variables `IDENTITY_JWKS_URL`, `IDENTITY_ISSUER`, `SERVICE_AUDIENCE` et
`BACKOFFICE_AUDIENCE` contrôlent les identités. Les connecteurs et seuils
métier sont injectés au déploiement ; une modification nécessite un
redeploiement.
