# DiddiSupport → DiddiComms : événements outbox

## Stream

Le worker `diddi_support.ops.outbox_worker` publie dans le stream Redis
`diddisupport.events`. Chaque entrée contient un champ `event` avec cette
enveloppe JSON :

```json
{
  "event_id": "33333333-3333-3333-3333-333333333333",
  "event_type": "support.case.message.created.v1",
  "aggregate_id": "11111111-1111-1111-1111-111111111111",
  "aggregate_version": 4,
  "occurred_at": "2026-10-21T00:00:00+00:00",
  "payload": {
    "case_id": "11111111-1111-1111-1111-111111111111",
    "message_id": "22222222-2222-2222-2222-222222222222",
    "visibility": "user_visible"
  }
}
```

Le corps du message, les notes internes, les identifiants privés et les
données métier sensibles ne sont jamais publiés.

## Types versionnés

- `support.case.created.v1`
- `support.case.updated.v1`
- `support.case.assigned.v1`
- `support.case.message.created.v1`
- `support.case.resolved.v1`

Une réponse agent `user_visible` produit un événement de message. Une note
`internal_note` n'entre pas dans l'outbox et ne produit pas de notification
utilisateur. Une version plus ancienne doit être ignorée par DiddiComms.

## Garantie et rejeu

L'écriture métier et l'outbox sont validées dans la même transaction
PostgreSQL. Le worker fait un `XADD`, puis renseigne `published_at` seulement
après le succès de Redis. Une panne entre ces deux opérations peut produire un
doublon : DiddiComms doit dédupliquer par `event_id`.

Les événements sont verrouillés par un bail (`lease_until`) pour éviter deux
publications concurrentes. Les échecs sont retentés avec backoff exponentiel.
Après `OUTBOX_MAX_ATTEMPTS`, l'événement est placé en quarantaine via
`quarantined_at` et `last_error`.

La rétention Redis est bornée par `OUTBOX_STREAM_MAXLEN`.

## Métriques et alertes

Le worker expose Prometheus sur `OUTBOX_METRICS_PORT` (9105 par défaut) :

- `diddisupport_outbox_pending`
- `diddisupport_outbox_oldest_age_seconds`
- `diddisupport_outbox_published_total`
- `diddisupport_outbox_failed_total`
- `diddisupport_outbox_quarantined_total`

Les règles d'alerte sont dans
`deploy/observability/prometheus/support-alerts.yml`.
