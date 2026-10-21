import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ACTIVE_STATUSES, api, downloadReport, fmtDate, fmtTokens, STAGES, stageIndex, streamRunEvents } from "../api.js";
import Icon from "../icons.jsx";

function eventText(ev) {
  const p = ev.payload ?? {};
  if (p.message) return p.message;
  if (p.content) return p.content;
  if (p.action) return p.action;
  return ev.event_type;
}

export default function RunDetail() {
  const { id } = useParams();
  const [run, setRun] = useState(null);
  const [events, setEvents] = useState([]);
  const [err, setErr] = useState(null);
  const [canceling, setCanceling] = useState(false);
  const seen = useRef(new Set());

  const load = useCallback(
    () => api(`/api/runs/${id}`).then(setRun).catch((e) => setErr(e.message)),
    [id]
  );

  const loadEvents = useCallback(
    () =>
      api(`/api/runs/${id}/events`)
        .then((rows) => {
          setEvents(rows);
          seen.current = new Set(rows.map((r) => r.id));
        })
        .catch(() => {}),
    [id]
  );

  useEffect(() => { load(); loadEvents(); }, [load, loadEvents]);

  const active = run && ACTIVE_STATUSES.includes(run.status);

  useEffect(() => {
    if (!active) return undefined;
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [active, load]);

  useEffect(() => {
    if (!active) return undefined;
    const controller = new AbortController();
    streamRunEvents(id, {
      signal: controller.signal,
      onStatus: (s) =>
        setRun((prev) => (prev ? { ...prev, ...s } : prev)),
      onEvent: (ev) => {
        if (seen.current.has(ev.id)) return;
        seen.current.add(ev.id);
        setEvents((prev) => [...prev, ev]);
      },
    }).catch(() => {});
    return () => controller.abort();
  }, [active, id]);

  async function cancelRun() {
    setCanceling(true);
    try {
      await api(`/api/runs/${id}/cancel`, { method: "POST" });
      load();
    } catch (e) { setErr(e.message); }
    setCanceling(false);
  }

  if (err && !run) {
    return (<><p className="error">{err}</p><Link className="btn" to="/app/runs">← Simülasyonlara dön</Link></>);
  }
  if (!run) return <div className="shell-loading" style={{ minHeight: 220 }}><div className="spinner" /></div>;

  const idx = stageIndex(run.status);
  const failed = run.status === "failed";
  const canceled = run.status === "canceled";

  return (
    <>
      <div className="detail-head">
        <div>
          <span className="crumb"><Link to="/app/runs">Simülasyonlar</Link><Icon name="chevron" size={13} /> {String(run.id).slice(0, 8)}</span>
          <h2>Simülasyon <span className="mono" style={{ fontSize: 18 }}>{String(run.id).slice(0, 8)}</span></h2>
          <div className="row" style={{ marginTop: 8 }}>
            {failed ? <span className="badge bad">hata</span> : canceled ? <span className="badge bad">iptal</span> : run.status === "completed" ? <span className="badge ok">tamamlandı</span> : <span className="badge run">{run.status}</span>}
            {run.project_name && <Link className="badge no-dot" to={`/app/projects/${run.project_id}`}>{run.project_name}</Link>}
            {run.template_key && <span className="badge no-dot">{run.template_key}</span>}
          </div>
        </div>
        <div className="row">
          {active && (
            <button className="btn" type="button" onClick={cancelRun} disabled={canceling}>
              <Icon name="x" size={15} /> {canceling ? "İptal ediliyor…" : "İptal Et"}
            </button>
          )}
          {run.report_object_key && (
            <>
              <Link className="btn" to={`/app/reports/${id}`}>
                <Icon name="chart" size={15} /> Analiz
              </Link>
              <button className="btn btn-primary" type="button" onClick={() => downloadReport(id, "pdf").catch((e) => setErr(e.message))}>
                <Icon name="doc" size={15} /> Rapor (PDF)
              </button>
            </>
          )}
        </div>
      </div>

      <div className="stat-grid">
        <div className="card stat"><div className="stat-label">Tur</div><div className="stat-value" style={{ fontSize: 22 }}>{run.current_round ?? 0}</div></div>
        <div className="card stat"><div className="stat-label">Token</div><div className="stat-value" style={{ fontSize: 22 }}>{fmtTokens(run.tokens_used)}</div></div>
        <div className="card stat"><div className="stat-label">Başlangıç</div><div className="stat-value" style={{ fontSize: 15, marginTop: 10 }}>{fmtDate(run.created_at)}</div></div>
      </div>

      {(failed || canceled) && run.error && <p className="error">{run.error}</p>}

      <div className="grid-2">
        <div className="card card-pad">
          <h3 style={{ marginBottom: 16 }}>İşlem hattı</h3>
          <div className="stage-list">
            {STAGES.map((s, i) => {
              let cls = "stage";
              if (failed && i === idx) cls += " failed";
              else if (run.status === "completed" || i < idx) cls += " done";
              else if (i === idx) cls += " current";
              return (
                <div className={cls} key={s.key}>
                  <span className="s-dot">{cls.includes("done") ? <Icon name="check" size={13} /> : i + 1}</span>
                  <div className="s-body">
                    <div className="s-label">{s.label}</div>
                    <div className="s-sub">{cls.includes("done") ? "tamamlandı" : cls.includes("current") ? failed ? "bu adımda hata oluştu" : "işleniyor…" : cls.includes("failed") ? "hata" : "bekliyor"}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="card card-pad">
          <h3 style={{ marginBottom: 12 }}>Canlı olay akışı <span className="badge no-dot" style={{ marginLeft: 6 }}>{events.length}</span></h3>
          {events.length === 0 ? (
            <p className="small muted">Simülasyon başladığında ajan olayları burada akar.</p>
          ) : (
            <div className="feed">
              {events.map((ev) => (
                <div className="feed-item" key={ev.id}>
                  <div className="feed-meta">
                    <div className="feed-round">T{ev.round}</div>
                    <div className="feed-actor">{ev.platform}</div>
                  </div>
                  <div className="feed-body">
                    <span className="evt">{ev.event_type}</span>{" "}
                    <span className="txt">{eventText(ev)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {run.report_meta && (
        <div className="card card-pad" style={{ marginTop: 18 }}>
          <div className="row" style={{ justifyContent: "space-between", marginBottom: 10 }}>
            <h3>Rapor</h3>
            <div className="row">
              <button className="btn btn-sm" type="button" onClick={() => downloadReport(id, "pdf").catch((e) => setErr(e.message))}>PDF indir</button>
              <button className="btn btn-sm" type="button" onClick={() => downloadReport(id, "md").catch((e) => setErr(e.message))}>Markdown indir</button>
            </div>
          </div>
          {Array.isArray(run.report_meta.sections) && run.report_meta.sections.length > 0 && (
            <div className="row" style={{ flexWrap: "wrap", gap: 6, marginBottom: 8 }}>
              {run.report_meta.sections.map((s, i) => <span className="badge no-dot" key={i}>{s}</span>)}
            </div>
          )}
          <p className="small muted">
            {run.report_meta.sources ? `${run.report_meta.sources} kaynak belge · ` : ""}
            {run.report_meta.events ? `${run.report_meta.events} olay` : ""}
          </p>
        </div>
      )}

      <div className="notice"><Icon name="bell" size={15} /><span>Bu koşunun tüm olayları ve raporu simülasyon ürünüdür; gerçek anket veya saha verisi değildir.</span></div>
    </>
  );
}
