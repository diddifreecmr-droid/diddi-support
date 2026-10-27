# Stratégie de reconnexion DiddiSupport

Ce document indique comment un client frontend récupère son état après une
perte de connexion. Il s'adresse aux équipes frontend et intégration.

Non applicable pour DiddiSupport : aucun WebSocket public n'est livré. Le
frontend doit relire les dossiers et messages depuis la façade publique
DiddiComms après reconnexion.
