# Journal P2-C — Scopes et compatibilité

- Statut : TERMINÉ
- Vérification : un principal délégué `service:diddiadmin` avec
  `diddi-support:read` atteint `GET /support/v1/backoffice/cases` ; les tests
  existants couvrent les permissions insuffisantes et le JWT utilisateur.
- Résultat : 65 tests passent, 1 warning FastAPI/httpx ; lint ciblé passe.
