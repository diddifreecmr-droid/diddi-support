# Contrat DiddiComms ↔ DiddiSupport

Statut : `contract-frozen`, implémentation conversationnelle à venir.

DiddiComms est le point d'entrée des utilisateurs et l'interface des agents.
DiddiSupport reste propriétaire des dossiers, des messages, des statuts, de
l'audit et des actions Support.

## Identité

Les appels service-to-service de DiddiComms utilisent :

- audience : `diddi-support` ;
- sujet : `service:diddicomms` ;
- scope de création : `diddi-support:cases:create` ;
- scope de lecture : `diddi-support:cases:read` ;
- `X-Client-ID` correspondant à `DIDDICOMMS_SERVICE_CLIENT_ID` ;
- `X-Request-ID` obligatoire pour la corrélation.

## Création d'un dossier depuis DiddiComms

```http
POST /support/v1/internal/cases
Authorization: Bearer <service-token>
X-Client-ID: <diddicomms-client-id>
X-Request-ID: <request-id>
Idempotency-Key: <stable-key>
```

Le corps contient la référence métier et l'utilisateur concerné :

```json
{
  "origin_service": "diddigo",
  "resource_type": "ride",
  "resource_id": "11111111-1111-1111-1111-111111111111",
  "origin_report_id": "comms-report-123",
  "reporter_user_id": "22222222-2222-2222-2222-222222222222",
  "category": "ride_issue",
  "subject": "Problème pendant la course",
  "priority": "normal"
}
```

`origin_service` indique le propriétaire de la ressource, pas l'appelant.
DiddiSupport audite séparément `service:diddicomms` comme créateur technique
et `reporter_user_id` comme utilisateur à l'origine du signalement.

Deux appels avec la même `Idempotency-Key` et le même contenu retournent le
même dossier. Une réutilisation avec un contenu différent retourne
`409 IDEMPOTENCY_CONFLICT`.

## Messages utilisateur

La future route interne dédiée sera :

```http
POST /support/v1/internal/cases/{case_id}/messages
```

Elle permettra à DiddiComms de transmettre un message utilisateur à Support.
Le message sera créé avec `author_type=user`, `author_id=reporter_user_id` et
une visibilité `user_visible`. La clé d'idempotence sera obligatoire.

DiddiComms recevra les réponses agent `user_visible` via l'API de lecture et,
à terme, via l'événement `support.case.message.created`. Les notes
`internal_note` resteront invisibles à l'utilisateur.

## Erreurs contractuelles

| HTTP | Code | Situation |
|---:|---|---|
| 400 | `IDEMPOTENCY_KEY_REQUIRED` | clé absente |
| 401 | `SERVICE_TOKEN_REQUIRED` ou `SERVICE_TOKEN_INVALID` | identité invalide |
| 403 | `SERVICE_SCOPE_FORBIDDEN` | scope manquant |
| 403 | `CONTEXT_CALLER_FORBIDDEN` | appelant non autorisé |
| 404 | `CASE_NOT_FOUND` | dossier inexistant |
| 409 | `IDEMPOTENCY_CONFLICT` | clé réutilisée avec un autre contenu |
| 503 | `SUPPORT_UNAVAILABLE` | Support temporairement indisponible |

## Responsabilités

DiddiComms transporte les échanges et notifie l'utilisateur. DiddiSupport
persiste le dossier et l'historique. Le module métier reste propriétaire de la
course, commande, livraison ou opération financière référencée.
