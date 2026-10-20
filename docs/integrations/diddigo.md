# Intégration DiddiGo — contexte de course

**Statut : `implemented` pour le connecteur contractuel ; `blocked` pour
l’activation réseau tant que l’URL et l’identité DiddiGo ne sont pas injectées.**

DiddiGo reste la source de vérité des courses. DiddiSupport ne lit jamais la
base DiddiGo et ne copie pas la course dans sa base.

## Contrat attendu

```text
GET {DIDDIGO_BASE_URL}/internal/v1/support/ride/{ride_id}/context
```

Le contexte doit être limité aux informations nécessaires au support :

- statut courant de la course ;
- participants utiles, sous forme d’identifiants ou de champs déjà autorisés ;
- montant et devise si le traitement du dossier le justifie ;
- chronologie limitée des événements utiles ;
- `as_of` et `redacted_fields`.

Les téléphones, coordonnées précises et données non nécessaires doivent être
masqués par DiddiGo. DiddiSupport conserve `fetched_at` et audite chaque
consultation réussie.

## Activation

```text
CONTEXT_CONNECTORS_JSON={
  "diddigo": {
    "base_url": "http://diddigo:8040",
    "scope": "diddigo:support-context:read"
  }
}
```

L’activation exige aussi l’identité sortante configurée par
`CONTEXT_AUTH_TOKEN` et `CONTEXT_CLIENT_ID`. Ces valeurs sont injectées par
l’environnement de déploiement ; elles ne sont jamais placées dans le code.
