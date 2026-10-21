import { useCallback, useEffect, useState } from "react";

import { api } from "../api.js";
import Icon from "../icons.jsx";

const STATUS = {
  queued: ["Sırada", "no-dot"],
  scheduled: ["Zamanlandı", "warn"],
  generating: ["Üretiliyor", "warn"],
  published: ["Yayınlandı", "ok"],
  failed: ["Hata", "bad"],
};

function fmt(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString("tr-TR");
}

export default function AdminBlog() {
  const [auto, setAuto] = useState(null);
  const [topics, setTopics] = useState([]);
  const [posts, setPosts] = useState([]);
  const [draft, setDraft] = useState("");
  const [err, setErr] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(null);

  const load = useCallback(async () => {
    const [a, t, p] = await Promise.all([
      api("/api/admin/blog/automation"),
      api("/api/admin/blog/topics"),
      api("/api/admin/blog/posts"),
    ]);
    setAuto(a);
    setTopics(t);
    setPosts(p);
  }, []);

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, [load]);

  async function saveAuto(patch) {
    setBusy("auto");
    setErr(null);
    setNotice(null);
    try {
      setAuto(await api("/api/admin/blog/automation", { method: "PUT", body: JSON.stringify({ ...auto, ...patch }) }));
      setNotice("Otomasyon ayarları kaydedildi.");
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  async function addTopics() {
    const lines = draft.split("\n").map((line) => line.trim()).filter((line) => line.length >= 4);
    if (!lines.length) {
      setErr("En az 4 karakterlik bir konu girin.");
      return;
    }
    if (lines.length > 50) {
      setErr("Tek seferde en fazla 50 konu eklenebilir.");
      return;
    }
    setBusy("add");
    setErr(null);
    setNotice(null);
    try {
      const res = await api("/api/admin/blog/topics", {
        method: "POST",
        body: JSON.stringify({ topics: lines.map((topic) => ({ topic, keywords: "" })) }),
      });
      setDraft("");
      setNotice(`${res.added} konu kuyruğa eklendi. Motor konuları sırayla işleyecek.`);
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  async function generate(id) {
    setBusy(`gen-${id}`);
    setErr(null);
    setNotice(null);
    try {
      await api(`/api/admin/blog/topics/${id}/generate`, { method: "POST" });
      setNotice("Konu üretim kuyruğuna alındı.");
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  async function remove(id) {
    setBusy(`del-${id}`);
    setErr(null);
    try {
      await api(`/api/admin/blog/topics/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  async function togglePost(slug, isPublished) {
    setBusy(`post-${slug}`);
    setErr(null);
    try {
      await api(`/api/admin/blog/posts/${slug}`, { method: "PATCH", body: JSON.stringify({ is_published: !isPublished }) });
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  async function tick() {
    setBusy("tick");
    setErr(null);
    setNotice(null);
    try {
      await api("/api/admin/blog/tick", { method: "POST" });
      setNotice("Zamanlayıcı tetiklendi; uygun konu varsa üretim başlayacak.");
    } catch (e) {
      setErr(e.message);
    }
    setBusy(null);
  }

  if (!auto) return <div className="shell-loading" style={{ minHeight: 220 }}><div className="spinner" /></div>;

  return (
    <>
      <div className="detail-head">
        <div>
          <span className="crumb"><Icon name="doc" size={13} /> İçerik operasyonları</span>
          <h2>AI blog editörü</h2>
          <p className="muted small">Konu kuyruğu, otomatik yayın aralığı ve yayınlanan yazıların yönetimi. Yazılar <a href="/blog" target="_blank" rel="noreferrer">/blog</a> adresinde görünür.</p>
        </div>
        <button className="btn" type="button" disabled={busy === "tick"} onClick={tick}><Icon name="activity" size={15} /> Zamanlayıcıyı çalıştır</button>
      </div>

      {err && <p className="error">{err}</p>}
      {notice && <p className="notice ok"><Icon name="check" size={15} /><span>{notice}</span></p>}

      <div className="grid-2">
        <div className="card card-pad">
          <div className="row-between">
            <div>
              <h3>Otomatik yayın</h3>
              <p className="small muted">Kuyruktaki sıradaki konu, seçilen aralıkta bir yayınlanır.</p>
            </div>
            <button
              className={`toggle${auto.enabled ? " on" : ""}`}
              type="button"
              aria-pressed={auto.enabled}
              disabled={busy === "auto"}
              onClick={() => saveAuto({ enabled: !auto.enabled })}
            >
              <span />
            </button>
          </div>
          <div className="row" style={{ marginTop: 16, alignItems: "end" }}>
            <label className="field" style={{ maxWidth: 180 }}>
              <span>Yayın aralığı (gün)</span>
              <input
                className="input"
                type="number"
                min="1"
                max="365"
                value={auto.interval_days}
                onChange={(e) => setAuto({ ...auto, interval_days: Number(e.target.value) })}
              />
            </label>
            <button className="btn btn-primary" type="button" disabled={busy === "auto"} onClick={() => saveAuto({ interval_days: auto.interval_days })}>Kaydet</button>
          </div>
          <div className="mini-facts" style={{ marginTop: 16 }}>
            <div><span>Durum</span><strong>{auto.enabled ? "Açık" : "Kapalı"}</strong></div>
            <div><span>Sıradaki çalışma</span><strong>{fmt(auto.next_run_at)}</strong></div>
            <div><span>Son üretim</span><strong>{fmt(auto.last_run_at)}</strong></div>
          </div>
        </div>

        <div className="card card-pad">
          <h3>Konu kuyruğu</h3>
          <p className="small muted">Her satıra bir konu yazın. Konular sırayla işlenir; üretim tamamlanınca yazı otomatik yayınlanır.</p>
          <textarea
            className="input"
            rows={5}
            style={{ marginTop: 10, resize: "vertical" }}
            placeholder={"Örnek: Sosyal medya gönderisi testi nasıl yapılır?\nSentetik kullanıcı segmentleriyle mesaj testi"}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btn-primary" type="button" disabled={busy === "add"} onClick={addTopics}><Icon name="plus" size={15} /> Kuyruğa ekle</button>
            <span className="small muted">Sırada {topics.filter((t) => t.status === "queued").length} konu</span>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head" style={{ padding: "18px 18px 0" }}><h3>Konular</h3></div>
        <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>Konu</th><th>Durum</th><th>Yayın</th><th>Hata</th><th className="num">İşlem</th></tr></thead>
          <tbody>
            {topics.map((topic) => {
              const [label, tone] = STATUS[topic.status] ?? [topic.status, "no-dot"];
              return (
                <tr key={topic.id}>
                  <td>
                    <strong>{topic.topic}</strong>
                    <div className="small muted">Eklendi: {fmt(topic.created_at)}</div>
                  </td>
                  <td><span className={`badge ${tone}`}>{label}</span></td>
                  <td className="small">{topic.post_slug ? <a href={`/blog/${topic.post_slug}`} target="_blank" rel="noreferrer">{topic.post_slug}</a> : fmt(topic.published_at)}</td>
                  <td className="small error" style={{ maxWidth: 220 }}>{topic.error || "—"}</td>
                  <td className="num">
                    {topic.status !== "published" && topic.status !== "generating" && (
                      <button className="btn btn-sm" type="button" disabled={busy === `gen-${topic.id}`} onClick={() => generate(topic.id)}>Şimdi üret</button>
                    )}{" "}
                    <button className="btn btn-sm" type="button" disabled={busy === `del-${topic.id}` || topic.status === "generating"} onClick={() => remove(topic.id)}>Sil</button>
                  </td>
                </tr>
              );
            })}
            {topics.length === 0 && <tr><td colSpan={5} className="muted small">Henüz konu yok.</td></tr>}
          </tbody>
        </table>
        </div>
      </div>

      <div className="card">
        <div className="card-head" style={{ padding: "18px 18px 0" }}><h3>Yayınlanan yazılar</h3><a className="btn btn-sm" href="/blog" target="_blank" rel="noreferrer">Blogu aç</a></div>
        <div className="table-wrap">
        <table className="tbl">
          <thead><tr><th>Başlık</th><th>Slug</th><th>Tarih</th><th>Durum</th><th className="num">İşlem</th></tr></thead>
          <tbody>
            {posts.map((post) => (
              <tr key={post.slug}>
                <td><strong>{post.title_tr}</strong><div className="small muted">{post.title_en}</div></td>
                <td className="small"><a href={`/blog/${post.slug}`} target="_blank" rel="noreferrer">{post.slug}</a></td>
                <td className="small muted">{fmt(post.published_at)}</td>
                <td><span className={`badge ${post.is_published ? "ok" : "no-dot"}`}>{post.is_published ? "Yayında" : "Gizli"}</span></td>
                <td className="num"><button className="btn btn-sm" type="button" disabled={busy === `post-${post.slug}`} onClick={() => togglePost(post.slug, post.is_published)}>{post.is_published ? "Yayından kaldır" : "Yayınla"}</button></td>
              </tr>
            ))}
            {posts.length === 0 && <tr><td colSpan={5} className="muted small">Henüz yazı yok.</td></tr>}
          </tbody>
        </table>
        </div>
      </div>
    </>
  );
}
