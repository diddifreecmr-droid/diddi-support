# Décisions d'implémentation — DiddiSupport

Les décisions déjà figées par le plan sont recopiées ci-dessous. Une décision
nouvelle ne modifie jamais silencieusement une décision existante.

### D-01 — Façade utilisateur
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : DiddiComms reste la façade utilisateur ; DiddiSupport reste interne.
- Pourquoi : DiddiComms reçoit et transporte les messages client ; Support gère les dossiers.
- Alternatives écartées : exposer DiddiSupport au navigateur.
- Source : Plan
- Impact : contrats DiddiComms, routes Support, sécurité.

### D-02 — Authentification BFF
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : le BFF DiddiAdmin utilise un token de service et transmet l'acteur délégué.
- Pourquoi : le navigateur ne doit pas recevoir de secret S2S.
- Alternatives écartées : appeler Support directement depuis le navigateur.
- Source : Plan
- Impact : authentification, headers Backoffice, audit.

### D-03 — Scopes
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : conserver les scopes `diddi-support:*` déjà utilisés par les routes Backoffice.
- Pourquoi : les permissions de route existent déjà.
- Alternatives écartées : créer une nouvelle matrice de permissions.
- Source : Plan
- Impact : route interne et tests d'autorisation.

### D-04 — Compatibilité JWT utilisateur
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : conserver temporairement l'acceptation du JWT utilisateur Backoffice.
- Pourquoi : la migration DiddiAdmin ne doit pas casser le contrat existant.
- Alternatives écartées : supprimer immédiatement le mode utilisateur.
- Source : Plan
- Impact : dépendance d'authentification duale et non-régression.

### D-05 — Réponse `X-Request-ID`
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : chaque réponse Support retourne l'identifiant entrant ou un identifiant généré.
- Pourquoi : le ticket exige une corrélation observable des réponses.
- Alternatives écartées : ne tracer que les appels sortants.
- Source : Plan
- Impact : middleware, erreurs, santé, tests, proxy.

### D-06 — Contrats HTTP
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : conserver les contrats HTTP existants et documenter les nouveaux headers/erreurs.
- Pourquoi : limiter le changement aux deux tickets.
- Alternatives écartées : créer de nouvelles routes métier.
- Source : Plan
- Impact : OpenAPI, catalogue d'erreurs, documentation.

### D-07 — Identité FreeID
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : utiliser `service:diddiadmin`.
- Pourquoi : identité recommandée et déjà documentée.
- Alternatives écartées : `service:backoffice` ou double identité.
- Source : Utilisateur
- Impact : vérification du token, tests et configuration.

### D-08 — Allowlist `X-Client-ID`
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : l'allowlist est globale.
- Pourquoi : le contrat utilisateur l'a explicitement fixé ainsi.
- Alternatives écartées : allowlist distincte par environnement.
- Source : Utilisateur
- Impact : validation du header client et configuration.

### D-09 — Raison Backoffice
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : `X-Backoffice-Reason` est facultatif mais enregistré lorsqu'il existe.
- Pourquoi : conserver l'audit sans bloquer les appels qui n'ont pas de raison.
- Alternatives écartées : rendre la raison obligatoire.
- Source : Utilisateur
- Impact : dépendance d'authentification, audit, tests.

### D-10 — Format de corrélation
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : générer les `X-Request-ID` absents en UUID v4.
- Pourquoi : format standard, générable localement et vérifiable.
- Alternatives écartées : identifiant opaque non spécifié.
- Source : Utilisateur
- Impact : middleware, tests et documentation.

### D-11 — Préservation de corrélation
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : l'application ajoute/préserve le header et le proxy le préserve de bout en bout.
- Pourquoi : la garantie doit couvrir le trajet réel.
- Alternatives écartées : responsabilité limitée à l'application.
- Source : Utilisateur
- Impact : application, reverse proxy, vérification staging.

### D-12 — Ajout du token service
- Date : 2026-11-28
- Phase / sous-lot : Plan
- Décision : ajouter l'acceptation du token service en conservant le JWT utilisateur.
- Pourquoi : la documentation prévoit le token service mais le code actuel ne l'accepte pas.
- Alternatives écartées : remplacer immédiatement le JWT utilisateur.
- Source : Utilisateur
- Impact : auth, routes Backoffice, tests et documentation.
