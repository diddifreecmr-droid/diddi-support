# Contrat frontend Support

Ce document décrit la façade publique attendue pour le frontend. Il s'adresse
aux équipes frontend et DiddiComms. Les routes marquées `PRÉVU` ne sont pas
encore exposées par DiddiSupport et ne doivent pas être appelées.

## Positionnement

Le frontend appelle DiddiComms. DiddiComms authentifie l'utilisateur puis
appelle les routes internes de DiddiSupport avec son identité de service.

```text
Frontend → DiddiComms public → DiddiSupport interne → contexte métier
```

Le frontend ne reçoit jamais de secret S2S, de token Redis ou de données de
base de données métier.

## Routes publiques

Les routes publiques suivantes sont le contrat cible de DiddiComms et sont
`PRÉVU` tant que leur OpenAPI DiddiComms n'est pas publié :

| Méthode | Route | Usage |
| --- | --- | --- |
| `POST` | `/comms/v1/support/cases` | créer ou retrouver un dossier |
| `GET` | `/comms/v1/support/cases` | lister les dossiers de l'utilisateur |
| `GET` | `/comms/v1/support/cases/{case_id}` | lire un dossier autorisé |
| `GET` | `/comms/v1/support/cases/{case_id}/messages` | lire la conversation |
| `POST` | `/comms/v1/support/cases/{case_id}/messages` | envoyer un message |

À CONFIRMER : DiddiComms doit publier ces routes et leurs schémas OpenAPI
avant toute implémentation frontend.

## Création d'un dossier

### Requête cible

```json
{
  "category": "payment_issue",
  "message": "Le paiement est affiché comme échoué.",
  "resource": {
    "type": "ride",
    "id": "11111111-1111-1111-1111-111111111111"
  },
  "attachments": []
}
```

`category` et `message` sont obligatoires. `resource` et `attachments` sont
optionnels selon le parcours. Le frontend ne fournit pas `user_id`, le rôle,
`origin_service` ni les participants.

À CONFIRMER : liste définitive des catégories, format des pièces jointes et
limite de taille avant publication de l'OpenAPI public.

### Réponse cible

```json
{
  "case_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "status": "open",
  "created": true,
  "conversation_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
}
```

Le serveur doit dédupliquer avec `Idempotency-Key`. Une répétition avec la
même clé et le même contenu retourne le dossier existant ; la même clé avec un
contenu différent retourne `409`.

## Message utilisateur

```json
{
  "body": "Je souhaite ajouter une précision.",
  "attachments": []
}
```

Le message utilisateur devient `user_visible`. Une note interne n'est jamais
créée par le frontend.

## Authentification et erreurs

Le frontend utilise le JWT utilisateur DiddiFreeID :

```http
Authorization: Bearer <user-jwt>
Idempotency-Key: <clé-stable-pour-l'opération>
X-Request-ID: <identifiant-de-corrélation>
```

| HTTP | Code | Action frontend |
| --- | --- | --- |
| `401` | `TOKEN_MISSING` ou `TOKEN_INVALID` | renouveler la session |
| `403` | `SUPPORT_ACCESS_FORBIDDEN` | masquer l'action |
| `404` | `CASE_NOT_FOUND` ou `RESOURCE_NOT_FOUND` | actualiser l'écran |
| `409` | `IDEMPOTENCY_CONFLICT` ou `CASE_ALREADY_EXISTS` | afficher l'état existant |
| `422` | `VALIDATION_ERROR` | corriger le formulaire |
| `429` | `RATE_LIMITED` | respecter le retry indiqué |
| `503` | `DEPENDENCY_UNAVAILABLE` | proposer un nouvel essai |

À CONFIRMER : codes finaux de la façade DiddiComms. Cette table est un contrat
cible, pas une preuve d'implémentation actuelle.

## Données et formats

- Les identifiants sont des UUID sauf indication contraire.
- Les dates sont ISO 8601 en UTC.
- Les montants portent leur devise dans le champ ou la documentation.
- `null` signifie une valeur connue comme absente ; un champ absent signifie
  qu'il n'est pas applicable ou non autorisé.
- Le frontend ne lit jamais `diddisupport.events` directement.

## Contrat interne correspondant

Après authentification par DiddiComms, DiddiSupport expose déjà :

- `POST /support/v1/internal/cases` ;
- `GET /support/v1/internal/context/{origin_service}/{resource_type}/{resource_id}` ;
- `POST /support/v1/internal/cases/{case_id}/messages`.

Ces routes utilisent un JWT de service, des scopes S2S et une clé d'idempotence.
Elles ne doivent pas être copiées dans le client frontend.
