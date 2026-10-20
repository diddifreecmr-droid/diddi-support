# DiddiSupport — appelant DiddiComms

- DiddiComms est désormais déclaré comme consommateur autorisé du contexte
  métier DiddiSupport.
- Les routes internes de lecture de contexte exigent le sujet
  `service:diddicomms`.
- Le `client_id` DiddiComms peut être verrouillé par environnement avec
  `DIDDICOMMS_SERVICE_CLIENT_ID`.
- L’URL staging DiddiSend est préparée dans la configuration du connecteur.
- Le contrat DiddiComms de création de dossier et de conversation est figé ;
  les routes de messages internes restent planifiées pour le sprint suivant.
- Les claims service DiddiFreeID sont maintenant vérifiés de manière cohérente
  (`token_type`, `role`, `status`, `sub` et `service`).
