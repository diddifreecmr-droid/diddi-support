# DiddiSupport — Plan d'implémentation MVP

**Statut :** plan de réalisation proposé  
**Protocole de référence :** `DIDDI_MODULE_PROTOCOL_V1.md`  
**Manifest :** `manifests/diddi-support.v1.json`  
**Hébergement initial :** module Support dans DiddiComms

## Règle d'exécution de chaque sprint

Un sprint n'est considéré comme terminé qu'après :

1. implémentation ;
2. tests unitaires, intégration et contrat concernés ;
3. compilation ou vérification statique ;
4. construction et démarrage Docker ;
5. correction des erreurs découvertes ;
6. mise à jour de la documentation dans `docs/` ;
7. validation finale propre ;
8. commit Git après validation uniquement.

Un commit ne doit jamais servir à conserver un état connu comme cassé. Le
journal de sprint doit indiquer les commandes exécutées, leur résultat et les
éventuels tests non applicables.

## Politique de configuration

Les valeurs d'exécution et d'infrastructure sont injectées par variables
d'environnement, avec validation au démarrage. Cela inclut les URLs, tokens,
audiences, bases, Redis, stockage, timeouts, retries, concurrence et
observabilité.

Les règles métier et de sécurité restent versionnées et nécessitent un
redeploiement : transitions de dossiers, états SOS, permissions, scopes,
catégories sensibles, actions financières, codes d'erreur et règles de
confidentialité. Elles ne sont pas pilotées par des variables faciles à
modifier.

Pour chaque nouvelle valeur, la question obligatoire est :

```text
Cette valeur change-t-elle seulement le fonctionnement technique,
ou peut-elle changer une décision métier, un droit ou un résultat financier ?
```

Dans le premier cas : variable d'environnement validée au démarrage. Dans le
second cas : contrat versionné, tests, documentation et redeploiement.

## Objectif du MVP

Permettre à un passager ou un chauffeur de signaler un problème lié à une
course DiddiGo, d'échanger avec le support, de joindre une preuve, de suivre
le traitement et de déclencher un parcours SOS prioritaire. Les informations
de course restent lues auprès de DiddiGo ; elles ne sont pas copiées comme
source de vérité dans Support.

## Sprint 0 — Gel du protocole

Objectif : rendre les règles d'intégration stables avant d'écrire les
connecteurs.

Livrables :

- valider `DIDDI_MODULE_PROTOCOL_V1.md` ;
- valider le manifest JSON ;
- confirmer audiences, scopes et clients DiddiFree ID ;
- figer l'enveloppe d'erreur, les headers et l'idempotence ;
- figer les états du dossier, du SOS et des actions ;
- ajouter des tests de validation du manifest.

Critères de sortie : tous les modules peuvent lire le même contrat sans
interprétation différente.

## Sprint 1 — Fondation Support

Objectif : créer le domaine Support dans DiddiComms sans dupliquer le moteur de
conversation existant.

Livrables :

- entités `SupportCase`, `SupportAssignment`, `SupportAction` ;
- statuts `open`, `in_progress`, `waiting_user`, `waiting_internal`,
  `resolved`, `closed` ;
- visibilité `user_visible`, `internal_note`, `system_event` ;
- migrations PostgreSQL et contraintes d'unicité ;
- audit append-only ;
- outbox et déduplication des transmissions ;
- erreurs conformes au protocole.

Critères de sortie : création, lecture et transition d'un dossier sont
testables sans dépendre d'une interface graphique.

## Sprint 2 — Création depuis DiddiGo

Objectif : permettre à DiddiGo de transmettre un signalement de manière fiable.

Livrables :

- endpoint interne de création de dossier ;
- validation du token `service:diddigo` ;
- scope `diddi-support:cases:create` ;
- `origin_service`, `resource_type`, `resource_id`, `origin_report_id` ;
- clé `Idempotency-Key` obligatoire ;
- création atomique dossier + conversation + audit + outbox ;
- reprise après timeout et rejet des conflits d'idempotence.

Critères de sortie : un passager ou chauffeur autorisé peut déposer un
signalement, et deux transmissions identiques ne créent qu'un seul dossier.

## Sprint 3 — Contexte métier réel DiddiGo

Objectif : permettre à l'agent de voir les informations utiles de la course.

Livrables :

- contrat `GET /internal/v1/support/{resource_type}/{resource_id}/context` ;
- adaptateur DiddiGo ;
- lecture du statut, des participants utiles et de la chronologie limitée ;
- gestion des erreurs et indisponibilités DiddiGo ;
- cache court uniquement pour continuité contrôlée ;
- audit de chaque consultation sensible ;
- aucun accès direct à la base DiddiGo.

Critères de sortie : l'agent voit l'état réel de la course et la date de
fraîcheur du contexte, sans recevoir de données inutiles ou interdites.

## Sprint 4 — Messages, pièces jointes et preuves

Objectif : compléter un dossier avec texte, photo ou vocal.

Livrables :

- séparation stricte messages utilisateur / notes internes ;
- intégration DiddiFiles par `file_id` ;
- usages privés `diddisupport_case_photo`, `diddisupport_case_voice` et
  `diddisupport_case_document` ;
- contrôle propriétaire, MIME, taille et disponibilité ;
- URLs temporaires après autorisation Support ;
- transcription vocale facultative et explicitement marquée comme dérivée ;
- tests d'absence d'URL publique et de fuite de fichiers.

Critères de sortie : une preuve est consultable uniquement par l'auteur et les
agents habilités.

