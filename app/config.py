import os
from pathlib import Path
from dotenv import load_dotenv
BASE=Path(__file__).resolve().parent.parent
load_dotenv(BASE/".env")
DATA=BASE/"data"; OUT=BASE/"generated"
DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY","").strip()
OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-4o-mini").strip()
DB=DATA/"sau.db"; PROFILE_FILE=DATA/"profile.json"; BOARDS_FILE=DATA/"company_boards.json"
GMAIL_CREDENTIALS=BASE/"credentials.json"; GMAIL_TOKEN=DATA/"gmail-token.json"
