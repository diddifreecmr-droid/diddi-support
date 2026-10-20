# Permissions DiddiSupport

Les permissions sont contrôlées côté API et non uniquement dans le Backoffice.

| Permission | Capacité |
|---|---|
| `diddi-support:read` | Lire les dossiers autorisés |
| `diddi-support:reply` | Répondre à l'utilisateur |
| `diddi-support:assign` | Affecter ou transférer un dossier |
| `diddi-support:sos-operate` | Prendre en charge ou escalader un SOS |
| `diddi-support:attachments-read` | Consulter les preuves autorisées |
| `diddi-support:audit-read` | Lire l'historique d'audit |

La consultation d'un contexte métier via DiddiSupport requiert également la
permission de service `diddi-support:cases:read`. Le module propriétaire
applique sa propre permission `owner:support-context:read`.

Le consommateur autorisé du contexte est explicitement `diddicomms` avec le
sujet `service:diddicomms`. Son `client_id` doit correspondre à
`DIDDICOMMS_SERVICE_CLIENT_ID` lorsqu'il est configuré.

Pour le Backoffice, l'agent doit présenter un JWT utilisateur actif destiné à
`BACKOFFICE_AUDIENCE` et posséder `diddi-support:read`. Les scopes de service
et les permissions d'agent ne sont pas interchangeables.

Les actions d'écriture sont séparées : `diddi-support:assign` pour affecter un
dossier et `diddi-support:write` pour changer son statut.

Une permission de lecture ne permet pas une décision métier ou financière.
