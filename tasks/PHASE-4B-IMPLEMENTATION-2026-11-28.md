# Journal P4-B — Vérification staging/Portainer

- Statut : EN ATTENTE — configuration du déploiement staging à corriger.
- Test effectué sans mutation : DiddiFreeID émet un token valide avec les six
  scopes attendus ; DiddiSupport répond `401 BACKOFFICE_CLIENT_ID_FORBIDDEN`.
- Cause probable confirmée par le code métier : l'allowlist active ne contient
  pas `backoffice-staging-diddisupport`.
- Corrélation vérifiée : le `X-Request-ID` envoyé est retourné à l'identique.
- Branche `wip/` : aucune, car aucun code partiel ni test échoué n'est concerné.
- À exécuter ultérieurement : injecter `BACKOFFICE_SERVICE_CLIENT_IDS` dans le
  déploiement actif, puis rejouer la checklist de `docs/IMPLEMENTATION-STATUS.md`.
