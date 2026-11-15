import hashlib,json,sqlite3
from openai import OpenAI
from app.config import OPENAI_API_KEY,OPENAI_MODEL,DB,PROFILE_FILE

def profile():
    if not PROFILE_FILE.exists(): return {"full_name":"","email":"","phone":"","location":"","skills":[],"education":[],"experience":[],"preferences":{"roles":[],"locations":[]}}
    return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
def save_profile(data):
    PROFILE_FILE.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8"); return data
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,source TEXT,company TEXT,title TEXT,location TEXT,url TEXT,description TEXT,score INTEGER DEFAULT 0,created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT,company TEXT,title TEXT,status TEXT DEFAULT 'saved',notes TEXT DEFAULT '',applied_at TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS email_events(id INTEGER PRIMARY KEY AUTOINCREMENT,gmail_id TEXT UNIQUE,sender TEXT,subject TEXT,snippet TEXT,category TEXT,draft TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.commit(); return c
def ai(prompt,system="You are a careful career assistant. Never invent candidate facts."):
    if not OPENAI_API_KEY: raise ValueError("OPENAI_API_KEY is missing. Add it to .env and restart.")
    client=OpenAI(api_key=OPENAI_API_KEY)
    r=client.chat.completions.create(model=OPENAI_MODEL,temperature=0.2,messages=[{"role":"system","content":system},{"role":"user","content":prompt}])
    return r.choices[0].message.content or ""
def score_job(job,candidate=None):
    p=candidate or profile(); skills=[str(s).lower() for s in p.get("skills",[]) if str(s).strip()]
    roles=[str(s).lower() for s in p.get("preferences",{}).get("roles",[]) if str(s).strip()]
    locations=[str(s).lower() for s in p.get("preferences",{}).get("locations",[]) if str(s).strip()]
    title=job.get("title","").lower(); text=(title+" "+job.get("description","")).lower()
    skill_score=sum(1 for s in skills if s in text)/max(1,len(skills))
    role_score=1 if any(r in title for r in roles) else 0
    loc=job.get("location","").lower(); location_score=1 if not locations or any(x in loc for x in locations) else 0
    return round(70*skill_score+20*role_score+10*location_score)
def stable_job_id(company,title,url):
    return hashlib.sha1((company+"|"+title+"|"+url).encode()).hexdigest()[:16]
def save_doc(text,path):
    from docx import Document
    d=Document()
    for line in text.splitlines():
        s=line.strip()
        if not s: continue
        if s.startswith("# "): d.add_heading(s[2:],0)
        elif s.startswith("## "): d.add_heading(s[3:],1)
        elif s.startswith("- "): d.add_paragraph(s[2:],style="List Bullet")
        else: d.add_paragraph(s.replace("**",""))
    d.save(str(path)); return str(path)
