import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, PROFILES, TEMPLATES } from "../api.js";
import Icon from "../icons.jsx";

function WizardBar({ step }) {
  const labels = ["Şablon", "Konu & Proje", "Simülasyon Profili"];
  return (
    <div className="wizard-steps">
      {labels.map((lbl, i) => {
        const n = i + 1;
        const cls = n === step ? "wz active" : n < step ? "wz done" : "wz";
        return (
          <div key={lbl} style={{ display: "contents" }}>
            {i > 0 && <span className={`wz-line${n <= step ? " done" : ""}`} />}
            <div className={cls}>
              <span className="dot">{n < step ? <Icon name="check" size={14} /> : n}</span>
              <span className="lbl">{lbl}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function NewProject() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const initialTpl = params.get("tpl");
  const hasTpl = initialTpl && TEMPLATES.some((t) => t.key === initialTpl);
  const [step, setStep] = useState(hasTpl ? 2 : 1);
  const [tpl, setTpl] = useState(hasTpl ? initialTpl : "market_research");
  const [templates, setTemplates] = useState(TEMPLATES);
  const [name, setName] = useState("");
  const [language, setLanguage] = useState("tr");
  const [profile, setProfile] = useState("std");
  const [custom, setCustom] = useState({ agents_n: 120, rounds: 30, platforms: 1 });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/api/templates")
      .then((list) => {
        if (Array.isArray(list) && list.length) setTemplates(list);
      })
      .catch(() => {});
  }, []);

  async function finish() {
    setBusy(true); setError(null);
    const cfg =
      profile === "custom"
        ? { agents_n: Number(custom.agents_n), rounds: Number(custom.rounds), platforms: Number(custom.platforms) || 1 }
        : (() => { const p = PROFILES.find((x) => x.key === profile); return { agents_n: p.agents_n, rounds: p.rounds, platforms: p.platforms }; })();
    try {
      const p = await api("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name, template_key: tpl, language, sim_config: cfg }),
      });
      nav(`/app/projects/${p.id}`);
    } catch (e) { setError(e.message); setBusy(false); }
  }

  return (
    <>
      <div className="page-head">
        <div><h2>Yeni simülasyon</h2><p>Şablon seçin, projenizi tanımlayın ve topluluk derinliğini belirleyin.</p></div>
      </div>

      <div className="card card-pad"><WizardBar step={step} /></div>

      {error && <p className="error">{error}</p>}

      {step === 1 && (
        <div className="choice-grid">
          {templates.map((t) => (
            <button key={t.key} type="button" className={`choice${tpl === t.key ? " sel" : ""}`} onClick={() => setTpl(t.key)}>
              <span className="c-icon"><Icon name="box" /></span>
              <h4>{t.name}</h4><p>{t.desc}</p>
            </button>
          ))}
          <div className="row" style={{ gridColumn: "1 / -1", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" type="button" onClick={() => setStep(2)}>Devam <Icon name="chevron" size={15} /></button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="card card-pad" style={{ maxWidth: 640 }}>
          <div className="field">
            <label htmlFor="pname">Proje adı</label>
            <input id="pname" className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Örn: 2026 telefon fiyatı konsept testi" required />
          </div>
          <div className="grid-2">
            <div className="field">
              <label htmlFor="lang">Rapor dili</label>
              <select id="lang" className="select" value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="tr">Türkçe</option><option value="en">English</option>
              </select>
            </div>
            <div className="field"><label>Şablon</label>
              <div className="input" style={{ background: "#f9fafb", display: "flex", alignItems: "center" }}>{templates.find((t) => t.key === tpl)?.name}</div>
            </div>
          </div>
          <div className="dropzone disabled"><Icon name="upload" size={22} />
            <strong>Belge yükleme yakında</strong>
            <p className="small muted">PDF / metin kaynak yükleme bir sonraki fazda bu adıma eklenir.</p>
          </div>
          <div className="row" style={{ marginTop: 18, justifyContent: "space-between" }}>
            <button className="btn" type="button" onClick={() => setStep(1)}><Icon name="arrowLeft" size={15} /> Geri</button>
            <button className="btn btn-primary" type="button" onClick={() => setStep(3)} disabled={!name.trim()}>Devam <Icon name="chevron" size={15} /></button>
          </div>
        </div>
      )}

      {step === 3 && (
        <>
          <div className="choice-grid">
            {PROFILES.map((p) => (
              <button key={p.key} type="button" className={`choice${profile === p.key ? " sel" : ""}`} onClick={() => setProfile(p.key)}>
                <h4>{p.name}</h4><p>{p.hint}</p><span className="meta">{p.agents_n} ajan · {p.rounds} tur · {p.platforms} platform</span><span className="meta">≈ maliyet {p.cost}</span>
              </button>
            ))}
            <button type="button" className={`choice${profile === "custom" ? " sel" : ""}`} onClick={() => setProfile("custom")}>
              <h4>Özel</h4><p>Parametreleri kendiniz belirleyin.</p><span className="meta">ajan 1–300 · tur 1–120</span>
            </button>
          </div>

          {profile === "custom" && (
            <div className="card card-pad" style={{ marginTop: 14 }}>
              <div className="grid-3">
                <div className="field"><label>Ajan sayısı</label><input className="input" type="number" min={1} max={300} value={custom.agents_n} onChange={(e) => setCustom({ ...custom, agents_n: e.target.value })} /></div>
                <div className="field"><label>Tur sayısı</label><input className="input" type="number" min={1} max={120} value={custom.rounds} onChange={(e) => setCustom({ ...custom, rounds: e.target.value })} /></div>
                <div className="field"><label>Platform</label><input className="input" type="number" min={1} max={4} value={custom.platforms} onChange={(e) => setCustom({ ...custom, platforms: e.target.value })} /></div>
              </div>
            </div>
          )}

          <div className="row" style={{ marginTop: 18, justifyContent: "space-between" }}>
            <button className="btn" type="button" onClick={() => setStep(2)}><Icon name="arrowLeft" size={15} /> Geri</button>
            <button className="btn btn-primary" type="button" onClick={finish} disabled={busy}>{busy ? "Oluşturuluyor…" : "Simülasyon projesini oluştur"}</button>
          </div>
        </>
      )}
    </>
  );
}
