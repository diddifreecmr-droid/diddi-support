# Diddi Module Protocol v1

**Statut :** proposition de contrat intermodules  
**Propriétaire :** DiddiSupport  
**Version :** `1.0`  
**Manifest associé :** `manifests/diddi-support.v1.json`

## 1. Objectif

Ce document définit la manière dont un module DiddiFree peut se connecter à
DiddiSupport. Il ne définit pas les tables internes des modules et ne permet
pas à un service de lire directement la base de données d'un autre service.

Le protocole couvre :

- l'identification des services ;
- l'authentification interservices ;
- les contrats HTTP et événementiels ;
- l'idempotence et les reprises ;
- les erreurs et les corrélations ;
- la propriété des données ;
- les règles de confidentialité et d'audit.

## 2. Principes obligatoires

1. Chaque module reste propriétaire de ses données métier.
2. DiddiSupport possède les dossiers, messages de support, affectations,
   priorités, actions de support et leur historique.
3. Le module d'origine possède l'objet métier référencé : course, commande ou
   livraison.
4. Un service ne transmet jamais un identifiant utilisateur fourni uniquement
   par le navigateur pour autoriser une action sensible.
5. Une notification temps réel n'est jamais la source de vérité. Le client
   relit l'état courant en HTTP.
6. Toute mutation interservice doit être idempotente ou récupérable après un
   timeout.
7. Les fichiers sont référencés par `file_id`; les binaires et URLs temporaires
   ne sont jamais stockés dans un dossier métier.
8. Une décision de support et l'exécution de cette décision sont deux étapes
   auditables et distinctes.

## 3. Identité et authentification

Les appels service-à-service utilisent un JWT court émis par DiddiFree ID.

```http
Authorization: Bearer <service-jwt>
X-Client-ID: <provisioned-client-id>
X-Request-ID: <correlation-id>
traceparent: <optional-w3c-trace-context>
```

Le service receveur vérifie au minimum :

- `iss` configuré pour DiddiFree ID ;
- `aud` égal à son audience ;
- `sub` égal au service attendu ;
- `token_type=service` ;
- `status=active` ;
- `client_id` égal à `X-Client-ID` ;
- le scope nécessaire à l'opération.

Le navigateur ne reçoit jamais un service token.

### Audiences et scopes DiddiSupport

Audience de DiddiSupport : `diddi-support`.

Scopes proposés :

| Scope | Utilisation |
|---|---|
| `diddi-support:cases:create` | Créer ou retrouver un dossier depuis un module métier |
| `diddi-support:cases:read` | Lire un dossier autorisé |
| `diddi-support:cases:write` | Affecter, prioriser, résoudre ou rouvrir un dossier |
| `diddi-support:messages:write` | Ajouter une réponse agent ou système |
| `diddi-support:attachments:read` | Lire les métadonnées ou obtenir un accès temporaire à une preuve |
| `diddi-support:sos:create` | Enregistrer une alerte SOS |
| `diddi-support:sos:operate` | Prendre en charge ou escalader une alerte SOS |
| `diddi-support:audit:read` | Lire les événements d'audit autorisés |

Les scopes sont ciblés. Un scope de lecture ne permet ni décision ni action
opérationnelle.

## 4. Référence métier commune

Tous les modules utilisent une référence externe stable :

```json
{
  "origin_service": "diddigo",
  "resource_type": "ride",
  "resource_id": "uuid",
  "origin_report_id": "uuid-or-stable-string"
}
```

Valeurs initiales :

| Module | `origin_service` | `resource_type` |
|---|---|---|
| DiddiGo | `diddigo` | `ride` |
| DiddiFood | `diddifood` | `order` |
| DiddiSend | `diddisend` | `delivery` |

Les nouveaux types doivent être ajoutés au manifest et testés par contrat.

## 5. Flux de création d'un dossier

Le module d'origine doit :

1. authentifier l'utilisateur et vérifier son droit sur l'objet métier ;
2. enregistrer le signalement dans sa propre transaction ;
3. enregistrer une transmission durable dans son outbox ;
4. transmettre le signalement à DiddiSupport avec une clé stable ;
5. conserver l'état de transmission et les erreurs de reprise.

DiddiSupport doit :

1. vérifier le token de service et le scope ;
2. valider la référence métier ;
3. dédupliquer sur `origin_service + origin_report_id` ou la clé
   d'idempotence ;
4. créer le dossier, la conversation et l'audit dans une transaction ;
5. répondre avec l'état réel : reçu, déjà reçu ou en attente de traitement.

Une même clé avec un contenu différent est rejetée.

## 6. Contrats HTTP

### Création interservice

```http
POST /support/v1/internal/cases
Authorization: Bearer <service-jwt>
X-Client-ID: <origin-service-client>
Idempotency-Key: <stable-operation-key>
X-Request-ID: <request-id>
```

Le corps contient uniquement les informations nécessaires au traitement :

```json
{
  "origin_service": "diddigo",
  "resource_type": "ride",
  "resource_id": "uuid",
  "origin_report_id": "ride-report-123",
  "reporter_user_id": "uuid",
  "category": "safety",
  "priority": "high",
  "initial_message": "Description fournie par l'utilisateur",
  "urgent": false
}
```

### Contexte métier

DiddiSupport ne lit pas les bases des modules. Il demande un contexte limité au
module propriétaire :

```http
GET /internal/v1/support/{resource_type}/{resource_id}/context
```

L'appel utilise un token DiddiSupport avec un scope propre au module, par
exemple `diddigo:support-context:read`.

