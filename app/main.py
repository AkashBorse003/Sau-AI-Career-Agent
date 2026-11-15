from pathlib import Path
from typing import Optional
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,HttpUrl
from app.core import ai,db,profile,save_profile,save_doc
from app.config import OUT,OPENAI_API_KEY
from app.job_sources import discover_jobs,list_jobs,get_job
from app.automation import inspect_and_fill,close_browser
from app.email_agent import list_unread,create_reply_draft
app=FastAPI(title="Sau AI Career Agent",version="1.0.0",description="Local-first AI career assistant")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
class SearchRequest(BaseModel): query:str=""; location:str=""
class ProfileRequest(BaseModel): profile:dict
class ApplicationRequest(BaseModel): job_id:str; status:str="saved"; notes:str=""
class AutomationRequest(BaseModel): url:HttpUrl; resume_path:Optional[str]=None
class EmailDraftRequest(BaseModel): message_id:str; instruction:str="Write a polite professional reply. Do not make commitments not confirmed by me."
@app.get("/")
def home(): return {"name":"Sau AI Career Agent","version":"1.0.0","docs":"/docs"}
@app.get("/api/health")
def health(): return {"status":"ok","ai_configured":bool(OPENAI_API_KEY)}
@app.get("/api/profile")
def get_profile(): return profile()
@app.put("/api/profile")
def put_profile(request:ProfileRequest): return save_profile(request.profile)
@app.post("/api/jobs/refresh")
def refresh(request:SearchRequest=SearchRequest()):
    try:
        found=discover_jobs(); return {"total_found":len(found),"jobs":list_jobs(request.query,request.location)}
    except Exception as e: raise HTTPException(500,str(e))
@app.get("/api/jobs")
def jobs(query:str="",location:str="",source:str=""): return list_jobs(query,location,source)
@app.post("/api/jobs/{job_id}/tailor")
def tailor(job_id:str):
    j=get_job(job_id)
    if not j: raise HTTPException(404,"Job not found. Refresh job boards first.")
    try:
        result=ai("Candidate profile: "+str(profile())+"\nJob: "+j["title"]+" at "+j["company"]+"\nDescription: "+j["description"][:10000]+"\nCreate truthful ATS-friendly resume Markdown and match analysis. Mark unknown details [VERIFY]. Never invent candidate facts.")
        return {"draft":result,"file":save_doc(result,OUT/("tailored_resume_"+job_id+".docx")),"warning":"Review every detail and [VERIFY] marker."}
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/api/jobs/{job_id}/prep")
def prep(job_id:str):
    j=get_job(job_id)
    if not j: raise HTTPException(404,"Job not found.")
    try:
        result=ai("Prepare technical and HR interview practice, answer outlines and a 5-day plan. Label all questions as practice predictions. Candidate: "+str(profile())+"\nJob: "+j["title"]+" at "+j["company"]+"\n"+j["description"][:9000])
        path=OUT/("interview_prep_"+job_id+".md"); path.write_text(result,encoding="utf-8")
        return {"preparation":result,"file":str(path)}
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/api/applications")
def add_application(request:ApplicationRequest):
    j=get_job(request.job_id)
    if not j: raise HTTPException(404,"Unknown job ID.")
    c=db(); cur=c.execute("INSERT INTO applications(job_id,company,title,status,notes) VALUES(?,?,?,?,?)",(request.job_id,j["company"],j["title"],request.status,request.notes))
    c.commit(); out={"id":cur.lastrowid,"saved":True}; c.close(); return out
@app.get("/api/applications")
def applications():
    c=db(); rows=[dict(x) for x in c.execute("SELECT * FROM applications ORDER BY created DESC")]; c.close(); return rows
@app.patch("/api/applications/{application_id}")
def update_application(application_id:int,status:str,notes:str=""):
    c=db(); cur=c.execute("UPDATE applications SET status=?,notes=? WHERE id=?",(status,notes,application_id)); c.commit(); c.close()
    if not cur.rowcount: raise HTTPException(404,"Application not found.")
    return {"updated":True}
@app.post("/api/automation/fill")
def autofill(request:AutomationRequest):
    try: return inspect_and_fill(str(request.url),profile(),request.resume_path)
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/api/automation/close")
def automation_close(): close_browser(); return {"closed":True}
@app.post("/api/email/unread")
def unread_emails(limit:int=15):
    try: return list_unread(max(1,min(limit,30)))
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/api/email/draft")
def email_draft(request:EmailDraftRequest):
    try: return create_reply_draft(request.message_id,request.instruction)
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/api/email/reply-text")
def reply_text(payload:dict):
    try:
        result=ai("Write a professional reply to this recruiter email.\nEmail: "+payload.get("email","")+"\nMy instruction: "+payload.get("instruction","Write a polite reply."),
          "Draft only; never send. Do not invent availability, salary or personal facts.")
        return {"draft":result}
    except Exception as e: raise HTTPException(400,str(e))
