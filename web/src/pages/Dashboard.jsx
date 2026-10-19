import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";

const TEMPLATES = [
  { key: "market_research", name: "Pazar Araştırması" },
  { key: "public_opinion", name: "Kamuoyu / Kriz" },
  { key: "concept_test", name: "Ürün Konsepti" },
  { key: "price_probe", name: "Fiyat Testi" },
  { key: "policy_review", name: "Politika / Düzenlemeler" },
  { key: "fiction_review", name: "Kütürel Dünya" },
];

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [err, setErr] = useState(null);
  const [name, setName] = useState("");
  const [template, setTemplate] = useState("market_research");

  useEffect(() => {
    api("/api/projects").then(setProjects).catch(setErr);
  }, []);

  async function createProject(e) {
    e.preventDefault();
    try {
      const p = await api("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name, template_key: template }),
      });
      setProjects([...projects, p]);
      setName("");
    } catch (e2) {
      setErr(e2.message);
    }
  }

  return (
    <main className="container">
      <h1>Projeler</h1>
      {err && <p className="error">{err}</p>}
      <form onSubmit={createProject} className="row">
        <select value={template} onChange={(e) => setTemplate(e.target.value)}>
          {TEMPLATES.map((t) => (
            <option key={t.key} value={t.key}>{t.name}</option>
          ))}
        </select>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Proje adı" required />
        <button type="submit">Oluştur</button>
      </form>
      <ul>
        {projects.map((p) => (
          <li key={p.id}>
            <Link to={`/projects/${p.id}`}>{p.name}</Link> — <em>{p.status}</em>
          </li>
        ))}
      </ul>
    </main>
  );
}
