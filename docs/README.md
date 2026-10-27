# Documentation DiddiSupport

Ce dossier décrit les contrats réellement livrés de DiddiSupport et s'adresse
aux équipes backend, frontend, support et intégration.

- [API](api/), [guides](guides/), [temps réel](realtime/), [intégrations](integrations/)
- [référence](reference/), [changements](changelog/) et [_archive](_archive/)
- [configuration d'environnement](../env/)

## Hors périmètre pour l'instant

- Le contrat frontend public est `PRÉVU` via la façade DiddiComms ; les routes
  internes S2S de DiddiSupport ne sont pas des routes frontend.
- Aucun WebSocket DiddiSupport n'est livré ; les deux fichiers realtime le
  signalent explicitement.

`api/openapi.json` est généré depuis l'application avec
`python scripts/generate_openapi.py`. Une fonctionnalité non implémentée est
marquée `PRÉVU` et ne doit pas être utilisée par un client.
