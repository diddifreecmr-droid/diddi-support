# DiddiSupport

Fondation du module Support partagé de l'écosystème DiddiFree.

Le service démarre avec une fondation FastAPI indépendante et reste hébergé
dans DiddiComms pour le premier MVP. Les contrats intermodules sont décrits
dans `DIDDI_MODULE_PROTOCOL_V1.md` et `manifests/diddi-support.v1.json`.

## Développement local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn diddi_support.main:app --reload --port 8050
```

Endpoints initiaux :

- `GET /health/live`
- `GET /health/ready`
- `GET /support/v1/ping`

## Validation

```powershell
python -m pytest
ruff check .
docker compose config
docker build -t diddi-support:local .
```

