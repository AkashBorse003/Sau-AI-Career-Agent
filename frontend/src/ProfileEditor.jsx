import React, { useEffect, useState } from "react";
import { Save, UserRound, Code2, MapPin } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const csv = (items) => Array.isArray(items) ? items.join(", ") : "";
const list = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);

export default function ProfileEditor({ profile, onSaved }) {
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!profile) return;
    setDraft({
      ...profile,
      skillsText: csv(profile.skills),
      rolesText: csv(profile.preferences?.roles),
      locationsText: csv(profile.preferences?.locations),
    });
  }, [profile]);

  async function save() {
    if (!draft) return;
    setBusy(true);
    setError("");
    const payload = {
      ...draft,
      skills: list(draft.skillsText || ""),
      preferences: {
        ...(draft.preferences || {}),
        roles: list(draft.rolesText || ""),
        locations: list(draft.locationsText || ""),
      },
    };
    delete payload.skillsText;
    delete payload.rolesText;
    delete payload.locationsText;
    try {
      const response = await fetch(API + "/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: payload }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not save profile.");
      onSaved?.(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (!draft) return <section className="panel"><p>Loading career profile...</p></section>;
  const change = (key, value) => setDraft((current) => ({ ...current, [key]: value }));

  return (
    <section className="panel profile-editor">
      <div className="panel-head">
        <div><h3>Career profile</h3><p>Accurate details improve job matching, resume tailoring and assisted form filling.</p></div>
        <button className="primary" onClick={save} disabled={busy}><Save size={16} />{busy ? "Saving..." : "Save profile"}</button>
      </div>
      {error && <div className="notice">{error}</div>}
      <div className="profile-grid">
        <label className="field">Full name<input value={draft.full_name || ""} onChange={(e) => change("full_name", e.target.value)} /></label>
        <label className="field">Email<input type="email" value={draft.email || ""} onChange={(e) => change("email", e.target.value)} /></label>
        <label className="field">Phone<input value={draft.phone || ""} onChange={(e) => change("phone", e.target.value)} /></label>
        <label className="field">Current location<input value={draft.location || ""} onChange={(e) => change("location", e.target.value)} /></label>
      </div>
      <label className="field"><span><Code2 size={14} /> Skills</span><small>Comma-separated, e.g. Java, Spring Boot, SQL, React</small><textarea rows="3" value={draft.skillsText || ""} onChange={(e) => change("skillsText", e.target.value)} placeholder="Java, Spring Boot, Python, SQL" /></label>
      <label className="field">Target job roles<small>Comma-separated</small><textarea rows="2" value={draft.rolesText || ""} onChange={(e) => change("rolesText", e.target.value)} placeholder="Java Developer, Spring Boot Developer, Full Stack Developer" /></label>
      <label className="field"><span><MapPin size={14} /> Preferred locations</span><small>Comma-separated; leave blank if flexible</small><textarea rows="2" value={draft.locationsText || ""} onChange={(e) => change("locationsText", e.target.value)} placeholder="Pune, Bengaluru, Remote" /></label>
      <div className="tip">Keep education and experience records accurate in data/profile.json. Do not add guessed qualifications or achievements. After saving, refresh jobs to recalculate match scores.</div>
    </section>
  );
}
