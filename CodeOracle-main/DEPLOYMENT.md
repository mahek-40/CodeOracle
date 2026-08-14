# 🚀 CodeOracle — Production Deployment Guide

Comprehensive instructions for deploying **CodeOracle** across Render, Vercel, Netlify, Railway, Google Cloud Run, AWS ECS, and Docker.

---

## 📋 Prerequisites

1. A [Google AI Studio](https://aistudio.google.com/) account with an active `GEMINI_API_KEY`.
2. A GitHub account with the CodeOracle repository pushed.
3. An account on your target cloud provider (Render, Vercel, Netlify, Railway, or AWS/GCP).

---

## 🎯 Deployment Strategies

CodeOracle supports two battle-tested deployment architectures:

| Strategy | Ideal For | Components | Setup Effort |
| :--- | :--- | :--- | :--- |
| **Strategy A: Render Blueprint (Split)** | Production scaling, independent CDN caching | Docker Web Service (Backend) + Static Site CDN (Frontend) | ⭐ One-Click (`render.yaml`) |
| **Strategy B: All-in-One Container** | Single instance, cost optimization, Railway/Cloud Run | 1 Multi-stage Docker Container serving API + React SPA | ⭐ Single Web Service |
| **Strategy C: Vercel/Netlify + Backend** | Maximum edge frontend performance | Vercel/Netlify (Frontend) + Render/Railway (Backend) | ⭐⭐ Simple Split |
| **Strategy D: Docker Compose** | On-premise, VPS (Hetzner/DigitalOcean/EC2), staging | Multi-stage Docker image with healthcheck | ⭐ Single command |

---

## 🔷 Strategy A: Render Blueprint (One-Click Split Deployment)

The included [`render.yaml`](./render.yaml) automatically orchestrates both the backend API and the static frontend CDN on Render.

1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click **"New +"** → Select **"Blueprint"**.
3. Connect your GitHub repository.
4. Render will detect `render.yaml` and configure:
   - **`codeoracle-backend`** (Web Service, Docker)
   - **`codeoracle-frontend`** (Static Site)
5. Set Environment Variables:
   - In `codeoracle-backend`:
     - `GEMINI_API_KEY`: `AIzaSy...` (Your Google Gemini API Key)
     - `ALLOWED_ORIGINS`: `*` (or your frontend domain once assigned)
   - In `codeoracle-frontend`:
     - `VITE_API_BASE_URL`: `https://codeoracle-backend.onrender.com` (Set to your live backend domain)
6. Click **"Apply"**.

---

## 🔷 Strategy B: Single Container Deployment (All-in-One)

The multi-stage [`Dockerfile`](./Dockerfile) bundles the React SPA and FastAPI backend into a single container. FastAPI automatically serves the static frontend at root `/` while routing all API endpoints at `/api/*`.

### Deploying to Render (Single Service):
1. In Render Dashboard, click **"New +"** → **"Web Service"**.
2. Select **"Docker"** runtime with `Dockerfile` at root.
3. Configure Environment Variables:
   - `GEMINI_API_KEY`: Your key
   - `ENV`: `production`
   - `PORT`: `8000` (Render manages this dynamically)
4. Health check path: `/api/health`.

### Deploying to Google Cloud Run:
```bash
gcloud run deploy codeoracle \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=your_key,ENV=production"
```

### Deploying to Railway:
1. Click **"New Project"** → **"Deploy from GitHub repo"**.
2. Railway will detect `Dockerfile` automatically.
3. Add `GEMINI_API_KEY` to the Variables tab.

---

## 🔷 Strategy C: Vercel / Netlify (Frontend) + Render (Backend)

### 1. Backend on Render:
Deploy the backend Docker service as described in Strategy A or B. Note your backend URL (e.g. `https://codeoracle-backend.onrender.com`).

### 2. Frontend on Vercel:
1. Import repository in [Vercel](https://vercel.com).
2. Set Root Directory to `frontend` (or leave at root using the included `vercel.json`).
3. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://codeoracle-backend.onrender.com`
4. Deploy.

### 3. Frontend on Netlify:
1. Import repository in [Netlify](https://netlify.com).
2. Netlify will auto-detect [`netlify.toml`](./netlify.toml).
3. Add Environment Variable:
   - `VITE_API_BASE_URL`: `https://codeoracle-backend.onrender.com`
4. Deploy.

---

## 🔷 Strategy D: Docker Compose (Local & Self-Hosted VPS)

Run the full production stack locally or on any cloud VPS:

1. Create a `.env` file from the template:
   ```bash
   cp .env.example .env
   ```
2. Insert your `GEMINI_API_KEY` in `.env`.
3. Launch the container:
   ```bash
   docker compose up --build -d
   ```
4. Access the application at `http://localhost:8000`.

---

## 🔐 Environment Variables Reference

| Variable | Target Service | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | Backend | **Yes** | Google Gemini API Key for AI code explanation, test gen, refactoring | `AIzaSy...` |
| `PORT` | Backend | No | HTTP server port (Render/Cloud Run dynamically injects this) | `8000` |
| `ENV` | Backend | No | Runtime mode (`production`, `development`, `test`) | `production` |
| `ALLOWED_ORIGINS` | Backend | No | Comma-separated CORS allowed origins or `*` | `*` |
| `CODEORACLE_TEMP_DIR` | Backend | No | Custom path for temporary workspace processing | `/tmp/jobs` |
| `VITE_API_BASE_URL` | Frontend | Split only | Public URL of backend API (leave empty for single-container) | `https://codeoracle-backend.onrender.com` |

---

## 🔍 Post-Deployment Verification Checklist

1. **Verify Backend Health & AI Key Status**:
   ```bash
   curl https://<backend-domain>/api/health
   ```
   **Expected Response:**
   ```json
   {
     "status": "ok",
     "app": "CodeOracle",
     "version": "0.1.0",
     "environment": "production",
     "gemini_configured": true,
     "timestamp": "2026-08-14T...",
     "phase": 0
   }
   ```
2. **Access Web Interface**:
   - Open your frontend domain in the browser.
   - Look at the footer status badge: `Backend connected (v0.1.0 · Gemini AI Ready) · FastAPI /api/health`.
3. **Ingest & Analyze**:
   - Click **"Load Preset →"** for Python Order Processing Suite or JavaScript Cart Manager.
   - Verify that file tree, AST symbols, and interactive dependency graph render.
4. **Hierarchical AI Explanations**:
   - Open the **Explanation** tab and verify system summary, module breakdown, and symbol explanations.
5. **Test Generation & Docker/Subprocess Sandbox**:
   - Open **Generated Tests & Coverage** and click **Run in Sandbox**.
   - Verify test execution output, passed/failed metrics, and coverage breakdown.
6. **Modernization & Breaking Change Warnings**:
   - Open **Refactored Code & Warnings** tab.
   - Verify unified split diffs, AST breaking change detection, and Risk Score gauge.
7. **Report Exports**:
   - Download Markdown Architecture Dossier, JSON AST Payload, and Unified Patch file via **Export Reports**.
