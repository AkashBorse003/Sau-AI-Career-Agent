import hashlib
import html
import json
import re
import sqlite3
from pathlib import Path

from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL, DB, PROFILE_FILE

DEFAULT_PROFILE = {
    "full_name": "", "email": "", "phone": "", "location": "",
    "skills": [], "education": [], "experience": [],
    "preferences": {"roles": [], "locations": []},
}


def profile():
    if not PROFILE_FILE.exists():
        return json.loads(json.dumps(DEFAULT_PROFILE))
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Profile must be a JSON object.")
        data.setdefault("preferences", {})
        data["preferences"].setdefault("roles", [])
        data["preferences"].setdefault("locations", [])
        for key, default in DEFAULT_PROFILE.items():
            data.setdefault(key, json.loads(json.dumps(default)))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Could not read data/profile.json: {exc}") from exc


def save_profile(data):
    if not isinstance(data, dict):
        raise ValueError("Profile must be a JSON object.")
    current = profile()
    merged = {**current, **data}
    merged["preferences"] = {**current.get("preferences", {}), **data.get("preferences", {})}
    PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = PROFILE_FILE.with_suffix(".json.tmp")
    temp.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(PROFILE_FILE)
    return merged


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def _add_missing_columns(conn, table, definitions):
    existing = _columns(conn, table)
    for name, definition in definitions.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")


def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, source TEXT, company TEXT, title TEXT,
            location TEXT, url TEXT, description TEXT, score INTEGER DEFAULT 0,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, company TEXT,
            title TEXT, status TEXT DEFAULT 'saved', notes TEXT DEFAULT '',
            applied_at TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS email_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT, gmail_id TEXT UNIQUE,
            sender TEXT, subject TEXT, snippet TEXT, category TEXT, draft TEXT,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        )""")

        # Additive migrations preserve records in older local databases.
        _add_missing_columns(conn, "jobs", {
            "source": "TEXT", "company": "TEXT", "title": "TEXT", "location": "TEXT",
            "url": "TEXT", "description": "TEXT", "score": "INTEGER DEFAULT 0", "created": "TEXT",
        })
        _add_missing_columns(conn, "applications", {
            "job_id": "TEXT", "company": "TEXT", "title": "TEXT", "status": "TEXT DEFAULT 'saved'",
            "notes": "TEXT DEFAULT ''", "applied_at": "TEXT", "created": "TEXT",
        })
        _add_missing_columns(conn, "email_events", {
            "gmail_id": "TEXT", "sender": "TEXT", "subject": "TEXT", "snippet": "TEXT",
            "category": "TEXT", "draft": "TEXT", "created": "TEXT",
        })
        for table in ("jobs", "applications", "email_events"):
            conn.execute(f"UPDATE {table} SET created=CURRENT_TIMESTAMP WHERE created IS NULL OR created=''")
        conn.execute("UPDATE applications SET company=(SELECT company FROM jobs WHERE jobs.id=applications.job_id) WHERE company IS NULL")
        conn.execute("UPDATE applications SET title=(SELECT title FROM jobs WHERE jobs.id=applications.job_id) WHERE title IS NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_score_created ON jobs(score DESC, created DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_created ON applications(created DESC)")
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


def ai(prompt, system="You are a careful career assistant. Never invent candidate facts."):
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is missing. Add it to .env and restart.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=OPENAI_MODEL, temperature=0.2,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _contains_phrase(text, phrase):
    phrase = _clean_text(phrase)
    if not phrase:
        return False
    pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


JOB_SKILL_CATALOG = [
    "Java", "Spring Boot", "Python", "JavaScript", "TypeScript", "React", "Angular", "Flutter",
    "SQL", "MySQL", "PostgreSQL", "Oracle", "MongoDB", "REST API", "Microservices", "Docker",
    "Kubernetes", "AWS", "Azure", "Git", "Linux", "Node.js", "FastAPI", "Django", "C++", "C#",
    ".NET", "Selenium", "Playwright", "Machine Learning", "Data Science", "HTML", "CSS",
]


def job_match(job, candidate=None):
    candidate = candidate or profile()
    prefs = candidate.get("preferences") or {}
    skills = [str(x).strip() for x in candidate.get("skills", []) if str(x).strip()]
    roles = [str(x).strip() for x in prefs.get("roles", []) if str(x).strip()]
    locations = [str(x).strip() for x in prefs.get("locations", []) if str(x).strip()]
    title = _clean_text(job.get("title"))
    all_text = title + " " + _clean_text(job.get("description"))
    job_location = _clean_text(job.get("location"))

    matched = [skill for skill in skills if _contains_phrase(all_text, skill)]
    detected = [skill for skill in JOB_SKILL_CATALOG if _contains_phrase(all_text, skill)]
    missing = [skill for skill in detected if not any(_clean_text(s) == _clean_text(skill) for s in skills)]
    role_matches = [role for role in roles if _contains_phrase(title, role)]
    location_matches = [loc for loc in locations if _contains_phrase(job_location, loc)]

    # Score only dimensions for which the candidate supplied preferences.
    weighted = []
    if skills:
        weighted.append((60, len(matched) / len(skills)))
    if roles:
        weighted.append((25, 1.0 if role_matches else 0.0))
    if locations:
        weighted.append((15, 1.0 if location_matches else 0.0))
    total_weight = sum(weight for weight, _ in weighted)
    score = round(sum(weight * value for weight, value in weighted) / total_weight * 100) if total_weight else 0
    return {
        "score": max(0, min(100, score)),
        "matched_skills": matched,
        "missing_skills": missing[:12],
        "role_matches": role_matches,
        "location_matches": location_matches,
        "explanation": "Matched " + (", ".join(matched) if matched else "no listed profile skills") + ".",
    }


def score_job(job, candidate=None):
    return job_match(job, candidate)["score"]


def stable_job_id(company, title, url):
    return hashlib.sha1((company + "|" + title + "|" + url).encode("utf-8")).hexdigest()[:16]


def save_doc(text, path):
    from docx import Document
    document = Document()
    for line in text.splitlines():
        item = line.strip()
        if not item:
            continue
        if item.startswith("# "):
            document.add_heading(item[2:], 0)
        elif item.startswith("## "):
            document.add_heading(item[3:], 1)
        elif item.startswith("- "):
            document.add_paragraph(item[2:], style="List Bullet")
        else:
            document.add_paragraph(item.replace("**", ""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    document.save(str(path))
    return str(path)
