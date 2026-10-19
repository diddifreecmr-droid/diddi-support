# Configuration DiddiSupport

## Variables d'environnement

Les variables d'environnement configurent le déploiement et le fonctionnement
technique : URLs de services, tokens, audiences, identifiants clients,
PostgreSQL, Redis, stockage, timeouts, retries, workers et observabilité.

Chaque variable doit être documentée avec son type, son caractère obligatoire,
sa valeur par défaut éventuelle et son comportement si elle est invalide.

## Redeploiement obligatoire

Les règles suivantes ne sont pas des variables facilement modifiables :

- transitions de dossiers et de SOS ;
- permissions et scopes ;
- catégories sensibles ;
- actions métier et financières ;
- visibilité des messages ;
- codes d'erreur et événements ;
- règles de confidentialité.

Une modification de ces règles exige code ou contrat versionné, tests,
documentation, validation Docker et redeploiement.

