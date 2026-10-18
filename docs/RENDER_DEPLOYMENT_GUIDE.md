# Echo — Backend Deployment Guide on Render

This guide outlines how to deploy the **Echo (FastAPI + FalkorDB + Gemini)** backend to [Render](https://render.com) using Docker.

---

## 1. Quick Overview

- **Deployment Type**: Render Web Service (Docker Runtime)
- **Base Image**: `python:3.11-slim` (lightweight, non-root user `appuser`)
- **Port**: Dynamically binds to Render's injected `$PORT` (default `8000`)
- **Health Check Path**: `/health` (instant 200 OK without external network delays)
- **Auto-Seeding**: Optional `SEED_ON_STARTUP=true` flag to auto-populate the graph architecture on first boot.

---

## 2. Deployment Options

### Option A: 1-Click Render Blueprint (Recommended)

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repository: `developSarth/ConseQ`.
4. Render will detect [`render.yaml`](../render.yaml) automatically and prompt you to fill in sensitive credentials (`FALKORDB_HOST`, `FALKORDB_PASSWORD`, `GEMINI_API_KEY`).
5. Click **Apply**. Render will build and deploy the container.

---

### Option B: Manual Web Service Setup

1. In the [Render Dashboard](https://dashboard.render.com), click **New +** → **Web Service**.
2. Select **Build and deploy from a Git repository** and pick `developSarth/ConseQ`.
3. Configure the service settings:
   - **Name**: `echo-backend`
   - **Region**: Oregon (or your preferred region closest to FalkorDB)
   - **Branch**: `main`
   - **Root Directory**: `.` (leave blank or enter `.`)
   - **Runtime**: **Docker**
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Context**: `.`
   - **Instance Type**: **Free** (or Starter for production persistence)
4. Under **Advanced**:
   - **Health Check Path**: `/health`
5. Click **Add Environment Variable** to add the required values (see table below).
6. Click **Create Web Service**.

---

## 3. Required Environment Variables

Configure these in the Render Dashboard (**Environment** tab):

| Variable | Recommended Value | Description | Secret? |
| :--- | :--- | :--- | :---: |
| `ENVIRONMENT` | `prod` | Application environment mode | No |
| `LOG_LEVEL` | `INFO` | Logging verbosity | No |
| `CORS_ORIGINS` | `*` (or your frontend URL) | Allowed origins (accepts `*`, comma list, or JSON) | No |
| `FALKORDB_HOST` | *(your cloud host)* | FalkorDB Cloud endpoint hostname | **Yes** |
| `FALKORDB_PORT` | `6379` | FalkorDB Redis port | No |
| `FALKORDB_USERNAME`| `default` | FalkorDB database user | No |
| `FALKORDB_PASSWORD`| *(your password)* | FalkorDB Cloud password | **Yes** |
| `FALKORDB_SSL` | `true` | Required for FalkorDB Cloud | No |
| `FALKORDB_GRAPH` | `echo_software` | Primary architecture graph name | No |
| `GEMINI_API_KEY` | *(your api key)* | Google AI Studio Gemini API key | **Yes** |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name | No |
| `MAX_CONCURRENT_FORKS` | `5` | Maximum active simulation memory forks | No |
| `FORK_TTL_MINUTES` | `30` | Auto-cleanup lifetime for temporary forks | No |
| `SEED_ON_STARTUP` | `true` (on first run) | Runs graph seeder on startup | No |

---

## 4. Seeding the Software Graph on Render

To populate the e-commerce microservices, routes, and fallbacks in FalkorDB:

### Method 1: Using the Environment Flag (Easiest)
Set `SEED_ON_STARTUP=true` in Render's environment variables. The entrypoint script will seed the graph on container startup. Once seeded, you can set it back to `false`.

### Method 2: Via Render Web Shell
1. Go to your Web Service in Render.
2. Click **Shell** in the left navigation.
3. Run:
   ```bash
   python /app/scripts/seed_software.py
   ```

---

## 5. Verifying Deployment

Once Render finishes the build:

1. **Liveness Check**:
   ```bash
   curl https://<your-render-service-url>.onrender.com/health
   ```
   *Expected response*: `{"app":"ECHO — AI-Powered Software Failure Simulator","version":"0.1.0","environment":"prod","uptime_s":...}`

2. **Readiness Check**:
   ```bash
   curl https://<your-render-service-url>.onrender.com/health/ready
   ```
   *Checks FalkorDB connectivity and schema state.*

3. **Connecting Frontend**:
   Update `frontend/js/app.js`:
   ```javascript
   const API_BASE = "https://<your-render-service-url>.onrender.com";
   ```
