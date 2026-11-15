import os,json,hashlib,sqlite3,re,requests
from openai import OpenAI
from docx import Document
from app.config import *

def profile():
    return json.load(open(os.path.join(DATA,"profile.json"),encoding="utf8"))

def db():
    os.makedirs(DATA,exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    c.execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,source TEXT,company TEXT,title TEXT,location TEXT,url TEXT,description TEXT,score INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY,job_id TEXT,status TEXT,notes TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP)")
    return c

def ai(prompt,system="You are a truthful job-search assistant. Never invent candidate facts."):
    if not OPENAI_API_KEY: raise ValueError("Set OPENAI_API_KEY in .env and restart.")
    r=OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(model=OPENAI_MODEL,temperature=.25,messages=[{"role":"system","content":system},{"role":"user","content":trompt}])
    return r.choices[0].message.content or ""

def discover():
    cfg=json.load(open(os.path.join(DATA,"company_boards.json"),encoding="utf8")); found=[]
    for x in cfg.get("greenhouse",[]):
        token=x.get("board_token","")
        if not token or token.startswith("REPLACE_"): continue
        try:
            data=requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",timeout=20).json()
            for j in data.get("jobs",[]):
                url=j.get("absolute_url",""); title=j.get("title",""); co=x["company"]
                found.append({"id":hashlib.sha1((co+title+url).encode()).hexdigest()[:16],"source":"Greenhouse","company":co,"title":title,"location":(j.get("location") or {}).get("name",""),"url":url,"description":j.get("content","")})
        except Exception as e: print("Greenhouse error:",e)
    for x in cfg.get("lever",[]):
        site=x.get("site","")
        if not site or site.startswith("REPLACE_"): continue
        try:
            data=requests.get(f"https://api.lever.co/v0/postings/{site}?mode=json",timeout=20).json()
            for j in data:
                url=j.get("hostedUrl",""); title=j.get("text",""); co=x["company"]; cat=j.get("categories") or {}
                found.append({"id":hashlib.sha1((co+title+url).encode()).hexdigest()[:16],"source":"Lever","company":co,"title":title,"location":cat.get("location",""),"url":url,"description":j.get("descriptionPlain","")+" "+j.get("additionalPlain","")})
        except Exception as e: print("Lever error:",e)
    p=profile(); terms=set(re.findall(r"[a-z0-9+#.]+",(" ".join(p.get("skills",[])+p.get("preferences",{}).get("roles",[]))).lower()))
    c=db()
    for j in found:
        text=(j["title"]+" "+j["description"]).lower()
        j["score"]=min(100,round(100*sum(t in text for t in terms)/max(1,len(terms))))
        c.execute("INSERT OR REPLACE INTO jobs VALUES(?,?,?,?,?,?,?,?)",(j["id"],j["source"],j["company"],j["title"],j["location"],j["url"],j["description"],j["score"]))
    c.commit();c.close()
    return found

def list_jobs(query="",location=""):
    c=db(); rows=[dict(x) for x in c.execute("SELECT * FROM jobs ORDER BY score DESC")];c.close()
    return [x for x in rows if query.lower() in (x["title"]+" "+x["description"]+" "+x["company"]).lower() and location.lower() in (x["location"]+" "+x["company"]).lower()]

def get_job(i):
    c=db();r=c.execute("SELECT * FROM jobs WHERE id=?",(i,)).fetchone();c.close()
    return dict(r) if r else None

def save_doc(text,name):
    os.makedirs(OUT,exist_ok=True); path=os.path.join(OUT,name); d=Document()
    for line in text.splitlines():
        s=line.strip()
        if not s: continue
        if s.startswith("# "):d.add_heading(s[2:],0)
        elif s.startswith("## "):d.add_heading(s[3:],1)
        elif s.startswith("- "):d.add_paragraph(s[2:],style="List Bullet")
        else:d.add_paragraph(s.replace("**",""))
    d.save(path);return path
