# Build from the repo root:  gcloud builds submit --tag ... -f service/Dockerfile .
# (scripts/deploy-agent.sh does this for you)
FROM python:3.12-slim
WORKDIR /srv
COPY agent/requirements.txt agent-requirements.txt
COPY service/requirements.txt service-requirements.txt
RUN pip install --no-cache-dir -r agent-requirements.txt -r service-requirements.txt
COPY agent/sre_agent ./sre_agent
COPY service/*.py ./
USER nobody
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT
