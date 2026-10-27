# Environnements DiddiSupport

Ce dossier contient les modèles de variables utilisés pour déployer
DiddiSupport. Il s'adresse aux développeurs et aux opérateurs Portainer.

Copier le modèle correspondant à l'environnement, remplir les emplacements
vides dans le gestionnaire de secrets, puis redéployer. Ne jamais committer un
secret réel. Une modification de configuration exige un redéploiement.

- `.env.example` : inventaire complet sans secrets.
- `development.env.example` : valeurs locales typiques.
- `staging.env.example` : valeurs staging à compléter dans Portainer.
- `production.env.example` : valeurs production à compléter dans le gestionnaire
  de secrets.
