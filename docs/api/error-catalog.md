# Catalogue d'erreurs DiddiSupport

| Code | Sens |
|---|---|
| `SERVICE_TOKEN_REQUIRED` | Token service absent ou incorrect |
| `SERVICE_SCOPE_FORBIDDEN` | Scope insuffisant |
| `RESOURCE_NOT_FOUND` | Ressource métier absente ou invisible |
| `SUPPORT_ACCESS_DENIED` | Accès au dossier refusé |
| `IDEMPOTENCY_CONFLICT` | Clé réutilisée avec un contenu différent |
| `INVALID_STATE_TRANSITION` | Transition interdite |
| `DEPENDENCY_UNAVAILABLE` | Dépendance indisponible |
| `ATTACHMENT_NOT_AUTHORIZED` | Pièce non autorisée |
| `ACTION_RESULT_UNKNOWN` | Résultat distant non confirmé |
| `SOS_ALREADY_ACKNOWLEDGED` | SOS déjà pris en charge |
| `IDEMPOTENCY_KEY_REQUIRED` | Clé d'idempotence absente |
| `SERVICE_ORIGIN_FORBIDDEN` | Le service n'est pas propriétaire de l'origine annoncée |
| `CONTEXT_NOT_FOUND` | Le contexte ou la ressource métier n'existe pas ou n'est pas visible |
| `CONTEXT_PROVIDER_NOT_CONFIGURED` | Aucun connecteur n'est configuré pour le service propriétaire |
| `CONTEXT_PROVIDER_UNAVAILABLE` | Le service propriétaire est indisponible ou a expiré |
| `CONTEXT_PROVIDER_INVALID_RESPONSE` | La réponse du propriétaire ne respecte pas `diddi.context.v1` |
| `CONTEXT_RESOURCE_MISMATCH` | La réponse ne correspond pas à la ressource demandée |
| `CONTEXT_AUTHENTICATION_FAILED` | Le token service DiddiFreeID n'a pas pu être obtenu |
