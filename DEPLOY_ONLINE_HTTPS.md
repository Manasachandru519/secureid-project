# SecureID — Online deployment (HTTPS)

This version is prepared for deployment as a public website. It uses **Vercel for the React frontend** and **Render for the Flask API**. Both platforms provide HTTPS automatically after deployment. The app does not need to run on your laptop after it is deployed.

## Important before publishing
- This is an academic demonstration, not a production identity-verification service. Do not upload real Aadhaar, passport, or other sensitive identity documents. Use sample data only.
- The demo has no production-grade user/admin authentication. Do not expose real personal information.
- For persistent hosted records, create a MongoDB Atlas database and set `MONGO_URI` in the Render service. Render's local filesystem may be temporary; SQLite data may be lost when the service restarts/redeploys.
- The AI fraud scoring is a demonstration model and should not be used to make real identity or fraud decisions.

## Step 1 — Upload project to GitHub
1. Extract this ZIP on your computer.
2. Create a GitHub repository, for example `secureid-project`.
3. Upload/push all files and folders from this extracted project to the repository (keep `backend`, `frontend`, `contracts`, and `render.yaml`).

## Step 2 — Deploy backend on Render
1. Sign in to Render and choose **New → Blueprint** (or create a **Web Service**).
2. Connect your GitHub repository. If using Blueprint, Render reads the root `render.yaml`.
3. If creating a Web Service manually, use these settings:
   - Root Directory: `backend`
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add environment variable `CORS_ORIGINS` with value `*` for the first demo deployment. Once the Vercel URL is known, replace `*` with that exact frontend origin, e.g. `https://secureid-demo.vercel.app`.
5. Wait for deployment. Copy the Render service URL, e.g. `https://secureid-api.onrender.com`.
6. Test `https://YOUR-RENDER-URL/api/health` in Chrome. It should return JSON with `"ok": true`.

## Step 3 — Deploy frontend on Vercel
1. Sign in to Vercel and choose **Add New → Project**. Import the same GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Framework preset: Vite. Build command: `npm run build`. Output directory: `dist`.
4. Add environment variable:
   - Name: `VITE_API_URL`
   - Value: `https://YOUR-RENDER-URL/api` (replace with your real Render URL).
5. Deploy. Vercel will give you a public HTTPS website URL. Open it in Chrome.

## Step 4 — Connect CORS securely
After Vercel gives you the website URL, return to Render → your API service → Environment. Set `CORS_ORIGINS` to your exact Vercel URL, without a trailing slash, for example `https://secureid-demo.vercel.app`. Save/redeploy.

## Step 5 — Persistent database (recommended)
Create a MongoDB Atlas cluster/database and copy its connection string. In Render → Environment, set `MONGO_URI` to that connection string. Ensure the Atlas network access settings allow connections from your Render service. Do not put database credentials in frontend code or GitHub.

## Local development (optional)
Backend: `cd backend`, create/activate a virtual environment, `pip install -r requirements.txt`, then `python app.py`.
Frontend: `cd frontend`, run `npm install`, then `npm run dev`. The default API address remains `http://127.0.0.1:5000/api` for local development.

## HTTPS note
You cannot get a public HTTPS website merely by changing `http` to `https` in the browser. The app must be deployed to a host with a TLS certificate. Vercel and Render configure HTTPS for their deployed service URLs.
