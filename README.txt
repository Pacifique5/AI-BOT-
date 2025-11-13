# AI Bot Project

## Overview
- Full-stack chat application using a FastAPI backend and React frontend.
- Backend wraps OpenAI’s Chat Completions API. Frontend provides a chat UI with health indicators and message history.
- Requires a valid OpenAI API key with billing / credits enabled.

## Project Layout
- `backend/` – FastAPI service, virtual environment, `.env` file.
- `frontend/` – Vite + React app.
- `.gitignore` – excludes `.env`, `venv/`, build artifacts.

## Prerequisites
- Python 3.13 (matching the virtual environment).
- Node.js 18+ and npm.
- OpenAI API key with active billing.
- Git (for source control).

## First-Time Setup

### 1. Clone & enter project
```powershell
git clone <repo-url>
cd ai-bot
```

### 2. Backend setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables
- Create `backend/.env` (ignored by git) containing:
```
OPENAI_API_KEY=sk-your-actual-api-key
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.7
REQUEST_TIMEOUT=30
```
- The key must have a paid plan or remaining credits; otherwise OpenAI returns errors.

### 4. Frontend dependencies
```powershell
cd ..\frontend
npm install
```

## Running the Application

### Backend (FastAPI)
```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```
- Health check: `curl http://localhost:8000/health` → expect `{"status":"healthy","api_configured":true}`.
- Logs clarify OpenAI failures (network, quota, etc.).

### Frontend (React)
```powershell
cd frontend
npm run dev
```
- Visit the URL printed in the console (default `http://localhost:5173/`).
- Header badge turns green when `/health` succeeds.
- Messages are posted to `POST http://localhost:8000/chat`.

### Typical Local Workflow
1. Start backend (leave running).
2. Start frontend in another terminal.
3. Interact via browser.
4. Stop servers with `Ctrl+C`.

## Deploy / Production Notes
- Use environment variables instead of `.env` when deploying.
- Restrict CORS origins in `backend/server.py` for production.
- Enforce HTTPS and secrets management on the hosting platform.
- Consider adding rate limiting and per-user auth before public availability.

## Testing the Integration
- Backend up: run `curl http://localhost:8000/health`.
- Frontend up: load page, send a message.
- If response shows `[object Object]`, ensure backend is on latest version (now flattens OpenAI structured outputs).
- OpenAI errors such as `insufficient_quota` indicate billing/credit issues with the key.

## Git Hygiene
- `.env` is excluded by `.gitignore`. If accidentally staged: `git reset HEAD backend/.env`.
- Recommended commit flow:
```powershell
git status
git add <files>
git commit -m "Describe the change"
git push origin <branch>
```

## Troubleshooting
- **`OPENAI_API_KEY not found`**: verify `.env` placement and content, restart server.
- **Backend unreachable from frontend**: ensure backend running on port 8000, check CORS/network.
- **`insufficient_quota` or authentication errors**: check OpenAI billing / key validity.
- **Windows PowerShell command errors**: avoid `&&`; run commands sequentially or use PowerShell pipelines.

## Further Enhancements (Ideas)
- Persist chat history beyond page refresh.
- Authentication / user sessions.
- Model selection UI, temperature slider.
- Streaming responses for faster feedback.
- Automated tests for backend endpoints.


