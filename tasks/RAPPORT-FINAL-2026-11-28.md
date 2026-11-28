# Rapport final — DiddiSupport

- Branche : `codex/diddi-support-2026-11-28`
- Phases terminées : P0, P1, P2, P3 ; P4-A terminé.
- Commits de phase : `45f50f1`, `d94f7a6`, `a7f6141`, `5574418`, `0c4fc4f`,
  `4223c0d`, `458ff88`, `d270c18`.
- P4-B : test staging exécuté ; le correctif de régression est poussé dans
  `b4cfc63`, redéploiement encore nécessaire.
- Décisions « Agent, à valider » : aucune.
- Contrat FreeID staging confirmé par l'utilisateur : client
  `backoffice-staging-diddisupport`, subject `service:diddiadmin`, audience
  `diddi-support`, scopes `read`/`write`, issuer/JWKS et endpoint token connus.
- Contrats encore à valider : parcours réel DiddiAdmin BFF → DiddiSupport et
  préservation du header par le proxy.
- Vérifications en attente : déploiement contrôlé, migration `support-migrate`,
  santé API/worker et test réel du token service.
- Test réel : token DiddiFreeID valide avec les six scopes attendus ; la
  configuration Portainer contient l'allowlist attendue. L'API a ensuite
  renvoyé `500` à cause du reset cross-context du `ContextVar` d'audit.
- Correctif : `b4cfc63`, 67 tests passent. Rejouer le test staging après
  redéploiement et vérifier `X-Request-ID` dans la réponse.
