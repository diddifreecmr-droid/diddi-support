# Statuts DiddiSupport

## Dossier

```text
open → in_progress → waiting_user
                  → waiting_internal
                  → resolved → closed
```

L'affectation à un agent est indépendante du statut.

## SOS

L'état de notification et l'état de prise en charge sont séparés.

```text
notification: recorded → pending → sent | failed
handling:     unacknowledged → acknowledged → in_progress → completed
```

Les transitions sont des règles versionnées et ne sont pas configurées par
une simple variable d'environnement.

