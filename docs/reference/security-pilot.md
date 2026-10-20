# Sécurité et pilote

Les identités de service et d'agent sont séparées. Un JWT agent ne peut pas
appeler les endpoints internes de service, et un agent doit avoir la permission
appropriée pour lire un dossier, une preuve, un SOS ou une action.

Les contrôles BOLA vérifient l'appartenance du dossier, du message et de la
pièce jointe avant chaque lecture ou écriture. Les événements outbox sont
idempotents par `event_id` et les actions par `operation_key`.

Le pilote staging suit le parcours : dossier DiddiGo → contexte métier →
message/preuve → affectation → SOS ou action → résultat confirmé. Aucun secret,
contenu privé ou numéro de téléphone ne doit apparaître dans les logs.

Les paramètres de déploiement sont injectés par variables d'environnement ;
les règles métier sensibles nécessitent un redeploiement pour changer.
