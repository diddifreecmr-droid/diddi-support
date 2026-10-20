# Parcours SOS

Une alerte SOS peut être liée à un dossier ou exister seule. Le module garde
deux états indépendants : notification (`recorded`, `pending`, `sent`,
`failed`) et prise en charge (`unconfirmed`, `confirmed`, `in_progress`,
`completed`).

La confirmation explicite d'un agent disposant de `diddi-support:sos-operate`
est obligatoire avant le démarrage ou la clôture. Une alerte non confirmée ne
doit donc jamais être présentée comme prise en charge.

Quand DiddiGo fournit un `source_alert_id`, il est utilisé pour l'idempotence.
Si DiddiGo indique que sa notification est déjà envoyée, DiddiSupport ne crée
pas de seconde demande. Les échecs sont rejouables jusqu'à
`SOS_MAX_NOTIFICATION_ATTEMPTS`, puis escaladés.
