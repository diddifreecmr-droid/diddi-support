# Intégration DiddiPay

Statut : `proposed` pour le connecteur réseau, `implemented` pour le contrat
d'état des actions.

DiddiSupport demande une action `diddipay.refund` avec une clé d'opération
stable. DiddiPay confirme ensuite le résultat par l'endpoint interne de
résultat. Seule une confirmation avec `provider_reference` produit l'état
`succeeded`; un délai d'attente reste `unknown`.
