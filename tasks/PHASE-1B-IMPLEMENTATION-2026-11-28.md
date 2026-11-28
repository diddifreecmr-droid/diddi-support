# Journal P1-B — Tests de corrélation

- Statut : TERMINÉ
- Couverture : réponses 200 de santé/ping, ID entrant, génération UUID v4,
  erreurs 401/403/404.
- Vérification : `python -m pytest -q` → 59 passed, 1 warning ; lint ciblé des
  fichiers modifiés → passe.
- Remarque : le lint global conserve les 3 E501 préexistants de P0 dans
  `tests/test_context.py`.
