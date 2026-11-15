# AgriNext Complete Production Deployment Guide

This guide walks you through deploying **AgriNext** from `AgriNext_StarShift1` to production.

---

## Architecture Overview

AgriNext consists of two components:
1. **Backend**: Python FastAPI service serving NASA Earth observations, spatial algorithms, and climate simulations.
2. **Frontend**: React 19 + Vite + Tailwind CSS Single-Page Application (SPA).

---

## Recommended Free/Starter Deployment (Render + Vercel)

This is the standard, battle-tested setup:
- **Backend on Render** (Free Web Service)
- **Frontend on Vercel** (Free Global Edge CDN)

---

### Step 1: Push Project to GitHub

1. If you haven't already, initialize a Git repository and push your project to your GitHub account:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for AgriNext"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/agrinext.git
   git push -u origin main
   ```

---

### Step 2: Deploy Backend to Render

1. Log in to **[Render.com](https://render.com/)** using your GitHub account.
2. Click **New +** → **Web Service**.
3. Select your GitHub repository (`agrinext`).
4. Configure the Web Service settings:
   - **Name:** `agrinext-backend`
   - **Root Directory:** `backend` (or `AgriNext_Baseline_Corrected/backend` depending on repository root)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
5. Scroll down to **Environment Variables** and add:
   | Key | Value | Notes |
   |---|---|---|
   | `AGRINEXT_ENV` | `production` | Enables production mode |
   | `AGRINEXT_COOKIE_SECURE` | `true` | Required for HTTPS cookie transmission |
   | `AGRINEXT_COOKIE_SAMESITE` | `none` | Allows cross-site session cookies between Vercel and Render |
   | `AGRINEXT_ALLOWED_ORIGINS` | `http://localhost:5173` | *Temporarily set to localhost, update in Step 4 with Vercel URL* |
   | `EARTHDATA_USERNAME` | *(Optional)* | Your NASA Earthdata login |
   | `EARTHDATA_PASSWORD` | *(Optional)* | Your NASA Earthdata password |
6. Click **Deploy Web Service**.
7. Once deployment finishes (usually 2–3 minutes), copy your Render backend URL:
   > Example: `https://agrinext-backend.onrender.com`  
   > Verify it by opening `https://agrinext-backend.onrender.com/docs` to see the live Swagger docs.

---

### Step 3: Deploy Frontend to Vercel

1. Log in to **[Vercel.com](https://vercel.com/)** using your GitHub account.
2. Click **Add New...** → **Project**.
3. Import your GitHub repository (`agrinext`).
4. In the project setup screen:
   - **Framework Preset:** Vite
   - **Root Directory:** Click *Edit* and select `frontend` (or `AgriNext_Baseline_Corrected/frontend`).
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Expand the **Environment Variables** section and add:
   | Key | Value |
   |---|---|
   | `VITE_API_URL` | Your Render Backend URL from Step 2 (e.g., `https://agrinext-backend.onrender.com`) |
6. Click **Deploy**.
7. Vercel will build and assign you a live HTTPS domain:
   > Example: `https://agrinext.vercel.app`

---

### Step 4: Final Handshake (Update CORS on Render)

1. Return to your **Render Dashboard** → click your `agrinext-backend` service → go to **Environment**.
2. Update `AGRINEXT_ALLOWED_ORIGINS` to include your new Vercel URL:
   ```
   https://agrinext.vercel.app,http://localhost:5173
   ```
3. Save changes. Render will perform a quick zero-downtime redeploy.
4. **Done!** Open your Vercel URL in your browser: full authentication, satellite map, 4-tier AP locations, NASA baseline evidence, and climate simulation are now fully live in production.

---

## Alternative: All-in-One Deployment on Railway

If you prefer keeping frontend and backend together on one dashboard:

1. Create an account on **[Railway.app](https://railway.app/)**.
2. Click **New Project** → **Deploy from GitHub repo**.
3. Add service 1 (Backend):
   - Set Root Directory to `backend`
   - Railway auto-detects `requirements.txt`
   - Set environment variables: `PORT=8000`, `AGRINEXT_ENV=production`, `AGRINEXT_COOKIE_SECURE=true`, `AGRINEXT_COOKIE_SAMESITE=none`
4. Add service 2 (Frontend):
   - Set Root Directory to `frontend`
   - Set `VITE_API_URL` to your Railway backend service domain.

---

## Docker Deployment (Cloud Run / VPS / Fly.io)

A ready-to-use Dockerfile is located at `backend/Dockerfile`:
```bash
# Build backend image
docker build -t agrinext-backend -f backend/Dockerfile backend/

# Run container
docker run -p 8000:8000 -e AGRINEXT_ENV=production agrinext-backend
```
