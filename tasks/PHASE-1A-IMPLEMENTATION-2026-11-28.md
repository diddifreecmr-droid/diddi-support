# Journal P1-A — Middleware de corrélation

- Statut : TERMINÉ
- Implémentation : middleware HTTP global dans `src/diddi_support/main.py`.
- Comportement : conserve un `X-Request-ID` non vide, sinon génère un UUID v4,
  réinjecte l'ID dans les headers de requête et le retourne sur la réponse.
- Vérification : `python -m pytest -q tests/test_health.py` passe ; lint ciblé
  du fichier applicatif passe.
