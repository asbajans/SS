import { useEffect, useState } from "react";

import { api } from "../api.js";

export default function ProjectDetail() {
  const [runs, setRuns] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api("/api/runs/").then(setRuns).catch(setErr);
  }, []);

  return (
    <main className="container">
      <h1>Proje</h1>
      {err && <p className="error">{err}</p>}
      <ul>
        {runs.map((r) => (
          <li key={r.id}>
            Run {r.id} — {r.status}
          </li>
        ))}
      </ul>
    </main>
  );
}
