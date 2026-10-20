# Intégration DiddiFiles

## Responsabilité

DiddiSupport ne stocke pas les octets des fichiers. Il conserve uniquement la
référence `file_id`, le propriétaire, l'usage, le type MIME et la taille.

## Contrat

Le service appelle `POST /internal/v1/files/{file_id}/temporary-access` avec
`purpose` et le `X-Request-ID` entrant. DiddiFiles retourne une URL temporaire
et sa date d'expiration.

Les URLs publiques sont interdites. Une réponse contenant `public_url` est
rejetée. Un fichier absent donne `404`; une intégration non configurée ou
indisponible donne `503`.

## Configuration

Les variables sont injectées au déploiement : `DIDDIFILES_BASE_URL`,
`DIDDIFILES_AUTH_TOKEN`, `DIDDIFILES_CLIENT_ID` et `ATTACHMENT_MAX_BYTES`.

Une référence peut être enregistrée sans activation réseau de DiddiFiles.
L'accès temporaire reste indisponible tant que l'URL de base n'est pas
configurée.
