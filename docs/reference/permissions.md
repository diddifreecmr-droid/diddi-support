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

Pour le Backoffice, l'agent doit présenter un JWT utilisateur actif destiné à
`BACKOFFICE_AUDIENCE` et posséder `diddi-support:read`. Les scopes de service
et les permissions d'agent ne sont pas interchangeables.

Une permission de lecture ne permet pas une décision métier ou financière.
