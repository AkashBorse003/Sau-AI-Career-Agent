import json
import requests

from app.config import BOARDS_FILE
from app.core import db, job_match, stable_job_id, profile

LAST_DISCOVERY_ERRORS = []


def _read_board_config():
    if not BOARDS_FILE.exists():
        return {"greenhouse": [], "lever": []}
    try:
        config = json.loads(BOARDS_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {BOARDS_FILE.name}: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("company_boards.json must contain a JSON object.")
    return config


def discovery_report():
    return {"errors": list(LAST_DISCOVERY_ERRORS)}


def discover_jobs():
    global LAST_DISCOVERY_ERRORS
    LAST_DISCOVERY_ERRORS = []
    config = _read_board_config()
    found = []
    session = requests.Session()
    session.headers.update({"User-Agent": "Sau-AI-Career-Agent/1.0 (public job board API client)"})

    for item in config.get("greenhouse", []):
        token = str(item.get("board_token", "")).strip()
        if not token or token.startswith("REPLACE_"):
            continue
        try:
            response = session.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true", timeout=25)
            response.raise_for_status()
            for job in response.json().get("jobs", []):
                company = item.get("company", token)
                url = job.get("absolute_url", "")
                found.append({
                    "id": stable_job_id(company, job.get("title", ""), url),
                    "source": "Greenhouse", "company": company, "title": job.get("title", ""),
                    "location": (job.get("location") or {}).get("name", ""),
                    "url": url, "description": job.get("content", ""),
                })
        except (requests.RequestException, ValueError, KeyError) as exc:
            LAST_DISCOVERY_ERRORS.append({"source": "Greenhouse", "company": item.get("company", token), "error": str(exc)})

    for item in config.get("lever", []):
        site = str(item.get("site", "")).strip()
        if not site or site.startswith("REPLACE_"):
            continue
        try:
            response = session.get(f"https://api.lever.co/v0/postings/{site}?mode=json", timeout=25)
            response.raise_for_status()
            for job in response.json():
                company = item.get("company", site)
                url = job.get("hostedUrl", "")
                categories = job.get("categories") or {}
                found.append({
                    "id": stable_job_id(company, job.get("text", ""), url),
                    "source": "Lever", "company": company, "title": job.get("text", ""),
                    "location": categories.get("location", ""), "url": url,
                    "description": (job.get("descriptionPlain", "") + " " + job.get("additionalPlain", "")).strip(),
                })
        except (requests.RequestException, ValueError, KeyError) as exc:
            LAST_DISCOVERY_ERRORS.append({"source": "Lever", "company": item.get("company", site), "error": str(exc)})

    candidate = profile()
    conn = db()
    try:
        for job in found:
            job["score"] = job_match(job, candidate)["score"]
            conn.execute("""INSERT INTO jobs(id,source,company,title,location,url,description,score)
                VALUES(:id,:source,:company,:title,:location,:url,:description,:score)
                ON CONFLICT(id) DO UPDATE SET source=excluded.source, company=excluded.company,
                title=excluded.title, location=excluded.location, url=excluded.url,
                description=excluded.description, score=excluded.score""", job)
        conn.commit()
    finally:
        conn.close()
    return found


def list_jobs(query="", location="", source=""):
    conn = db()
    try:
        rows = [dict(row) for row in conn.execute("SELECT * FROM jobs ORDER BY score DESC, created DESC")]
    finally:
        conn.close()
    q, loc, src = query.strip().lower(), location.strip().lower(), source.strip().lower()
    result = []
    candidate = profile()
    for row in rows:
        searchable = " ".join([row.get("title") or "", row.get("description") or "", row.get("company") or ""]).lower()
        if q and q not in searchable:
            continue
        if loc and loc not in (row.get("location") or "").lower():
            continue
        if src and src not in (row.get("source") or "").lower():
            continue
        match = job_match(row, candidate)
        row["score"] = match["score"]
        row["match_details"] = match
        result.append(row)
    result.sort(key=lambda row: (row["score"], row.get("created") or ""), reverse=True)
    return result


def get_job(job_id):
    conn = db()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
