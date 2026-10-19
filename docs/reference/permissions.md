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

Une permission de lecture ne permet pas une décision métier ou financière.
