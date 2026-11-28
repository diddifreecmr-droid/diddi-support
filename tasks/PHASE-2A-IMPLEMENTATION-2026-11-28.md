# Journal P2-A — Authentification duale

- Statut : TERMINÉ
- Ajouts : `BACKOFFICE_SERVICE_CLIENT_IDS` via `backoffice_service_client_ids`,
  conversion du service principal en `BackofficePrincipal`, validation de
  `service:diddiadmin`, client ID, acteur UUID et raison facultative.
- Compatibilité : le JWT utilisateur continue d'utiliser `BACKOFFICE_AUDIENCE`
  et ses permissions.
- Vérification : `python -m pytest -q` → 62 passed, 1 warning ; lint ciblé passe.
