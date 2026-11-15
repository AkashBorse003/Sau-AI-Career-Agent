import os
from dotenv import load_dotenv
load_dotenv()
OPENAI_API_KEY=os.getenv('OPENAI_API_KEY','').strip()
OPENAI_MODEL=os.getenv('OPENAI_MODEL','gpt-6').strip()
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(BASE,'data')
OUT=os.path.join(BASE,'generated')
DB=os.path.join(DATA,'sau.db')
