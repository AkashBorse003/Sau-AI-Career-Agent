import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import core


class MatchingTests(unittest.TestCase):
    def test_relevant_skills_role_and_location_score_high(self):
        candidate = {
            "skills": ["Java", "Spring Boot", "SQL"],
            "preferences": {"roles": ["Java Developer"], "locations": ["Pune"]},
        }
        job = {
            "title": "Java Developer - Spring Boot",
            "location": "Pune, India",
            "description": "Build REST API services using Java, Spring Boot and SQL.",
        }
        result = core.job_match(job, candidate)
        self.assertGreaterEqual(result["score"], 90)
        self.assertEqual(set(result["matched_skills"]), {"Java", "Spring Boot", "SQL"})

    def test_missing_skills_are_reported(self):
        candidate = {"skills": ["Java"], "preferences": {"roles": [], "locations": []}}
        job = {"title": "Python Engineer", "location": "Remote", "description": "Python, Docker and AWS"}
        result = core.job_match(job, candidate)
        self.assertIn("Docker", result["missing_skills"])
        self.assertIn("AWS", result["missing_skills"])


class MigrationTests(unittest.TestCase):
    def test_legacy_database_is_migrated_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "legacy.db"
            connection = sqlite3.connect(database)
            connection.execute("CREATE TABLE jobs(id TEXT PRIMARY KEY, source TEXT, company TEXT, title TEXT, location TEXT, url TEXT, description TEXT, score INTEGER DEFAULT 0)")
            connection.execute("INSERT INTO jobs(id,company,title) VALUES('job-1','Example','Java Developer')")
            connection.execute("CREATE TABLE applications(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, status TEXT DEFAULT 'saved', notes TEXT DEFAULT '', created TEXT DEFAULT CURRENT_TIMESTAMP)")
            connection.execute("INSERT INTO applications(job_id) VALUES('job-1')")
            connection.commit()
            connection.close()
            with patch.object(core, "DB", database):
                migrated = core.db()
                job_columns = {row[1] for row in migrated.execute("PRAGMA table_info(jobs)")}
                application_columns = {row[1] for row in migrated.execute("PRAGMA table_info(applications)")}
                self.assertIn("created", job_columns)
                self.assertTrue({"company", "title", "applied_at"}.issubset(application_columns))
                self.assertEqual(migrated.execute("SELECT title FROM jobs WHERE id='job-1'").fetchone()[0], "Java Developer")
                self.assertEqual(migrated.execute("SELECT company FROM applications WHERE job_id='job-1'").fetchone()[0], "Example")
                migrated.close()


if __name__ == "__main__":
    unittest.main()
