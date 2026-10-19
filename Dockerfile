FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY manifests ./manifests
COPY docs ./docs
COPY DIDDI_MODULE_PROTOCOL_V1.md SPRINT_PLAN_DIDDI_SUPPORT_MVP.md ./

RUN pip install --no-cache-dir .

EXPOSE 8050

CMD ["uvicorn", "diddi_support.main:app", "--host", "0.0.0.0", "--port", "8050"]

