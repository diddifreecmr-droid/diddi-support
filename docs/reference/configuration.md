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
- `CONTEXT_READER_ALLOWED_SERVICES` : liste des services autorisés à lire un
  contexte via DiddiSupport. Par défaut, seul `diddicomms` est accepté.
- `CASE_DELEGATED_ORIGIN_SERVICES` : propriétaires métier pour lesquels
  DiddiComms peut ouvrir un dossier par délégation. Cette liste est validée au
  démarrage et nécessite un redeploiement pour changer.
- `DIDDICOMMS_SERVICE_CLIENT_ID` : client ID DiddiFreeID attendu pour les
  appels de contexte provenant de DiddiComms. Une valeur doit être injectée
  en staging et en production.
- `DIDDIFREEID_SERVICE_TOKEN_URL` : endpoint DiddiFreeID pour le grant
  `client_credentials`.
- `DIDDISUPPORT_DIDDIGO_BASE_URL` : URL réseau de DiddiGo.
- `DIDDISUPPORT_DIDDIGO_SERVICE_CLIENT_ID` et
  `DIDDISUPPORT_DIDDIGO_SERVICE_CLIENT_SECRET` : identité de DiddiSupport
  pour interroger DiddiGo. Le secret est injecté uniquement par Portainer.
- `DIDDISUPPORT_DIDDIGO_SERVICE_AUDIENCE` et
  `DIDDISUPPORT_DIDDIGO_SERVICE_SCOPE` : audience et scope demandés au token.
- `DIDDISUPPORT_DIDDISEND_BASE_URL` : URL réseau de DiddiSend
  (`http://diddisend-api-staging.diddifree.com` en staging si le proxy est en
  HTTP).
- `DIDDISUPPORT_DIDDISEND_SERVICE_CLIENT_ID` et
  `DIDDISUPPORT_DIDDISEND_SERVICE_CLIENT_SECRET` : identité de DiddiSupport
  pour interroger DiddiSend. Le secret est injecté uniquement par Portainer.
- `DIDDISUPPORT_DIDDISEND_SERVICE_AUDIENCE` et
  `DIDDISUPPORT_DIDDISEND_SERVICE_SCOPE` : audience et scope demandés au token.
- `BACKOFFICE_AUDIENCE` : audience JWT attendue pour les agents du Backoffice.

## Dispatcher outbox

- `OUTBOX_STREAM_NAME` : stream Redis de publication, par défaut
  `diddisupport.events`.
- `OUTBOX_STREAM_MAXLEN` : rétention maximale approximative du stream.
- `OUTBOX_BATCH_SIZE` : nombre maximal d'événements réclamés par cycle.
- `OUTBOX_LEASE_SECONDS` : durée du bail anti-concurrence d'un événement.
- `OUTBOX_MAX_ATTEMPTS` : nombre maximal de tentatives avant quarantaine.
- `OUTBOX_BACKOFF_BASE_SECONDS` et `OUTBOX_BACKOFF_MAX_SECONDS` : bornes du
  backoff exponentiel.
- `OUTBOX_METRICS_PORT` : port Prometheus du worker, 9105 par défaut.
## Sécurité et pilote

Les variables `IDENTITY_JWKS_URL`, `IDENTITY_ISSUER`, `SERVICE_AUDIENCE` et
`BACKOFFICE_AUDIENCE` contrôlent les identités. Les connecteurs et seuils
métier sont injectés au déploiement ; une modification nécessite un
redeploiement.
