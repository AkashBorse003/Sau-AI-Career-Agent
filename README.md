# Sau AI Career Agent — MVP

## Included
- Public Greenhouse and Lever company career-board search.
- Basic job matching against your editable profile.
- OpenAI-powered tailored resume drafts (DOCX), interview prep, study plan and HR email drafts.
- Local SQLite application tracker and FastAPI API dashboard.

## Safe automation
This MVP does not scrape LinkedIn/Naukri/Indeed, bypass logins/CAPTCHAs, submit applications, or send emails/messages. It prepares materials and official links for your review. Use official APIs, saved job alerts and platform-authorized integrations. AI-generated content must be checked before use.

## Install on Windows
Open PowerShell inside the extracted folder:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```
Add your API key: `OPENAI_API_KEY=your_key_here`. Keep `.env` private.
Run:
```powershell
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

If activation is blocked, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

## Configure
1. Edit `data/profile.json`; verify all education dates, experience, skills, projects and certificates.
2. Edit `data/company_boards.json`. Replace placeholder Greenhouse board tokens and Lever site names with real identifiers for companies you want to monitor.
3. The `gpt-6` model name in `.env` must be available to your API account. If not, set an API-supported model ID. ChatGPT subscriptions and API billing are separate.

## Test
- GET `/api/health` should return `{"status":"ok"}`.
- GET `/api/profile` should show your profile.
- Add at least one valid Greenhouse or Lever board identifier.
- POST `/api/jobs/refresh` with `{"query":"application support","location":"India"}`.
- GET `/api/jobs` to view stored jobs.
- For a returned job ID, POST to `/api/jobs/{id}/tailor`, `/prep`, and `/application-pack  with {"job_id":"same-id"}`.
- Generated files are saved under `generated/`.
- Track reviewed applications with POST `/api/applications`.

LinkedIn and Naukri can be integrated later through permitted APIs, job alert email ingestion, or user-provided job links/descriptions—not unauthorized scraping or bot activity.
