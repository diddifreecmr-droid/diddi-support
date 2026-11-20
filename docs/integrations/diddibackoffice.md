# Contrat DiddiBackoffice ↔ DiddiSupport

Statut : `DiddiSupport livré — intégration DiddiBackoffice à réaliser`.

Ce document décrit l'intégration du Backoffice avec DiddiSupport. Il ne crée
pas de routes dans DiddiBackoffice et ne remplace pas le contrat OpenAPI
canonique : [`docs/api/openapi.json`](../api/openapi.json).

## Responsabilités

| Composant | Responsabilité |
|---|---|
| DiddiBackoffice | Interface agent, session utilisateur, contrôle d'accès UI, filtres et affichage |
| BFF/API du Backoffice | Conserver les secrets, obtenir le token de service, appeler DiddiSupport, propager la corrélation |
| DiddiSupport | Dossiers, messages, statuts, affectation, audit, actions Support, SOS et références de fichiers |
| Module métier | Source de vérité de la course, commande, livraison ou opération financière référencée |
| DiddiComms | Conversation et notifications utilisateur ; ce n'est pas l'inbox agent du Backoffice |
| DiddiFreeID | Émission et validation des identités et tokens |

Le navigateur ne doit pas appeler directement DiddiSupport avec un secret de
service. Le Backoffice doit passer par son BFF ou son backend sécurisé.

## Base URL et version

En staging, la base attendue est :

```text
https://support-backend-staging.diddifree.com
```

Les routes sont préfixées par `/support/v1/backoffice`. Le client doit charger
les chemins et les schémas depuis l'OpenAPI ; il ne doit pas reconstruire les
réponses à partir de détails internes de la base de données.

## Authentification

### Appel recommandé : BFF du Backoffice

Le BFF appelle DiddiSupport avec un JWT de service représentant
`service:diddiadmin`, accompagné de l'agent qui a déclenché l'action :

```http
Authorization: Bearer <service-token>
X-Client-ID: <diddiadmin-client-id>
X-Backoffice-Actor: <agent-user-uuid>
X-Backoffice-Reason: <raison-courte>
X-Request-ID: <correlation-id>
```

Le token doit être actif, de type service, destiné à l'audience Support et
porter les scopes `diddi-support:*` nécessaires. `X-Backoffice-Actor` est un
UUID d'agent et `X-Backoffice-Reason` est obligatoire pour l'audit, avec une
longueur maximale de 200 caractères.

### Appel avec JWT d'agent

Les routes acceptent aussi un JWT utilisateur actif destiné à
`BACKOFFICE_AUDIENCE` (valeur par défaut : `diddi-comms-backoffice`) et portant
les permissions Support. Cette option est utile pour un backend déjà intégré à
l'identité agent ; elle ne doit pas exposer de secret au navigateur.

Les permissions sont contrôlées par DiddiSupport, même si le Backoffice masque
déjà les boutons correspondants.

## Permissions

| Permission | Autorise |
|---|---|
| `diddi-support:read` | Lire les dossiers, messages, timeline, contexte et files autorisés |
| `diddi-support:reply` | Envoyer une réponse visible à l'utilisateur, demander une prise en charge humaine |
| `diddi-support:write` | Ajouter une note interne, changer le statut, exécuter les écritures Support |
| `diddi-support:assign` | Affecter ou transférer un dossier |
| `diddi-support:sos-operate` | Confirmer, démarrer, terminer ou relancer un SOS |
| `diddi-support:attachments-read` | Lire les pièces jointes et demander un accès temporaire |
| `diddi-support:audit-read` | Accéder aux éléments d'audit autorisés |

## Routes disponibles

Toutes les routes ci-dessous utilisent le préfixe
`/support/v1/backoffice`.

| Méthode | Route | Usage | Permission principale |
|---|---|---|---|
| `GET` | `/cases` | File des dossiers, filtres `status`, `priority`, `limit` | `read` |
| `GET` | `/cases/{case_id}/context` | Dossier avec le contexte fourni par le module métier | `read` |
| `GET` | `/cases/{case_id}/messages` | Historique des messages du dossier | `read` |
| `POST` | `/cases/{case_id}/messages` | Réponse visible ou note interne | `reply` ou `write` |
| `GET` | `/cases/{case_id}/timeline` | Historique chronologique Support | `read` |
| `POST` | `/cases/{case_id}/assign` | Affecter à un agent | `assign` |
| `POST` | `/cases/{case_id}/transfer` | Transférer à un autre agent | `assign` |
| `POST` | `/cases/{case_id}/transition` | Changer le statut du dossier | `write` |
| `POST` | `/cases/{case_id}/handoff` | Demander ou activer le transfert vers un agent | `reply` ou `write` |
| `POST` | `/cases/{case_id}/attachments` | Référencer une pièce jointe DiddiFiles | `reply` |
| `GET` | `/cases/{case_id}/attachments` | Lister les pièces jointes autorisées | `attachments-read` |
| `POST` | `/cases/{case_id}/attachments/{attachment_id}/temporary-access` | Obtenir un accès temporaire DiddiFiles | `attachments-read` |
| `POST` | `/actions` | Demander une action métier Support | `write` |
| `GET` | `/actions/{action_id}` | Lire l'état d'une action | `read` |
| `GET` | `/sos` | File des alertes SOS | `read` |
| `POST` | `/sos/{alert_id}/confirm` | Confirmer une alerte | `sos-operate` |
| `POST` | `/sos/{alert_id}/start` | Démarrer la prise en charge | `sos-operate` |
| `POST` | `/sos/{alert_id}/complete` | Terminer la prise en charge | `sos-operate` |
| `POST` | `/sos/{alert_id}/retry-notification` | Relancer la notification SOS | `sos-operate` |