La réponse ne contient que les éléments nécessaires au support : état, acteurs
utiles, chronologie limitée et références métier. Les documents KYC, secrets,
numéros non nécessaires et données sans rapport sont exclus.

### Dossier côté utilisateur

Le transport actuel de DiddiComms reste compatible avec ces principes :

```text
POST /comms/v1/support/cases
GET  /comms/v1/support/cases/{case_id}
POST /comms/v1/support/cases/{case_id}/messages
```

Si DiddiSupport devient un service déployé séparément, ces routes seront
versionnées sous `/support/v1` avec un adaptateur de compatibilité. Les clients
ne doivent pas connaître la base de données ni les détails du fournisseur de
chat.

## 7. Événements

Les événements sont au moins distribués une fois et portent une enveloppe
commune :

```json
{
  "event_id": "uuid",
  "event_type": "support.case.created",
  "event_version": 1,
  "occurred_at": "2026-10-19T12:00:00Z",
  "producer": "diddi-support",
  "aggregate_type": "support_case",
  "aggregate_id": "uuid",
  "correlation_id": "request-id",
  "causation_id": "optional-event-id",
  "payload": {}
}
```

Événements initiaux :

- `support.case.created` ;
- `support.case.updated` ;
- `support.case.assigned` ;
- `support.case.message.created` ;
- `support.case.resolved` ;
- `support.sos.created` ;
- `support.sos.acknowledged` ;
- `support.sos.escalated` ;
- `support.action.requested` ;
- `support.action.completed` ;
- `support.action.failed`.

Les consommateurs dédupliquent sur `event_id` et accusent réception après
commit local. Une notification WebSocket ou push n'est pas un événement métier
durable.

## 8. Pièces jointes

Le module utilisateur obtient un dépôt auprès de DiddiFiles, avec un usage
spécifique tel que :

```text
diddisupport_case_photo
diddisupport_case_voice
diddisupport_case_document
```

DiddiSupport conserve :

- `file_id` ;
- le dossier et éventuellement le message ;
- l'auteur ;
- le type média ;
- l'état de contrôle.

L'accès à une preuve exige une autorisation DiddiSupport puis une URL
temporaire DiddiFiles. Une transcription vocale est un dérivé identifié et ne
remplace jamais l'original.

## 9. Erreurs communes

| Code | Signification |
|---|---|
| `SERVICE_TOKEN_REQUIRED` | Token service absent ou de type incorrect |
| `SERVICE_SCOPE_FORBIDDEN` | Scope insuffisant |
| `RESOURCE_NOT_FOUND` | Référence métier inconnue ou non visible |
| `SUPPORT_ACCESS_DENIED` | Utilisateur non autorisé à consulter le dossier |
| `IDEMPOTENCY_CONFLICT` | Même clé réutilisée avec un contenu différent |
| `INVALID_STATE_TRANSITION` | Transition du dossier interdite |
| `DEPENDENCY_UNAVAILABLE` | Module dépendant indisponible |
| `ATTACHMENT_NOT_AUTHORIZED` | Fichier non autorisé pour ce dossier |
| `ACTION_RESULT_UNKNOWN` | Résultat distant non confirmé après timeout |
| `SOS_ALREADY_ACKNOWLEDGED` | Prise en charge déjà enregistrée |

Les réponses d'erreur contiennent un code stable, un message sûr pour le
client et le `request_id`. Elles ne révèlent ni token, ni contenu privé, ni
raison sensible à un autre participant.

## 10. Compatibilité et gouvernance

- Une modification incompatible crée une nouvelle version majeure du manifest.
- Une nouvelle route ou un nouveau scope doit être ajouté au manifest avant son
  déploiement.
- Chaque module fournit des tests de contrat pour ses endpoints et événements.
- Le manifest est versionné dans Git et validé par revue ; il n'est pas exposé
  comme endpoint public de découverte.
- Les routes non présentes dans le manifest ne sont pas considérées comme
  intégrées.

## 11. Politique de configuration

La configuration d'exécution est injectée par variables d'environnement et
validée au démarrage. Elle ne doit pas modifier silencieusement les règles
métier ou les permissions.

### Variables d'environnement

Sont concernés notamment :

- URLs des services et fournisseurs ;
- audience, client ID et endpoint de token ;
- secrets et clés de chiffrement ;
- base de données, Redis et stockage ;
- timeouts réseau, nombre de retries et concurrence des workers ;
- niveau de logs, métriques et traces ;
- activation technique d'une intégration déjà contractée.

Toute variable obligatoire doit avoir une validation de type, de format et de
cohérence. Une valeur invalide bloque le démarrage plutôt que de produire un
comportement partiel.

### Règles versionnées nécessitant un redeploiement

Les éléments suivants restent dans le code ou dans un contrat versionné :

- transitions et invariants des dossiers ;
- états et transitions SOS ;
- permissions et scopes ;
- catégories de preuves et types de pièces ;
- actions financières ou métier autorisées ;
- enveloppes d'événements et codes d'erreur ;
- règles de confidentialité et visibilité des messages ;
- règles qui peuvent modifier le résultat métier ou la sécurité.

Ces règles ne doivent pas être facilement modifiables par une simple variable
d'environnement. Leur évolution passe par revue, tests, documentation et
redeploiement.

### Principe de sécurité

Une variable d'environnement peut régler le fonctionnement technique, mais ne
peut pas accorder un nouveau privilège, contourner une vérification ou rendre
une action financière possible sans modification versionnée du contrat.
