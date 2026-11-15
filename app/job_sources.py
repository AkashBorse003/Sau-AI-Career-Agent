import json,requests
from app.config import BOARDS_FILE
from app.core import db,score_job,stable_job_id,profile
def discover_jobs():
    cfg=json.loads(BOARDS_FILE.read_text(encoding="utf-8")) if BOARDS_FILE.exists() else {}; found=[]
    for x in cfg.get("greenhouse",[]):
        token=x.get("board_token","")
        if not token or token.startswith("REPLACE_"): continue
        try:
            r=requests.get("https://boards-api.greenhouse.io/v1/boards/"+token+"/jobs?content=true",timeout=20); r.raise_for_status()
            for j in r.json().get("jobs",[]):
                co=x.get("company",token); url=j.get("absolute_url","")
                found.append({"id":stable_job_id(co,j.get("title",""),url),"source":"Greenhouse","company":co,"title":j.get("title",""),"location":(j.get("location") or {}).get("name",""),"url":url,"description":j.get("content","")})
        except requests.RequestException as e: print("Greenhouse error:",e)
    for x in cfg.get("lever",[]):
        site=x.get("site","")
        if not site or site.startswith("REPLACE_"): continue
        try:
            r=requests.get("https://api.lever.co/v0/postings/"+site+"?mode=json",timeout=20); r.raise_for_status()
            for j in r.json():
                co=x.get("company",site); url=j.get("hostedUrl",""); cat=j.get("categories") or {}
                found.append({"id":stable_job_id(co,j.get("text",""),url),"source":"Lever","company":co,"title":j.get("text",""),"location":cat.get("location",""),"url":url,"description":j.get("descriptionPlain","")+" "+j.get("additionalPlain","")})
        except requests.RequestException as e: print("Lever error:",e)
    c=db()
    for j in found:
        j["score"]=score_job(j,profile())
        c.execute("INSERT OR REPLACE INTO jobs(id,source,company,title,location,url,description,score) VALUES(:id,:source,:company,:title,:location,:url,:description,:score)",j)
    c.commit(); c.close(); return found
def list_jobs(query="",location="",source=""):
    c=db(); rows=[dict(x) for x in c.execute("SELECT * FROM jobs ORDER BY score DESC,created DESC")]; c.close()
    q,l,s=query.lower(),location.lower(),source.lower()
    return [x for x in rows if q in (x["title"]+" "+x["description"]+" "+x["company"]).lower() and l in x["location"].lower() and s in x["source"].lower()]
def get_job(job_id):
    c=db(); row=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone(); c.close(); return dict(row) if row else None
