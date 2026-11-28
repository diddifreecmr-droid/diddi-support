# Journal P2-B — Audit de la raison Backoffice

- Statut : TERMINÉ
- Implémentation : la raison reçue par le dependency d'authentification est
  placée dans un contexte de requête et ajoutée aux métadonnées des audits
  persistants sous `backoffice_reason` lorsqu'elle existe.
- Nettoyage : le contexte est réinitialisé par le middleware après la réponse.
- Vérification : 64 tests passent ; lint ciblé du repository et du contexte passe.