## Sprint 5 — Parcours SOS

Objectif : traiter les urgences dans une file et un état distincts.

Livrables :

- `SosAlert` lié ou non à un dossier ;
- états notification : enregistrée, en attente, envoyée, échouée ;
- états prise en charge : non confirmée, confirmée, en cours, terminée ;
- file SOS prioritaire ;
- confirmation humaine explicite ;
- retries et escalade configurables ;
- raccordement au SOS existant de DiddiGo sans double notification.

Critères de sortie : le système ne prétend jamais qu'un SOS est pris en charge
avant confirmation d'un agent.

## Sprint 6 — Backoffice Agents

Objectif : permettre aux agents de travailler les dossiers depuis DiddiAdmin.

Livrables :

- file générale ;
- file SOS ;
- détail dossier ;
- affectation et transfert ;
- réponses utilisateur ;
- notes internes ;
- chronologie complète ;
- permissions `read`, `reply`, `assign`, `sos-operate`, `attachments-read`,
  `audit-read` ;
- audit de toutes les actions agents.

Critères de sortie : un agent sans capacité adéquate ne peut ni consulter une
preuve ni intervenir sur un dossier sensible.

## Sprint 7 — Actions métier et paiements

Objectif : enregistrer les décisions sans confondre décision et exécution.

Livrables :

- actions `requested`, `pending`, `succeeded`, `failed`, `unknown` ;
- connecteur DiddiGo pour les actions autorisées ;
- connecteur DiddiPay pour consultation et remboursement autorisé ;
- clé d'opération stable ;
- récupération du résultat après timeout ;
- affichage de l'état réel dans le backoffice ;
- audit de la décision, de la demande et du résultat.

Critères de sortie : Support n'affiche jamais « remboursé » avant confirmation
de DiddiPay.

## Sprint 8 — Connecteurs DiddiFood et DiddiSend

Objectif : rendre le protocole réutilisable au-delà de DiddiGo.

Livrables :

- contexte `diddifood/order` ;
- contexte `diddisend/delivery` ;
- mêmes règles de token, scope, référence et idempotence ;
- tests de contrat indépendants pour chaque module ;
- activation par feature flag ;
- aucun code métier Food ou Send dans le domaine Support.

Critères de sortie : ajouter un nouveau module ne nécessite pas de modifier le
noyau des dossiers et conversations.

## Sprint 9 — IA et reprise humaine

Objectif : ajouter une assistance IA contrôlée.

Livrables :

- mode `ai`, `human_requested`, `human_active` ;
- accusé de réception automatique ;
- catégorisation et questions simples ;
- résumé pour agent ;
- bouton de reprise humaine ;
- arrêt des réponses IA concurrentes après reprise ;
- garde-fous contre sanctions, culpabilité, remboursement ou clôture SOS ;
- fonctionnement du dépôt même si l'IA est indisponible.

Critères de sortie : l'IA ne peut déclencher seule aucune action administrative
ou financière.

## Sprint 10 — Sécurité, observabilité et pilote

Objectif : préparer un lancement contrôlé.

Livrables :

- tests BOLA et séparation des participants ;
- tests tokens utilisateur/service et scopes ;
- tests de doublons, retries et événements redélivrés ;
- tests de fuite de message, téléphone et fichier ;
- métriques : queue, SLA, SOS, outbox, erreurs de connecteurs ;
- dashboards et alertes ;
- politique de conservation ;
- feature flags par module et environnement ;
- scénario staging complet ;
- runbooks d'indisponibilité et de reprise.

Critères de sortie : le parcours suivant passe en staging :

```text
course DiddiGo
→ signalement
→ transmission outbox
→ dossier Support
→ contexte course
→ message/preuve
→ affectation agent
→ action métier
→ résultat confirmé
```

## Ordre recommandé

```text
S0 → S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8 → S9 → S10
```

Les Sprints 4 et 5 peuvent avancer en parallèle après la stabilisation du
dossier. Le connecteur DiddiPay ne doit pas bloquer le dépôt d'une plainte ni
le traitement d'un SOS.

## Definition of Done commune

Chaque sprint doit fournir :

- code ou contrat versionné ;
- tests unitaires et tests de contrat ;
- migration réversible si nécessaire ;
- audit et observabilité ;
- documentation de configuration ;
- comportement défini en cas de timeout ou d'indisponibilité ;
- aucun secret, contenu privé ou numéro de téléphone dans les logs.

- le commit n'est créé qu'après validation complète du sprint.

## Documentation par sprint

Chaque sprint met à jour uniquement les documents concernés, selon cette
structure :

```text
docs/
├── api/
│   ├── openapi.json
│   └── error-catalog.md
├── guides/
│   ├── support-case-flow.md
│   ├── agent-case-flow.md
│   ├── sos-safety.md
│   ├── attachments-and-evidence.md
│   └── actions-and-resolution.md
├── realtime/
│   ├── websocket-contract.md
│   └── reconnection-strategy.md
├── integrations/
│   ├── diddifiles.md
│   ├── diddipay.md
│   ├── diddigo.md
│   ├── diddifood.md
│   ├── diddisend.md
│   └── diddicomms.md
├── reference/
│   ├── statuses.md
│   ├── configuration.md
│   └── permissions.md
└── changelog/
    └── YYYY-MM-DD.md
```

`openapi.json` doit être généré depuis l'application, jamais modifié à la
main. Les documents d'intégration indiquent le statut de chaque contrat :
`implemented`, `proposed`, `blocked` ou `future`.
