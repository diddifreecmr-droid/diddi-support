# Suivi d'implémentation — DiddiSupport

Branche : `codex/diddi-support-2026-11-28`
Plan : `IMPLEMENTATION_PLAN_2026-11-28_CORRELATION_BACKOFFICE_AUTH.md`

## Phases

- [x] P0 — Figer l'identité et établir la baseline
  - [x] P0-A — Créer le suivi et établir les commandes de vérification
  - [x] P0-B — Vérifier la baseline et les contrats existants
- [ ] P1 — Corrélation `X-Request-ID`
  - [x] P1-A — Implémenter la corrélation globale des réponses
  - [x] P1-B — Tester les réponses normales et d'erreur
- [ ] P2 — Authentification Backoffice par token de service
  - [ ] P2-A — Introduire l'authentification duale
  - [ ] P2-B — Propager l'acteur, la raison et l'audit
  - [ ] P2-C — Tester les scopes et la compatibilité JWT utilisateur
- [ ] P3 — Contrats, OpenAPI et tests d'intégration
  - [ ] P3-A — Mettre à jour les contrats et l'OpenAPI
  - [ ] P3-B — Compléter les tests de contrat et de non-régression
- [ ] P4 — Vérification staging et livraison contrôlée
  - [ ] P4-A — Préparer la vérification de livraison
  - [ ] P4-B — Vérifier staging/Portainer lorsque l'exécution sera autorisée

## Vérifications de déploiement en attente

- [ ] Vérifier le parcours réel DiddiAdmin BFF → DiddiSupport avec un token de service FreeID.
- [ ] Vérifier la conservation de `X-Request-ID` par l'application et le proxy.
- [ ] Vérifier API/worker/migration dans Portainer sans modifier de secret.

## Idées hors plan

- Aucune.
