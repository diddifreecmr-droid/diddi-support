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
- `CONTEXT_AUTH_TOKEN` et `CONTEXT_CLIENT_ID` : identité sortante de
  DiddiSupport vers les modules propriétaires. Le token reste un secret.
- `BACKOFFICE_AUDIENCE` : audience JWT attendue pour les agents du Backoffice.
