FROM node:20-slim AS dashboard-build
WORKDIR /app/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci --silent
COPY dashboard/ .
RUN npm run build

FROM python:3.13-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY sdk/ ./sdk/
COPY server/ ./server/
RUN pip install --no-cache-dir ".[server]"

COPY --from=dashboard-build /app/dashboard/dist ./dashboard/dist

ENV CULPA_DB_PATH=/data/culpa.db
ENV CORS_ORIGINS=*
ENV JWT_SECRET=change-me-in-production

EXPOSE 8000
VOLUME /data

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
