# Plan d'implémentation — DiddiSupport : corrélation et authentification Backoffice
Statut : VALIDÉ
Date : 2026-11-28
Branche du run : codex/diddi-support-2026-11-28

## 1. Objectif et périmètre

- Inclus dans le MVP :
  - retourner `X-Request-ID` sur toutes les réponses DiddiSupport, en réutilisant l'identifiant entrant ou en en générant un ;
  - accepter le JWT de service du BFF DiddiAdmin sur `/support/v1/backoffice/*` ;
  - conserver temporairement l'acceptation du JWT utilisateur Backoffice ;
  - appliquer les scopes Support par route ;
  - auditer `X-Backoffice-Actor`, `X-Backoffice-Reason` et `X-Request-ID` ;
  - tester les deux contrats en local et en staging. (source : `C:/Users/Vanauld/Downloads/SLACK/007-no-x-request-id-in-responses.md`, sections Problem/Expected ; `C:/Users/Vanauld/Downloads/SLACK/109-accept-backoffice-service-token.md`, sections Expected change/Not breaking)
- Exclu du MVP :
  - modification des routes publiques DiddiAdmin ;
  - accès direct du navigateur à DiddiSupport ;
  - changement du routage client de DiddiComms ;
  - suppression immédiate du mode JWT utilisateur ;
  - déploiement ou modification de secrets dans Portainer. (source : `docs/integrations/diddibackoffice.md`, sections Responsabilités et Authentification)

## 2. Architecture retenue

DiddiComms reste la porte d'entrée utilisateur et transporte les messages ;
DiddiSupport reste un service interne propriétaire des dossiers, messages
Support, statuts, audit, actions et SOS. DiddiAdmin passe par son BFF : le BFF
obtient un JWT de service FreeID, appelle DiddiSupport et transmet l'identité de
l'agent dans `X-Backoffice-Actor`. (source : `docs/integrations/diddicomms.md`, sections Identité et Responsabilités ; `docs/integrations/diddibackoffice.md`, sections Responsabilités et Appel recommandé)

La corrélation est transversale : l'identifiant de requête est reçu, retourné,
transmis aux dépendances et enregistré dans l'audit/outbox. Les corps de
messages, tokens et données sensibles restent exclus des logs. (source : `DIDDI_MODULE_PROTOCOL_V1.md`, sections Identité, Événements et Confidentialité ; `docs/integrations/diddibackoffice.md`, section Contexte métier et confidentialité)

## 3. Décisions figées

| ID | Décision | Source |
|---|---|---|
| D-01 | Le frontend ne parle pas directement à DiddiSupport ; DiddiComms reste la façade utilisateur. | `docs/api/frontend-support-contract.md`, sections Positionnement et Routes publiques |
| D-02 | Le BFF DiddiAdmin utilise un token de service ; le navigateur ne reçoit aucun secret S2S. | `docs/integrations/diddibackoffice.md`, sections Responsabilités et Authentification |
| D-03 | Les permissions restent les scopes `diddi-support:*` déjà utilisés par les routes Backoffice. | `docs/integrations/diddibackoffice.md`, sections Permissions et Routes disponibles |
| D-04 | Le JWT utilisateur Backoffice reste accepté pendant la transition. | `C:/Users/Vanauld/Downloads/SLACK/109-accept-backoffice-service-token.md`, section Not breaking |
| D-05 | Toute réponse doit contenir `X-Request-ID`, entrant ou généré. | `C:/Users/Vanauld/Downloads/SLACK/007-no-x-request-id-in-responses.md`, section Expected |
| D-06 | Les routes Backoffice et les erreurs utilisent le contrat HTTP existant ; les nouveaux écarts doivent être documentés dans l'OpenAPI et le catalogue d'erreurs. | `docs/integrations/diddibackoffice.md`, sections Base URL et Erreurs et reprises |
| D-07 | L'identité acceptée est `service:diddiadmin`. | Utilisateur, 2026-11-28 |
| D-08 | L'allowlist `X-Client-ID` est globale. | Utilisateur, 2026-11-28 |
| D-09 | `X-Backoffice-Reason` est facultatif, mais enregistré lorsqu'il est présent. | Utilisateur, 2026-11-28 |
| D-10 | Un `X-Request-ID` absent est généré comme UUID v4. | Utilisateur, 2026-11-28 |
| D-11 | L'application doit ajouter/préserver le header et le proxy doit le préserver de bout en bout. | Utilisateur, 2026-11-28 |
| D-12 | Le token service Backoffice doit être ajouté au code, en conservant temporairement le JWT utilisateur. | Utilisateur, 2026-11-28 |

## 4. Contrats avec les autres services

| Service | Ce qu'on attend (endpoints, événements) | État : existe / à créer / à valider | Source |
|---|---|---|---|
| DiddiFreeID | JWKS, issuer, audience `diddi-support`, JWT service actif, scopes Backoffice, identité `service:diddiadmin`, client ID autorisé | existe côté vérification ; configuration opérationnelle à vérifier | `src/diddi_support/core/auth.py`, `docs/integrations/diddibackoffice.md`, Slack 109 ; Utilisateur, 2026-11-28 |
| DiddiAdmin BFF | Appels `/support/v1/backoffice/*` avec `Authorization`, `X-Client-ID`, `X-Backoffice-Actor`, `X-Backoffice-Reason`, `X-Request-ID` | à intégrer/valider | `docs/integrations/diddibackoffice.md`, sections Authentification et Ce que DiddiBackoffice doit encore fournir |
| DiddiSupport | Réponse avec `X-Request-ID`, contrôle de scope, audit de l'acteur délégué | à implémenter | Slack 007 et Slack 109 |
| DiddiComms | Propagation de `X-Request-ID` vers les appels Support et consommation des contrats internes | déjà contracté ; hors modification de ce plan | `docs/integrations/diddicomms.md`, sections Identité et Messages utilisateur |
| Portainer | Redéploiement contrôlé de DiddiSupport après validation ; aucune mutation prévue dans ce plan | existe ; vérification staging à faire | `docs/reference/configuration.md`, section Migrations et observabilité de déploiement |

## 5. Déjà fait (ne pas refaire)

- Le service possède déjà `ServiceTokenVerifier` avec JWKS, issuer, audience,
  `client_id`, type et statut du token. (source : `src/diddi_support/core/auth.py`)
- Les routes Backoffice et leurs permissions sont déjà définies. (source : `src/diddi_support/presentation/internal_router.py`, routes `/support/v1/backoffice/*` ; `docs/api/openapi.json`)
- Le mode JWT utilisateur Backoffice existe déjà via `require_support_agent`. (source : `src/diddi_support/core/auth.py`)
- La propagation de `X-Request-ID` vers les appels contexte et fichiers existe
  déjà. (source : `src/diddi_support/presentation/internal_router.py` ; `src/diddi_support/infrastructure/context/http.py` ; `src/diddi_support/infrastructure/files/client.py`)
- L'audit et l'outbox persistants existent déjà pour les mutations Support. (source : `migrations/0001_support_foundation.sql` ; `src/diddi_support/infrastructure/persistence/repository.py`)
- Le dispatcher Redis, les migrations automatiques et le worker outbox existent
  déjà. (source : commits `a4e64c1`, `2e4623e`, `acff6a7` ; `src/diddi_support/infrastructure/outbox.py` ; `src/diddi_support/ops/outbox_worker.py`)
- Les tests de domaine, contrats outbox, sécurité et santé existent déjà. (source : `tests/`)

## 6. Phases

### P0 — Figer l'identité et établir la baseline

- Objectif : disposer d'un contrat non ambigu avant toute modification.
- Dépend de : D-07, D-08 et D-09.
- Contenu :
  - enregistrer dans la configuration et les tests l'identité `service:diddiadmin` ;
  - appliquer l'allowlist globale de `X-Client-ID` ;
  - traiter `X-Backoffice-Reason` comme facultatif et l'enregistrer lorsqu'il est présent ;
  - exécuter la suite actuelle et conserver le résultat comme baseline. (source : Slack 109 ; `docs/integrations/diddibackoffice.md`, sections Authentification et Erreurs)
- Hors de cette phase : aucune modification d'authentification ou de code métier.
- Critères de fin (vérifiables) : `python -m pytest -q` passe sur `origin/main` ; les tests de configuration couvrent `service:diddiadmin`, l'allowlist globale et le caractère facultatif de `X-Backoffice-Reason`.
- Risques : une identité FreeID mal confirmée rendrait le contrat incompatible avec DiddiAdmin.

### P1 — Corrélation `X-Request-ID`

- Objectif : rendre chaque réponse Support traçable avec un identifiant stable.
- Dépend de : D-05.
- Contenu :
  - ajouter le middleware ou mécanisme global de génération/écho ;
  - couvrir les réponses normales et les exceptions FastAPI ;
  - préserver l'identifiant déjà utilisé par les appels downstream, audits et outbox ;
  - ajouter la documentation de comportement et le test contractuel. (source : Slack 007 ; `docs/integrations/diddicomms.md`, section Identité)
- Hors de cette phase : changement de format métier des réponses.
- Critères de fin (vérifiables) : tests avec ID fourni et absent ; tests sur `/health/live`, `/health/ready`, `/support/v1/ping` et une erreur `401/403/404` ; aucune réponse de ces routes ne manque `X-Request-ID`.
- Risques : un proxy peut supprimer le header ; le test staging doit distinguer absence côté application et suppression côté proxy.

### P2 — Authentification Backoffice par token de service

