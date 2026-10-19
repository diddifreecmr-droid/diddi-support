# File de support Backoffice

## Consulter la file

```text
GET /support/v1/backoffice/cases?status=open&priority=high&limit=50
```

Permission : `diddi-support:read`.

La réponse est triée par date de création. Les filtres `status` et `priority`
sont optionnels et `limit` est borné à 100.

## Affecter un dossier

```text
POST /support/v1/backoffice/cases/{case_id}/assign
Authorization: Bearer <agent-user-token>
Content-Type: application/json

{ "agent_id": "44444444-4444-4444-4444-444444444444" }
```

Permission : `diddi-support:assign`.

## Changer le statut

```text
POST /support/v1/backoffice/cases/{case_id}/transition
Authorization: Bearer <agent-user-token>
Content-Type: application/json

{ "status": "in_progress" }
```

Permission : `diddi-support:write`.

Les transitions sont contrôlées par le domaine. Une transition invalide
retourne `409 INVALID_CASE_TRANSITION` et ne produit aucune modification.
Chaque affectation et transition validée génère un événement d’audit et un
événement outbox.
