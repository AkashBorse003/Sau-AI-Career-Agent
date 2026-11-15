# Sau AI Career Agent

Local-first career assistant using FastAPI, SQLite, React + Vite, Playwright and optional Gmail OAuth.

## Features
- Greenhouse and Lever public job-board discovery.
- SQLite job and application tracker.
- Profile-based job matching.
- AI resume tailoring to DOCX and interview preparation.
- Visible Playwright assisted form filling. It never clicks submit.
- AI recruiter email reply drafting.
- Optional Gmail integration to read unread mail and save replies as Gmail drafts; it never auto-sends.
- React dashboard.

## Requirements
Python 3.10+, Node.js 18+, OpenAI API key for AI features. Gmail requires Google OAuth Desktop credentials.

## Backend (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
Copy-Item .env.example .env
# Edit .env and add OPENAI_API_KEY
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Frontend
Open a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173

## Configure job boards
Edit data/company_boards.json with public Greenhouse board tokens or Lever site identifiers. Example:
```json
{"greenhouse":[{"company":"Example Co","board_token":"example"}],"lever":[{"company":"Example Co","site":"example"}]}
```
Portal support depends on official APIs and each website's terms. This starter does not scrape LinkedIn/Naukri or bypass login, CAPTCHA, bot protection or access controls. Add integrations only where permitted.

## Profile
Edit data/profile.json with accurate verified information before using resume or autofill features.

## Gmail (optional)
1. Enable Gmail API in Google Cloud Console.
2. Create OAuth Client ID of type Desktop app.
3. Save downloaded JSON in project root as credentials.json.
4. Call POST /api/email/unread to authorize. The local OAuth browser will open.
5. Use POST /api/email/draft with a message_id to save an AI reply as a Gmail draft. It is never sent automatically.

## Form autofill
Use the Auto Apply tab with an official application URL. The visible browser fills common fields from your profile. Review every answer and submit manually. No login or CAPTCHA bypass. Resume upload requires a local file path and a normal file input.

Keep .env, credentials.json, Gmail tokens, local database and generated files private. Test each employer form before relying on it.
