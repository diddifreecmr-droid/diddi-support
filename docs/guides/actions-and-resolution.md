# Actions métier et paiements

Une action Support est une décision enregistrée, pas une preuve d'exécution.
Elle suit `requested`, `pending`, `succeeded`, `failed` ou `unknown` et porte
une `operation_key` stable pour rendre les retries idempotents.

Le résultat `succeeded` exige la référence du module propriétaire. DiddiSupport
n'affiche donc jamais « remboursé » avant la confirmation de DiddiPay. Un
timeout devient `unknown` et doit être récupéré avec la même clé d'opération.
