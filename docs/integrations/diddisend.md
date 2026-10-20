# Intégration DiddiSend

Statut : `implemented` pour le contrat `diddi.context.v1`, activation réseau
en attente de l'URL et des identifiants de service DiddiSend.

DiddiSupport interroge `diddisend` pour `delivery` avec le scope
`diddisend:support-context:read`. DiddiSend reste propriétaire du statut et
des informations opérationnelles de livraison.

## Contrat propriétaire

`GET /internal/v1/support/delivery/{delivery_id}/context`

La réponse utilise l'enveloppe standard `diddi.context.v1`. Le champ `data`
contient le statut, le mode de livraison, les montants et devise, le mode et
statut de paiement, les participants identifiés par UUID et la chronologie.
Les téléphones, adresses, coordonnées brutes, PIN et détails du prestataire de
paiement sont explicitement exclus et listés dans `redacted_fields`.

Authentification : token DiddiFreeID `client_credentials`, audience
`diddisend`, scope `diddisend:support-context:read`, sujet
`service:diddisupport`, et en-tête `X-Support-Context-Scope` identique au
scope.
