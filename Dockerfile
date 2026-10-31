# Built from the repo root by scripts/04-deploy-agent.sh (gcloud run deploy --source .).
# Python 3.12: google-adk 2.13 needs 3.11+.
FROM python:3.12-slim
WORKDIR /srv
COPY agent/requirements.txt agent-requirements.txt
COPY service/requirements.txt service-requirements.txt
RUN pip install --no-cache-dir -r agent-requirements.txt -r service-requirements.txt
COPY agent/sre_agent ./sre_agent
COPY service/*.py ./
USER nobody
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
