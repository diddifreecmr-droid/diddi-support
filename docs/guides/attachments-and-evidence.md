# Pièces jointes et preuves

Un agent peut rattacher une preuve à un dossier support. Le fichier doit
appartenir au déclarant du dossier et respecter le type MIME autorisé pour
son usage : photo, audio ou document.

Le module conserve la référence DiddiFiles, jamais une URL publique. Pour
consulter la preuve, le Backoffice demande une autorisation temporaire limitée
dans le temps par DiddiFiles.

Les créations de messages et de références sont transactionnelles avec leur
événement d'audit et leur événement outbox. Les données sensibles ne doivent
pas être copiées dans le corps des événements.
