# Contrat de contexte métier `diddi.context.v1`

DiddiSupport ne devient pas propriétaire des courses, commandes, livraisons,
paiements ou paies. Il interroge le module qui possède la donnée via un
connecteur configuré au déploiement.

## Appel sortant standard

Pour un propriétaire `diddigo` et une ressource `ride`, DiddiSupport appelle :

```text
GET {base_url}/internal/v1/support/ride/{resource_id}/context
```

Headers obligatoires :

- `Authorization: Bearer <service-token>` si le token sortant est configuré ;
- `X-Client-ID` si l'identifiant client est configuré ;
- `X-Request-ID` propagé depuis la requête support ;
- `X-Support-Context-Scope: {owner}:support-context:read`.

## Réponse obligatoire

```json
{
  "protocol": "diddi.context.v1",
  "origin_service": "diddigo",
  "resource_type": "ride",
  "resource_id": "11111111-1111-1111-1111-111111111111",
  "data": {
    "status": "completed",
    "fare": { "amount": 2500, "currency": "XAF" }
  },
  "redacted_fields": ["driver.phone"]
}
```

Le module propriétaire reste responsable de l’autorisation, de la fraîcheur
et de la minimisation des données. Les champs sensibles doivent être masqués
par le propriétaire et déclarés dans `redacted_fields`.

## Endpoint DiddiSupport

Les clients internes autorisés peuvent demander le contexte à DiddiSupport :

```text
GET /support/v1/internal/context/{origin_service}/{resource_type}/{resource_id}
```

Permission requise : `diddi-support:cases:read`.

Réponses principales : `404` si aucun connecteur ou contexte n’est disponible,
`503` si le module propriétaire est indisponible, et `403` si la permission
manque. DiddiSupport ne met pas encore ces réponses en cache afin d’éviter de
présenter un état métier périmé.
