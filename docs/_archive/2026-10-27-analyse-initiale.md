# Analyse initiale DiddiSupport — 27 octobre 2026

Ce document conserve l'état observé avant la mise en conformité documentaire.
Il s'adresse aux mainteneurs et aux équipes d'intégration.

## 1. Ce que fait le module

DiddiSupport centralise les dossiers, messages, affectations, résolutions,
actions support, SOS et audit. Il expose des routes internes protégées pour
DiddiComms et des routes de contexte pour lire les informations limitées des
modules propriétaires. Il publie les événements Support dans Redis Streams via
une outbox transactionnelle.

## 2. Ce qui est réellement fait dans le code

- Création idempotente et lecture de dossiers.
- Messages utilisateur visibles et notes internes.
- Affectation, transfert, résolution et actions support.
- Contexte métier via DiddiGo, DiddiFood, DiddiSend et DiddiPay selon la
  configuration.
- Publication `diddisupport.events` avec retries, quarantaine et métriques.
- Migrations PostgreSQL automatiques avec `support-migrate`.

## 3. Ce qui est prévu mais pas fait

- PRÉVU : façade publique frontend complète dans DiddiComms.
- PRÉVU : WebSocket public Support.
- PRÉVU : contrat public final pour catégories et pièces jointes.

## 4. Contradictions observées

- Les routes internes DiddiSupport sont implémentées, mais le contrat frontend
  public reste documenté comme cible dans DiddiComms.
- Le frontend DiddiGo prépare un signalement de course, mais sa route publique
  de création de dossier Support n'est pas publiée.

## 5. Parcours métier trouvés

- Signalement d'une course DiddiGo par passager ou chauffeur.
- SOS pendant une course DiddiGo.
- Réclamation d'une livraison DiddiSend.
- Signalement lié à une commande DiddiFood.
- Demande générale et conversation avec le support.
- Affectation, traitement et résolution par un agent.

## 6. Modules externes appelés

- DiddiGo : contexte de course.
- DiddiSend : contexte de livraison.
- DiddiFood : contexte de commande.
- DiddiPay : contexte de paiement.
- DiddiFiles : métadonnées et accès temporaire aux pièces jointes.
- DiddiFreeID : identité et jetons de service.
- DiddiComms : conversation, notifications et consommation des événements.

## 7. Configuration trouvée

Les variables sont listées dans `env/.env.example` et
`docs/reference/configuration.md`. Les valeurs sensibles restent vides dans
les exemples et doivent être injectées par Portainer.

## 8. Statuts trouvés

Les dossiers utilisent `open`, `in_progress`, `waiting_user`,
`waiting_internal`, `resolved` et `closed`. Les SOS et actions ont leurs
propres statuts documentés dans `docs/reference/`.

## 9. Informations manquantes

- À CONFIRMER : contrat public final DiddiComms.
- À CONFIRMER : catégories frontend et contrat des pièces jointes.
- À CONFIRMER : politique publique de pagination et de refresh JWT.
