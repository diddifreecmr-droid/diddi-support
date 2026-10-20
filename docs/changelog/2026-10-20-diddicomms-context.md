# DiddiSupport — appelant DiddiComms

- DiddiComms est désormais déclaré comme consommateur autorisé du contexte
  métier DiddiSupport.
- Les routes internes de lecture de contexte exigent le sujet
  `service:diddicomms`.
- Le `client_id` DiddiComms peut être verrouillé par environnement avec
  `DIDDICOMMS_SERVICE_CLIENT_ID`.
- L’URL staging DiddiSend est préparée dans la configuration du connecteur.
