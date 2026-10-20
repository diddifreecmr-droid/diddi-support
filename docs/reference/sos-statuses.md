# États SOS

Les valeurs sont contractuelles et ne doivent pas être remplacées par un
booléen `handled`.

| Domaine | Valeurs |
| --- | --- |
| Notification | `recorded`, `pending`, `sent`, `failed` |
| Prise en charge | `unconfirmed`, `confirmed`, `in_progress`, `completed` |

Les paramètres de retry et d'escalade sont injectés par environnement :
`SOS_MAX_NOTIFICATION_ATTEMPTS` et `SOS_ESCALATION_AFTER_SECONDS`.
