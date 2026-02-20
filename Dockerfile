# --- Frontend build ---
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit
COPY frontend/ ./
RUN npm run build

# --- Backend ---
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/
RUN cd frontend && npm ci --no-audit --omit=dev

EXPOSE 8000 3000
VOLUME /app/data

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host ${SENTINEL_HOST:-0.0.0.0} --port ${SENTINEL_PORT:-8000} --workers 1 & cd frontend && npx next start -p ${FRONTEND_PORT:-3000} & wait"]