Les champs exacts des requêtes et réponses sont ceux de l'OpenAPI. Les UUID
doivent rester des UUID, les dates sont en ISO 8601 UTC et les valeurs d'enum
ne doivent pas être traduites côté client.

## Parcours agent recommandé

1. Charger `GET /cases?status=open&limit=50`.
2. Ouvrir le dossier avec `GET /cases/{case_id}/messages`,
   `GET /cases/{case_id}/timeline` et, si nécessaire,
   `GET /cases/{case_id}/context`.
3. Affecter le dossier avec `/assign` ou `/transfer`.
4. Répondre avec `POST /cases/{case_id}/messages` en utilisant
   `visibility=user_visible`, ou écrire une note avec
   `visibility=internal_note`.
5. Modifier le statut avec `/transition`.
6. Rafraîchir le dossier et la timeline après chaque commande réussie.

Une note `internal_note` reste interne. Elle ne doit jamais être présentée à
l'utilisateur ni déclencher une notification utilisateur via DiddiComms.

## Statuts et transitions

Les statuts actuels sont : `open`, `in_progress`, `waiting_user`,
`waiting_internal`, `resolved` et `closed`.

| Statut courant | Transitions autorisées |
|---|---|
| `open` | `in_progress`, `waiting_user`, `waiting_internal` |
| `in_progress` | `waiting_user`, `waiting_internal`, `resolved` |
| `waiting_user` | `in_progress`, `resolved` |
| `waiting_internal` | `in_progress`, `resolved` |
| `resolved` | `closed`, `in_progress` |
| `closed` | aucune |

Une transition refusée renvoie `409 INVALID_CASE_TRANSITION`. Un dossier
`resolved` ou `closed` ne peut pas recevoir de message ; le serveur renvoie
`409 CASE_NOT_MODIFIABLE`.

## Exemples minimaux

### Réponse agent visible

```http
POST /support/v1/backoffice/cases/<case-id>/messages
Authorization: Bearer <token>
X-Client-ID: <diddiadmin-client-id>
X-Backoffice-Actor: <agent-user-uuid>
X-Backoffice-Reason: Réponse au passager
X-Request-ID: <request-id>
Content-Type: application/json
```

```json
{
  "body": "Bonjour, nous avons bien pris en charge votre demande.",
  "visibility": "user_visible"
}
```

### Note interne

```json
{
  "body": "Vérifier le remboursement avec DiddiPay.",
  "visibility": "internal_note"
}
```

Une valeur `system_event` n'est pas autorisée pour la création d'un message
depuis le Backoffice.

### Changement de statut

```http
POST /support/v1/backoffice/cases/<case-id>/transition
Content-Type: application/json
```

```json
{
  "status": "in_progress"
}
```

## Erreurs et reprises

Les erreurs sont renvoyées dans une enveloppe `detail`, avec un code métier
stable lorsqu'il existe :

```json
{
  "detail": {
    "code": "CASE_NOT_FOUND",
    "message": "Support case not found"
  }
}
```

Codes fréquemment rencontrés : `401` pour une identité invalide, `403` pour une
permission manquante, `404 CASE_NOT_FOUND`, `409` pour une transition ou un
dossier non modifiable, `413` pour une pièce jointe trop volumineuse, `415`
pour un type MIME interdit et `503` pour une dépendance indisponible.

Les lectures `GET` peuvent être retentées avec backoff. Les commandes `POST`
ne doivent pas être retentées aveuglément : la route Backoffice de création de
message n'est pas documentée comme idempotente. Pour les actions métier,
utiliser le `operation_key` prévu par le schéma et conserver le même identifiant
lors d'un rejeu. Envoyer un `X-Request-ID` stable pour toute tentative logique.

## Contexte métier et confidentialité

Le contexte retourné par `/context` est une projection fournie par le module
propriétaire (`diddigo`, `diddifood`, `diddisend` ou `diddipay`). DiddiSupport
ne devient pas propriétaire de ces données et le Backoffice ne doit pas les
modifier directement.

Les corps de messages, notes internes, tokens et données sensibles ne doivent
pas être écrits dans les logs du Backoffice. Les pièces jointes passent par
DiddiFiles et doivent être consultées avec un accès temporaire, jamais avec un
secret permanent embarqué dans le frontend.

## Ce que DiddiBackoffice doit encore fournir

- un BFF sécurisé configuré avec l'identité `diddiadmin` et les scopes requis ;
- la propagation de `X-Request-ID`, `X-Backoffice-Actor` et
  `X-Backoffice-Reason` ;
- les écrans de file, détail, messages, affectation, statut, timeline et SOS ;
- la gestion des erreurs et des états de chargement ;
- les tests d'intégration contre l'OpenAPI et un environnement staging ;
- la configuration TLS correcte de `support-backend-staging.diddifree.com`.

Le dépôt DiddiBackoffice doit confirmer séparément ses routes BFF publiques,
car elles ne sont pas définies par DiddiSupport. Tant que cette façade n'existe
pas, le Backoffice ne doit pas exposer directement les routes internes Support
au navigateur.

## Références

- [OpenAPI DiddiSupport](../api/openapi.json)
- [Permissions](../reference/permissions.md)
- [Configuration](../reference/configuration.md)
- [Contexte métier](business-context.md)
- [Manifeste inter-modules](../../manifests/diddi-support.v1.json)
