# ─── Stage 1: Build React Frontend ───────────────────────────────────────────
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

# Copy package manifests and install dependencies
COPY frontend/package*.json ./
RUN npm ci || npm install

# Copy frontend source code and build production bundle
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Production Python & Node Runtime ───────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Set production environment flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production \
    PORT=8000

# Install system dependencies + Node.js & npm runtime for dual-language test execution sandbox
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend source code
COPY backend /app/backend

# Copy built frontend production artifacts from builder stage
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

WORKDIR /app/backend

EXPOSE 8000

# Health check for orchestrators (Render, Docker, Kubernetes, AWS, GCP)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

# Start FastAPI application using dynamic PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
