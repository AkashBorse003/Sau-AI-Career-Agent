import os,json
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from app.core import *
app=FastAPI(title="Sau AI Career Agent",version="0.1 MVP")
class Search(BaseModel):
    query:str=""
    location:str=""
class JobAction(BaseModel):
    job_id:str
class Track(BaseModel):
    job_id:str
    status:str="prepared"
    notes:str=""
@app.get("/")
def home():
    return {"name":"Sau AI Career Agent","message":"Open /docs to use the dashboard API","quick_start":["POST /api/jobs/refresh","GET /api/jobs","POST /api/jobs/{id}/tailor","POST /api/jobs/{id}/prep","POST /api/jobs/{id}/application-pack"]}
@app.get("/api/health")
def health(): return {"status":"ok"}
@app.get("/api/profile")
def get_profile(): return profile()
@app.post("/api/jobs/refresh")
def refresh(x:Search):
    data=discover()
    return {"total_found":len(data),"jobs":list_jobs(x.query,x.location)}
@app.get("/api/jobs")
def jobs(query:str="",location:str=""): return list_jobs(query,location)
def require_job(i):
    j=get_job(i)
    if not j: raise HTTPException(404,"Job not found. Configure a company board and refresh.")
    return j
@app.post("/api/jobs/{i}/tailor")
def tailor(i:str,x:JobAction):
    j=require_job(i);p=profile()
    prompt=f"Candidate profile facts: {json.dumps(p)}\\nJob: {j['title']} at {j['company']}\\nDescription: {j['description'][:10000]}\\nWrite an ATS-friendly resume in Markdown, plus match analysis and missing skills. Mark uncertain details [VERIFY]."
    try: out=ai(prompt,"Create truthful resumes. Never invent dates, skills, metrics, employers, qualifications or achievements.")
    except Exception as e: raise HTTPException(400,str(e))
    path=save_doc(out,"resume_"+i+".docx")
    return {"resume_draft":out,"docx_file":path,"warning":"Review every detail and [VERIFY] field."}
@app.post("/api/jobs/{i}/prep")
def prep(i:str,x:JobAction):
    j=require_job(i);p=profile()
    prompt=f"Candidate profile: {json.dumps(p)}\\nJob: {j['title']} at {j['company']}\\nDescription: {j['description'][:9000]}\\nCreate technical and HR interview questions, answer outlines, study materials/resources and a 5-day study plan. Clearly label questions as predicted unless you have a verifiable public source; do not claim unverified questions were previously asked."
    try: out=ai(prompt,"You are a transparent interview preparation researcher.")
    except Exception as e: raise HTTPException(400,str(e))
    os.makedirs(OUT,exist_ok=True);path=os.path.join(OUT,"interview_prep_"+i+".md");open(path,"w",encoding="utf8").write(out)
    return {"preparation":out,"file":path}
@app.post("/api/jobs/{i}/application-pack")
def pack(i:str,x:JobAction):
    j=require_job(i);p=profile()
    prompt=f"Candidate: {json.dumps(p)}\\nJob: {j['title']} at {j['company']}\\nURL: {j['url']}\\nDraft a concise professional HR application email. Do not invent a contact name or email address."
    try: draft=ai(prompt,"Write a truthful professional recruiter email.")
    except Exception as e: raise HTTPException(400,str(e))
    text=f"# Application checklist\\nCompany: {j['company']}\\nRole: {j['title']}\\nOfficial application page: {j['url']}\\n\\n- [ ] Verify job is active and eligibility matches\\n- [ ] Review resume and all details\\n- [ ] Review every application form answer\\n- [ ] Submit manually on official site\\n- [ ] Save confirmation\\n\\n# HR email draft\\n{draft}"
    os.makedirs(OUT,exist_ok=True);path=os.path.join(OUT,"application_pack_"+i+".md");open(path,"w",encoding="utf8").write(text)
    return {"application_pack":text,"file":path,"submission":"Not submitted. Human review and submission required."}
@app.post("/api/applications")
def track(x:Track):
    if not get_job(x.job_id): raise HTTPException(404,"Unknown job")
    c=db();c.execute("INSERT INTO applications(job_id,status,notes) VALUES(?,?,?)",(x.job_id,x.status,x.notes));c.commit();c.close()
    return {"saved":True}
@app.get("/api/applications")
def applications():
    c=db();r=[dict(x) for x in c.execute("SELECT * FROM applications ORDER BY created DESC")];c.close();return r