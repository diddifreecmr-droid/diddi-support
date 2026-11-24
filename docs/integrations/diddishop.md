# Intégration DiddiShop

Statut : contrat et connecteur DiddiSupport implémentés. L'activation staging
reste conditionnée à l'injection des URLs et identifiants S2S DiddiShop.

DiddiShop reste propriétaire des commandes. DiddiSupport ne stocke qu'une
référence vers la commande et interroge DiddiShop pour le contexte métier.

## Contexte commande

DiddiSupport appelle :

```http
GET /internal/v1/support/order/{order_id}/context
```

La réponse doit respecter l'enveloppe `diddi.context.v1` :

```json
{
  "protocol": "diddi.context.v1",
  "origin_service": "diddishop",
  "resource_type": "order",
  "resource_id": "11111111-1111-1111-1111-111111111111",
  "data": {
    "status": "paid"
  },
  "redacted_fields": [],
  "as_of": "2026-11-24T10:00:00Z",
  "fetched_at": "2026-11-24T10:00:01Z"
}
```

Authentification sortante : token DiddiFreeID `client_credentials`, audience
`diddishop`, scope `diddishop:support-context:read`, et en-tête
`X-Support-Context-Scope: diddishop:support-context:read`.

## Ouverture d'un dossier

```http
POST /support/v1/internal/cases
Authorization: Bearer <service-token>
Idempotency-Key: diddishop-order-complaint-123
X-Request-ID: <uuid>
```

```json
{
  "origin_service": "diddishop",
  "resource_type": "order",
  "resource_id": "11111111-1111-1111-1111-111111111111",
  "origin_report_id": "diddishop-report-123",
  "reporter_user_id": "22222222-2222-2222-2222-222222222222",
  "category": "order_missing_item",
  "subject": "Article manquant dans la commande",
  "priority": "normal"
}
```

Le token d'appel direct DiddiShop utilise l'audience `diddi-support`, le sujet
`service:diddishop` et le scope `diddi-support:cases:create`. DiddiComms peut
également ouvrir un dossier par délégation avec `origin_service=diddishop`.

## Idempotence

La clé `Idempotency-Key` est obligatoire. Une nouvelle tentative avec la même
clé et le même payload retourne le même dossier. La même clé avec un payload
différent retourne `409 IDEMPOTENCY_CONFLICT`. Les retries réutilisent la même
clé et le même `X-Request-ID`.

## Catégories recommandées

`order_missing_item`, `order_wrong_item`, `order_damaged`, `order_late`,
`order_cancelled`, `order_refund`, `order_payment`, `order_vendor_issue`,
`order_delivery_issue`, `order_other`.

Le champ est actuellement une chaîne contractuelle de 1 à 80 caractères ;
cette liste doit donc être respectée par les clients jusqu'à l'introduction
d'une énumération versionnée.

## Actions de commande

Aucune action `diddishop.*` n'est actuellement exposée par DiddiSupport.
DiddiShop reste le système d'exécution des commandes. Toute action telle que
annulation, remboursement ou remplacement devra faire l'objet d'un contrat
versionné séparé avant d'être ajoutée aux actions Support.
