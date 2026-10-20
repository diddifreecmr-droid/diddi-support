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

L’activation utilise le flux DiddiFreeID `client_credentials` :

```text
DIDDIFREEID_SERVICE_TOKEN_URL
DIDDISUPPORT_DIDDIGO_SERVICE_CLIENT_ID
DIDDISUPPORT_DIDDIGO_SERVICE_CLIENT_SECRET
DIDDISUPPORT_DIDDIGO_SERVICE_AUDIENCE=diddigo
DIDDISUPPORT_DIDDIGO_SERVICE_SCOPE=diddigo:support-context:read
```

Le secret est injecté par l’environnement de déploiement et n’est jamais
placé dans le code ou dans Git. DiddiSupport met en cache le token jusqu’à
quelques secondes avant son expiration, puis le renouvelle automatiquement.
