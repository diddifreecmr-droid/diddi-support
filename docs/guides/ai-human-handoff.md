# IA et reprise humaine

Une conversation démarre en mode `ai`. Une demande de reprise passe en
`human_requested`, puis un agent habilité l'active en `human_active`.

Après activation humaine, le système doit refuser toute réponse IA concurrente
pour le dossier. L'IA ne peut pas déclencher seule une action administrative,
financière ou SOS. Si le fournisseur IA est indisponible, la création du
dossier et la demande de reprise restent disponibles.
