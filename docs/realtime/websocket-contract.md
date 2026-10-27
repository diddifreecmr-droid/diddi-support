# Contrat temps réel DiddiSupport

Ce document indique les événements temps réel visibles par un client. Il
s'adresse aux équipes frontend et intégration.

Non applicable pour DiddiSupport : aucun WebSocket public n'est livré. Les
événements Redis `diddisupport.events` sont un transport interservice et ne
doivent pas être consommés par une application frontend.