- Objectif : permettre à DiddiAdmin d'appeler les routes Backoffice sans recevoir de `401` pour un token de service valide.
- Dépend de : P0 et du contrat FreeID confirmé.
- Contenu :
  - introduire une dépendance d'authentification Backoffice duale ;
  - conserver le chemin JWT utilisateur ;
  - vérifier pour le chemin service : signature RS256/JWKS, issuer, audience, `token_type`, rôle/statut, client ID et allowlist ;
  - lire le scope requis par route ;
  - lire et valider `X-Backoffice-Actor` et `X-Backoffice-Reason` ;
  - utiliser l'acteur délégué pour les audits d'écriture ;
  - conserver le sujet du service comme identité technique séparée. (source : Slack 109 ; `docs/integrations/diddibackoffice.md`, sections Authentification et Permissions)
- Hors de cette phase : suppression du JWT utilisateur et modification des routes BFF publiques de DiddiAdmin.
- Critères de fin (vérifiables) : un token service valide accède à `GET /cases` ; chaque scope route est contrôlé ; les écritures sans acteur sont rejetées ; les audits contiennent l'acteur délégué et la raison ; les tests JWT utilisateur existants restent verts.
- Risques : divergence entre le claim `service` réel FreeID et la règle actuellement codée dans `validate_service_claims`.

### P3 — Contrats, OpenAPI et tests d'intégration

- Objectif : rendre le comportement consommable et vérifiable par DiddiAdmin.
- Dépend de : P1 et P2.
- Contenu :
  - mettre à jour `docs/api/openapi.json`, le catalogue d'erreurs et le contrat Backoffice ;
  - documenter les headers, erreurs, acteur délégué et réponse `X-Request-ID` ;
  - ajouter tests de contrat service-token, scopes, actor/reason, corrélation et erreurs ;
  - vérifier que les messages internes ne sont jamais exposés à DiddiComms ou aux événements utilisateur. (source : `docs/integrations/diddibackoffice.md`, sections Erreurs et reprises et Confidentialité ; `docs/realtime/outbox-events.md`)
- Hors de cette phase : création de nouvelles routes métier.
- Critères de fin (vérifiables) : `python -m pytest -q`, `ruff check .`, génération OpenAPI sans différence inattendue, tests de non-régression des contrats DiddiComms et outbox.
- Risques : l'OpenAPI actuel peut refléter le JWT utilisateur uniquement et nécessiter une mise à jour générée depuis l'application.

### P4 — Vérification staging et livraison contrôlée

- Objectif : prouver le parcours réel DiddiAdmin → DiddiSupport.
- Dépend de : P3, credentials FreeID valides et configuration BFF DiddiAdmin disponible.
- Contenu :
  - déployer l'image Support via le workflow Portainer existant ;
  - vérifier migration `support-migrate`, API et worker outbox ;
  - exécuter `GET /support/v1/backoffice/cases` depuis le BFF DiddiAdmin ;
  - exécuter une lecture et une écriture avec actor/reason ;
  - vérifier `X-Request-ID` de bout en bout et retester les deux entrées Slack ;
  - conserver la compatibilité JWT utilisateur jusqu'à confirmation de migration DiddiAdmin. (source : `docs/reference/configuration.md`, section Migrations ; `docs/integrations/diddibackoffice.md`, section Ce que DiddiBackoffice doit encore fournir ; Slack 007 et Slack 109)
- Hors de cette phase : redémarrage manuel non nécessaire, rollback ou modification de secrets sans décision séparée.
- Critères de fin (vérifiables) : tests staging ciblés verts ; réponse DiddiSupport `2xx` avec `X-Request-ID` ; aucune erreur `401` sur les écrans Support DiddiAdmin ; containers API/worker healthy et migration terminée avec code 0.
- Risques : le BFF DiddiAdmin ou le reverse proxy peut ne pas transmettre les headers malgré une application correcte.

## 7. Questions ouvertes

Aucune question bloquante restante pour ce plan.

## 8. Contradictions entre sources

Aucune contradiction bloquante restante après les décisions utilisateur du 2026-11-28.

## 9. Critère de fin du plan entier

Le plan sera considéré comme exécuté lorsque, sur la branche de run :

- `python -m pytest -q` passe avec les tests existants et nouveaux ;
- `ruff check .` passe ;
- `docker compose config --quiet` passe ;
- l'OpenAPI et les documents de contrat correspondent au comportement implémenté ;
- un appel DiddiAdmin service-token valide atteint les routes Backoffice avec les scopes attendus ;
- un appel sans droit reçoit le code HTTP et le code métier attendus ;
- toutes les réponses vérifiées contiennent `X-Request-ID` ;
- le staging confirme le parcours BFF DiddiAdmin → DiddiSupport sans `401` et sans perte de corrélation ;
- les décisions D-07 à D-12 sont intégrées au plan avec leur source utilisateur.
