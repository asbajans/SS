import { useCallback, useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api } from "../api.js";
import { detectMeasurementId } from "../seo.js";
import Icon from "../icons.jsx";

const EMPTY = {
  site_name: "Social Simulator",
  site_url: "",
  title_suffix: "",
  default_description_tr: "",
  default_description_en: "",
  og_image: "",
  twitter_site: "",
  robots_extra: "",
  block_ai_bots: false,
  allow_ai_bots: "GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot",
  llms_txt: "",
  google_site_verification: "",
  bing_site_verification: "",
  indexnow_enabled: false,
  indexnow_key: "",
  indexnow_endpoint: "https://api.indexnow.org/indexnow",
  analytics_enabled: false,
  analytics_provider: "gtag",
  analytics_id: "",
  analytics_domain: "",
  analytics_code: "",
  ads_enabled: false,
  adsense_client: "",
  adsense_slot: "",
  adsense_slot_secondary: "",
};

const PAGE_FIELDS = [
  "title_tr", "title_en", "description_tr", "description_en",
  "og_image", "canonical_url", "focus_keyword", "noindex",
  "sitemap_priority", "changefreq",
];

function Field({ label, hint, children }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

function Text({ value, onChange, placeholder, type = "text" }) {
  return (
    <input
      className="input"
      type={type}
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function Area({ value, onChange, rows = 3, placeholder }) {
  return (
    <textarea
      className="input"
      rows={rows}
      value={value ?? ""}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

function Check({ checked, onChange, label }) {
  return (
    <label className="check">
      <input type="checkbox" checked={Boolean(checked)} onChange={(e) => onChange(e.target.checked)} />
      {label}
    </label>
  );
}

export default function AdminSeo() {
  const user = useOutletContext();
  const [form, setForm] = useState(EMPTY);
  const [pages, setPages] = useState([]);
  const [staticPages, setStaticPages] = useState([]);
  const [posts, setPosts] = useState([]);
  const [audit, setAudit] = useState(null);
  const [log, setLog] = useState([]);
  const [events, setEvents] = useState([]);
  const [eventCounts, setEventCounts] = useState([]);
  const [editingPage, setEditingPage] = useState(null);
  const [pageForm, setPageForm] = useState({});
  const [editingPost, setEditingPost] = useState(null);
  const [postForm, setPostForm] = useState({});
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const detectedId = detectMeasurementId(form.analytics_code);

  const load = useCallback(async () => {
    try {
      const data = await api("/api/admin/seo");
      const provider = data.settings.analytics_provider;
      setForm({
        ...EMPTY,
        ...data.settings,
        analytics_provider: provider === "ga4" ? "gtag" : (provider || "gtag"),
      });
      setPages(data.pages ?? []);
      setStaticPages(data.static_pages ?? []);
      setPosts(data.posts ?? []);
    } catch (e) {
      setErr(e.message);
    }
  }, []);

  const loadAudit = useCallback(async () => {
    try {
      setAudit(await api("/api/admin/seo/audit"));
    } catch (e) {
      setErr(e.message);
    }
  }, []);

  const loadLog = useCallback(async () => {
    try {
      setLog(await api("/api/admin/seo/indexnow/log"));
    } catch (e) {
      setErr(e.message);
    }
  }, []);

  const loadEvents = useCallback(async () => {
    try {
      const data = await api("/api/admin/analytics/events?limit=100");
      setEvents(data.events ?? []);
      setEventCounts(data.counts ?? []);
    } catch (e) {
      setErr(e.message);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadAudit(); }, [loadAudit]);
  useEffect(() => { loadLog(); }, [loadLog]);
  useEffect(() => { loadEvents(); }, [loadEvents]);

  if (user && !user.is_admin) {
    return <p className="error">Bu sayfa yalnızca yöneticilere açıktır.</p>;
  }

  async function save() {
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      await api("/api/admin/seo", { method: "PUT", body: JSON.stringify(form) });
      setMsg("SEO ayarları kaydedildi");
      load();
      loadAudit();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function regenerateKey() {
    setErr(null);
    try {
      const res = await api("/api/admin/seo/indexnow/key", { method: "POST" });
      set("indexnow_key", res.indexnow_key);
      setMsg("Yeni IndexNow anahtarı üretildi — kaydedin");
    } catch (e) {
      setErr(e.message);
    }
  }

  async function submitIndexNow(allPages = true) {
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      const res = await api("/api/admin/seo/indexnow/submit", {
        method: "POST",
        body: JSON.stringify({ all_pages: allPages, urls: [] }),
      });
      setMsg(res.ok ? `IndexNow gönderimi başarılı (${res.submitted} URL)` : `IndexNow hatası: ${res.detail}`);
      loadLog();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  function startEditPage(p) {
    setEditingPage(p.path);
    const src = p ?? { path: "" };
    const next = { path: src.path ?? "" };
    PAGE_FIELDS.forEach((f) => { next[f] = src[f] ?? ""; });
    next.noindex = Boolean(src.noindex);
    next.sitemap_priority = Number(src.sitemap_priority ?? 0.7);
    setPageForm(next);
  }

  async function savePage() {
    setErr(null);
    setMsg(null);
    const path = (pageForm.path || "").trim();
    if (!path) { setErr("Sayfa yolu gerekli"); return; }
    try {
      await api(`/api/admin/seo/pages${path.startsWith("/") ? path : `/${path}`}`, {
        method: "PUT",
        body: JSON.stringify({
          title_tr: pageForm.title_tr || "",
          title_en: pageForm.title_en || "",
          description_tr: pageForm.description_tr || "",
          description_en: pageForm.description_en || "",
          og_image: pageForm.og_image || "",
          canonical_url: pageForm.canonical_url || "",
          focus_keyword: pageForm.focus_keyword || "",
          noindex: Boolean(pageForm.noindex),
          sitemap_priority: Number(pageForm.sitemap_priority ?? 0.7),
          changefreq: pageForm.changefreq || "weekly",
        }),
      });
      setMsg(`${path} meta verisi kaydedildi`);
      setEditingPage(null);
      load();
      loadAudit();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function deletePage(path) {
    setErr(null);
    try {
      await api(`/api/admin/seo/pages${path}`, { method: "DELETE" });
      setMsg(`${path} meta verisi silindi`);
      load();
      loadAudit();
    } catch (e) {
      setErr(e.message);
    }
  }

  function startEditPost(p) {
    setEditingPost(p.slug);
    setPostForm({
      meta_description_tr: p.meta_description_tr || "",
      meta_description_en: p.meta_description_en || "",
      focus_keyword_tr: p.focus_keyword_tr || "",
      focus_keyword_en: p.focus_keyword_en || "",
      og_image: p.og_image || "",
      canonical_url: p.canonical_url || "",
      noindex: Boolean(p.noindex),
    });
  }

  async function savePost() {
    setErr(null);
    setMsg(null);
    try {
      await api(`/api/admin/seo/posts/${encodeURIComponent(editingPost)}`, {
        method: "PATCH",
        body: JSON.stringify({
          meta_description_tr: postForm.meta_description_tr || "",
          meta_description_en: postForm.meta_description_en || "",
          focus_keyword_tr: postForm.focus_keyword_tr || "",
          focus_keyword_en: postForm.focus_keyword_en || "",
          og_image: postForm.og_image || "",
          canonical_url: postForm.canonical_url || "",
          noindex: Boolean(postForm.noindex),
        }),
      });
      setMsg(`${editingPost} SEO verisi kaydedildi`);
      setEditingPost(null);
      load();
      loadAudit();
    } catch (e) {
      setErr(e.message);
    }
  }

  const issues = audit?.issues ?? [];
  const warnings = audit?.warnings ?? [];

  return (
    <>
      <div className="page-head">
        <div>
          <h2>SEO &amp; Pazarlama</h2>
          <p>
            Site haritaları, robots/llms.txt politikası, arama motoru doğrulaması, IndexNow,
            analytics ve reklam ağları tek yerden yönetilir.
          </p>
        </div>
        <button className="btn btn-primary" type="button" onClick={save} disabled={busy}>
          <Icon name="check" size={15} /> Kaydet
        </button>
      </div>

      {err && <p className="error">{err}</p>}
      {msg && <p className="ok-box">{msg}</p>}

      {/* ---------- audit ---------- */}
      <div className="card card-pad" style={{ marginTop: 18 }}>
        <div className="card-head">
          <div>
            <h3>SEO denetimi</h3>
            <p className="muted small">
              {audit ? `${audit.stats.posts} yazı · ${audit.stats.words} kelime · ${audit.site_url}` : "Yükleniyor…"}
            </p>
          </div>
          <div className="row">
            <span className={`badge ${audit?.score >= 80 ? "ok" : audit?.score >= 50 ? "warn" : "bad"}`}>
              Skor {audit?.score ?? "—"}
            </span>
            <span className="badge bad">{audit?.error_count ?? 0} hata</span>
            <span className="badge warn">{audit?.warning_count ?? 0} uyarı</span>
            <button className="btn btn-sm" type="button" onClick={loadAudit}>Yenile</button>
          </div>
        </div>

        {issues.length === 0 && warnings.length === 0 && (
          <p className="muted small">Sorun bulunamadı. Site arama motorları için hazır.</p>
        )}

        {issues.length > 0 && (
          <>
            <h4 style={{ margin: "14px 0 8px", fontSize: 14 }}>Hatalar</h4>
            <div className="table-wrap">
              <table className="tbl compact">
                <thead><tr><th>Kapsam</th><th>Referans</th><th>Sorun</th><th>Öneri</th></tr></thead>
                <tbody>
                  {issues.map((i, idx) => (
                    <tr key={`e${idx}`}>
                      <td><span className="badge bad">{i.scope}</span></td>
                      <td className="mono small">{i.ref}</td>
                      <td className="small">{i.message}</td>
                      <td className="small muted">{i.fix}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {warnings.length > 0 && (
          <>
            <h4 style={{ margin: "16px 0 8px", fontSize: 14 }}>Uyarılar</h4>
            <div className="table-wrap">
              <table className="tbl compact">
                <thead><tr><th>Kapsam</th><th>Referans</th><th>Uyarı</th><th>Öneri</th></tr></thead>
                <tbody>
                  {warnings.map((w, idx) => (
                    <tr key={`w${idx}`}>
                      <td><span className="badge warn">{w.scope}</span></td>
                      <td className="mono small">{w.ref}</td>
                      <td className="small">{w.message}</td>
                      <td className="small muted">{w.fix}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {(audit?.duplicate_pairs ?? []).length > 0 && (
          <>
            <h4 style={{ margin: "16px 0 8px", fontSize: 14 }}>Kopya içerik riski</h4>
            <div className="table-wrap">
              <table className="tbl compact">
                <thead><tr><th>Sayfa 1</th><th>Sayfa 2</th><th>Benzerlik</th><th>Tür</th></tr></thead>
                <tbody>
                  {audit.duplicate_pairs.map((d, idx) => (
                    <tr key={`d${idx}`}>
                      <td className="mono small">{d.left}</td>
                      <td className="mono small">{d.right}</td>
                      <td className="num">%{Math.round(d.similarity * 100)}</td>
                      <td className="small">{d.kind}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {/* ---------- site ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Site kimliği</h2><p>Kanonik alan adı, varsayılan meta açıklamalar ve paylaşım görseli.</p></div>
      </div>
      <div className="card card-pad">
        <div className="grid-2">
          <Field label="Site adı">
            <Text value={form.site_name} onChange={(v) => set("site_name", v)} />
          </Field>
          <Field label="Kanonik site URL" hint="Sitemap, IndexNow ve canonical adresleri bu değerden üretilir.">
            <Text value={form.site_url} onChange={(v) => set("site_url", v)} placeholder="https://app.example.com" />
          </Field>
          <Field label="Başlık son eki" hint="Sayfa başlığına otomatik eklenir.">
            <Text value={form.title_suffix} onChange={(v) => set("title_suffix", v)} />
          </Field>
          <Field label="OG / paylaşım görseli" hint="1200×630 önerilir.">
            <Text value={form.og_image} onChange={(v) => set("og_image", v)} placeholder="/og-image.png" />
          </Field>
          <Field label="Varsayılan açıklama (TR)">
            <Area value={form.default_description_tr} onChange={(v) => set("default_description_tr", v)} rows={3} />
          </Field>
          <Field label="Varsayılan açıklama (EN)">
            <Area value={form.default_description_en} onChange={(v) => set("default_description_en", v)} rows={3} />
          </Field>
          <Field label="Twitter site hesabı">
            <Text value={form.twitter_site} onChange={(v) => set("twitter_site", v)} placeholder="@socialsimulator" />
          </Field>
        </div>
      </div>

      {/* ---------- crawling ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Tarama ve AI erişimi</h2><p>robots.txt, llms.txt ve yapay zekâ tarayıcı politikası.</p></div>
      </div>
      <div className="card card-pad">
        <div className="grid-2">
          <Field label="İzin verilen AI botları" hint="Virgülle ayırın. Bu botlar her zaman Allow alır.">
            <Text value={form.allow_ai_bots} onChange={(v) => set("allow_ai_bots", v)} />
          </Field>
          <Field label="Ek robots.txt kuralları">
            <Area value={form.robots_extra} onChange={(v) => set("robots_extra", v)} rows={3} />
          </Field>
          <Field label="llms.txt ek notları" hint="LLM tarayıcılarına verilen ek bağlam.">
            <Area value={form.llms_txt} onChange={(v) => set("llms_txt", v)} rows={4} />
          </Field>
          <div className="field">
            <label>AI bot politikası</label>
            <Check
              checked={form.block_ai_bots}
              onChange={(v) => set("block_ai_bots", v)}
              label="AI tarayıcılarını tamamen engelle"
            />
            <div className="hint">
              Kapalıyken tüm AI botları wildcard kuralından serbestçe erişir. Açıkken izin
              listesinde olmayan bilinen AI botları <code>Disallow: /</code> alır.
            </div>
          </div>
        </div>
      </div>

      {/* ---------- verification ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Arama motoru doğrulaması</h2><p>Google Search Console ve Bing Webmaster için meta etiket değerleri.</p></div>
      </div>
      <div className="card card-pad">
        <div className="grid-2">
          <Field label="Google site doğrulama">
            <Text value={form.google_site_verification} onChange={(v) => set("google_site_verification", v)} />
          </Field>
          <Field label="Bing site doğrulama">
            <Text value={form.bing_site_verification} onChange={(v) => set("bing_site_verification", v)} />
          </Field>
        </div>
      </div>

      {/* ---------- indexnow ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>IndexNow</h2><p>Yeni/değişen sayfaları Bing, Yandex ve destekleyen motorlara anında bildirir.</p></div>
      </div>
      <div className="card card-pad">
        <div className="grid-2">
          <Field label="IndexNow anahtarı" hint={`Anahtar kök dizinde /${form.indexnow_key || "<anahtar>"}.txt olarak sunulur.`}>
            <Text value={form.indexnow_key} onChange={(v) => set("indexnow_key", v)} />
          </Field>
          <Field label="IndexNow endpoint">
            <Text value={form.indexnow_endpoint} onChange={(v) => set("indexnow_endpoint", v)} />
          </Field>
        </div>
        <div className="row" style={{ marginTop: 10 }}>
          <Check checked={form.indexnow_enabled} onChange={(v) => set("indexnow_enabled", v)} label="IndexNow aktif" />
          <button className="btn btn-sm" type="button" onClick={regenerateKey}>Anahtar üret</button>
          <button className="btn btn-sm" type="button" onClick={() => submitIndexNow(true)} disabled={busy || !form.indexnow_enabled}>
            Tüm sayfaları gönder
          </button>
        </div>

        <h4 style={{ margin: "18px 0 8px", fontSize: 14 }}>Gönderim geçmişi</h4>
        <div className="table-wrap">
          <table className="tbl compact">
            <thead><tr><th>Zaman</th><th>URL</th><th>Durum</th><th>Detay</th></tr></thead>
            <tbody>
              {log.map((l) => (
                <tr key={l.id}>
                  <td className="small">{new Date(l.created_at).toLocaleString("tr-TR")}</td>
                  <td className="mono small">{l.url}</td>
                  <td><span className={`badge ${l.status === "ok" ? "ok" : "bad"}`}>{l.status}</span></td>
                  <td className="small muted">{l.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {log.length === 0 && <div style={{ padding: 14 }}><p className="muted small">Henüz gönderim yok.</p></div>}
        </div>
      </div>

      {/* ---------- analytics / ads ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Analytics ve reklam ağları</h2><p>Kod yeniden derlenmeden çalışma zamanında etkinleştirilir.</p></div>
      </div>
      <div className="card card-pad">
        <div className="grid-2">
          <Field label="Analytics sağlayıcısı">
            <select className="select" value={form.analytics_provider} onChange={(e) => set("analytics_provider", e.target.value)}>
              <option value="gtag">Google Analytics 4 (gtag.js)</option>
              <option value="plausible">Plausible</option>
              <option value="custom">Özel kod (aşağıdaki kutu)</option>
            </select>
          </Field>
          {form.analytics_provider === "plausible" ? (
            <Field label="Plausible domain" hint="Örn: app.socialsimulator.com.tr">
              <Text value={form.analytics_domain} onChange={(v) => set("analytics_domain", v)} />
            </Field>
          ) : (
            <Field
              label="Ölçüm kimliği (measurement ID)"
              hint={
                detectedId
                  ? `Yapıştırılan koddan algılandı: ${detectedId}`
                  : "G-XXXXXXXXXX biçiminde. Kod yapıştırılırsa otomatik doldurulur."
              }
            >
              <Text value={form.analytics_id} onChange={(v) => set("analytics_id", v)} placeholder="G-S9Z3Y1VYP5" />
            </Field>
          )}
        </div>

        <Field
          label="Analytics kodu (gtag etiketi)"
          hint="Google veya Plausible'ın verdiği kodu olduğu gibi buraya yapıştırın. <script> etiketi dahil tamamını kabul eder; measurement ID otomatik algılanır."
        >
          <Area
            value={form.analytics_code}
            onChange={(v) => {
              set("analytics_code", v);
              const found = detectMeasurementId(v);
              if (found) {
                set("analytics_id", found);
                if (form.analytics_provider !== "plausible") set("analytics_provider", "gtag");
              }
            }}
            rows={7}
            placeholder={'<!-- Google tag (gtag.js) -->\n<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>\n<script>\n  window.dataLayer = window.dataLayer || [];\n  function gtag(){dataLayer.push(arguments);}\n  gtag(\'js\', new Date());\n  gtag(\'config\', \'G-XXXXXXXXXX\');\n</script>'}
          />
        </Field>

        {form.analytics_code && !detectedId && !form.analytics_domain && (
          <p className="notice" style={{ marginTop: 4 }}>
            Yapıştırılan koddan bir measurement ID algılanamadı. Kod yalnızca <code>G-...</code> biçiminde
            bir kimlikse, yukarıdaki alana elle yazın.
          </p>
        )}

        <div className="row" style={{ marginTop: 10 }}>
          <Check checked={form.analytics_enabled} onChange={(v) => set("analytics_enabled", v)} label="Analytics aktif" />
          <Check checked={form.ads_enabled} onChange={(v) => set("ads_enabled", v)} label="Reklamlar aktif" />
        </div>

        <h4 style={{ margin: "20px 0 8px", fontSize: 14 }}>Reklam ağı (AdSense)</h4>
        <div className="grid-2">
          <Field label="AdSense yayıncı kimliği" hint="ca-pub-XXXXXXXXXXXXXXXX">
            <Text value={form.adsense_client} onChange={(v) => set("adsense_client", v)} />
          </Field>
          <Field label="AdSense slot (birincil)">
            <Text value={form.adsense_slot} onChange={(v) => set("adsense_slot", v)} />
          </Field>
          <Field label="AdSense slot (ikincil)">
            <Text value={form.adsense_slot_secondary} onChange={(v) => set("adsense_slot_secondary", v)} />
          </Field>
        </div>
      </div>

      {/* ---------- analytics events ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div>
          <h2>Analytics olayları</h2>
          <p>
            Üyelik ve satın alma olayları GA4&apos;e gönderilmek üzere kuyruğa alınır; tarayıcı
            gönderdikten sonra &quot;iletildi&quot; işaretlenir.
          </p>
        </div>
        <button className="btn btn-sm" type="button" onClick={loadEvents}>Yenile</button>
      </div>
      <div className="card card-pad" style={{ marginBottom: 14 }}>
        <div className="row">
          {eventCounts.map((c) => (
            <span key={c.name} className="badge">{c.name}: {c.count}</span>
          ))}
          {eventCounts.length === 0 && <span className="muted small">Henüz olay yok.</span>}
        </div>
      </div>
      <div className="card table-wrap">
        <table className="tbl compact">
          <thead>
            <tr><th>Zaman</th><th>Olay</th><th>Kaynak</th><th>Değer</th><th>Parametreler</th><th>Durum</th></tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td className="small">{e.created_at ? new Date(e.created_at).toLocaleString("tr-TR") : "—"}</td>
                <td className="mono small">{e.name}</td>
                <td className="small">{e.source}</td>
                <td className="num small">
                  {e.value != null ? `${e.value} ${e.currency ?? ""}` : "—"}
                </td>
                <td className="small muted" style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }}>
                  {JSON.stringify(e.params ?? {})}
                </td>
                <td>
                  {e.delivered
                    ? <span className="badge ok">iletildi</span>
                    : <span className="badge warn">bekliyor</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {events.length === 0 && <div style={{ padding: 16 }}><p className="muted small">Kayıt bulunamadı.</p></div>}
      </div>

      {/* ---------- static pages ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Statik sayfa meta verileri</h2><p>Ana sayfa ve blog listesi için başlık, açıklama ve indeksleme durumu.</p></div>
        <button className="btn btn-sm" type="button" onClick={() => startEditPage(null)}>
          <Icon name="plus" size={14} /> Sayfa ekle
        </button>
      </div>
      <div className="card table-wrap">
        <table className="tbl">
          <thead><tr><th>Yol</th><th>Başlık (TR)</th><th>Açıklama (TR)</th><th>Öncelik</th><th>İndeks</th><th>İşlem</th></tr></thead>
          <tbody>
            {staticPages.map((sp) => {
              const ov = pages.find((p) => p.path === sp.path);
              return (
                <tr key={sp.path}>
                  <td className="mono">{sp.path}</td>
                  <td>{ov?.title_tr || <span className="muted small">varsayılan</span>}</td>
                  <td className="small">{ov?.description_tr || <span className="muted small">varsayılan</span>}</td>
                  <td className="num">{ov ? Number(ov.sitemap_priority).toFixed(2) : sp.priority}</td>
                  <td>{ov?.noindex ? <span className="badge">noindex</span> : <span className="badge ok">index</span>}</td>
                  <td className="num">
                    <button className="btn btn-sm" type="button" onClick={() => startEditPage(ov ?? { path: sp.path })}>Düzenle</button>
                  </td>
                </tr>
              );
            })}
            {pages.filter((p) => !staticPages.some((sp) => sp.path === p.path)).map((p) => (
              <tr key={p.path}>
                <td className="mono">{p.path}</td>
                <td>{p.title_tr || <span className="muted small">—</span>}</td>
                <td className="small">{p.description_tr || <span className="muted small">—</span>}</td>
                <td className="num">{Number(p.sitemap_priority).toFixed(2)}</td>
                <td>{p.noindex ? <span className="badge">noindex</span> : <span className="badge ok">index</span>}</td>
                <td className="num">
                  <button className="btn btn-sm" type="button" onClick={() => startEditPage(p)}>Düzenle</button>{" "}
                  <button className="btn btn-sm" type="button" onClick={() => deletePage(p.path)}>Sil</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editingPage && (
        <div className="card card-pad" style={{ marginTop: 14 }}>
          <div className="grid-2">
            <Field label="Yol">
              <Text value={pageForm.path} onChange={(v) => setPageForm({ ...pageForm, path: v })} placeholder="/pricing" />
            </Field>
            <Field label="Odak anahtar kelime">
              <Text value={pageForm.focus_keyword} onChange={(v) => setPageForm({ ...pageForm, focus_keyword: v })} />
            </Field>
            <Field label="Başlık (TR)">
              <Text value={pageForm.title_tr} onChange={(v) => setPageForm({ ...pageForm, title_tr: v })} />
            </Field>
            <Field label="Başlık (EN)">
              <Text value={pageForm.title_en} onChange={(v) => setPageForm({ ...pageForm, title_en: v })} />
            </Field>
            <Field label="Açıklama (TR)">
              <Area value={pageForm.description_tr} onChange={(v) => setPageForm({ ...pageForm, description_tr: v })} rows={2} />
            </Field>
            <Field label="Açıklama (EN)">
              <Area value={pageForm.description_en} onChange={(v) => setPageForm({ ...pageForm, description_en: v })} rows={2} />
            </Field>
            <Field label="OG görseli">
              <Text value={pageForm.og_image} onChange={(v) => setPageForm({ ...pageForm, og_image: v })} />
            </Field>
            <Field label="Canonical URL">
              <Text value={pageForm.canonical_url} onChange={(v) => setPageForm({ ...pageForm, canonical_url: v })} />
            </Field>
            <Field label="Sitemap önceliği (0-1)">
              <Text
                type="number"
                value={pageForm.sitemap_priority}
                onChange={(v) => setPageForm({ ...pageForm, sitemap_priority: v })}
              />
            </Field>
            <Field label="Sitemap değişim sıklığı">
              <select className="select" value={pageForm.changefreq} onChange={(e) => setPageForm({ ...pageForm, changefreq: e.target.value })}>
                {["always", "hourly", "daily", "weekly", "monthly", "yearly", "never"].map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </Field>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <Check checked={pageForm.noindex} onChange={(v) => setPageForm({ ...pageForm, noindex: v })} label="noindex" />
            <span style={{ flex: 1 }} />
            <button className="btn" type="button" onClick={() => setEditingPage(null)}>Vazgeç</button>
            <button className="btn btn-primary" type="button" onClick={savePage}>Kaydet</button>
          </div>
        </div>
      )}

      {/* ---------- blog posts ---------- */}
      <div className="page-head" style={{ marginTop: 26 }}>
        <div><h2>Blog yazıları</h2><p>Yazı başına meta açıklama, odak kelime, OG görseli ve indeksleme durumu.</p></div>
      </div>
      <div className="card table-wrap">
        <table className="tbl">
          <thead><tr><th>Slug</th><th>Başlık</th><th>Odak kelime</th><th>Meta (TR)</th><th>Durum</th><th>İşlem</th></tr></thead>
          <tbody>
            {posts.map((p) => (
              <tr key={p.slug}>
                <td className="mono small">{p.slug}</td>
                <td className="small">{p.title_tr}</td>
                <td className="small">{p.focus_keyword_tr || <span className="muted">—</span>}</td>
                <td className="small">{(p.meta_description_tr || "").slice(0, 60) || <span className="muted">—</span>}</td>
                <td>
                  {p.noindex
                    ? <span className="badge">noindex</span>
                    : p.is_published
                      ? <span className="badge ok">yayında</span>
                      : <span className="badge warn">taslak</span>}
                </td>
                <td className="num">
                  <button className="btn btn-sm" type="button" onClick={() => startEditPost(p)}>Düzenle</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {posts.length === 0 && <div style={{ padding: 18 }}><p className="muted small">Blog yazısı yok.</p></div>}
      </div>

      {editingPost && (
        <div className="card card-pad" style={{ marginTop: 14 }}>
          <h3 className="mono" style={{ marginBottom: 12 }}>{editingPost}</h3>
          <div className="grid-2">
            <Field label="Meta açıklama (TR)">
              <Area value={postForm.meta_description_tr} onChange={(v) => setPostForm({ ...postForm, meta_description_tr: v })} rows={2} />
            </Field>
            <Field label="Meta açıklama (EN)">
              <Area value={postForm.meta_description_en} onChange={(v) => setPostForm({ ...postForm, meta_description_en: v })} rows={2} />
            </Field>
            <Field label="Odak kelime (TR)">
              <Text value={postForm.focus_keyword_tr} onChange={(v) => setPostForm({ ...postForm, focus_keyword_tr: v })} />
            </Field>
            <Field label="Odak kelime (EN)">
              <Text value={postForm.focus_keyword_en} onChange={(v) => setPostForm({ ...postForm, focus_keyword_en: v })} />
            </Field>
            <Field label="OG görseli">
              <Text value={postForm.og_image} onChange={(v) => setPostForm({ ...postForm, og_image: v })} />
            </Field>
            <Field label="Canonical URL">
              <Text value={postForm.canonical_url} onChange={(v) => setPostForm({ ...postForm, canonical_url: v })} />
            </Field>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <Check checked={postForm.noindex} onChange={(v) => setPostForm({ ...postForm, noindex: v })} label="noindex" />
            <span style={{ flex: 1 }} />
            <button className="btn" type="button" onClick={() => setEditingPost(null)}>Vazgeç</button>
            <button className="btn btn-primary" type="button" onClick={savePost}>Kaydet</button>
          </div>
        </div>
      )}
    </>
  );
}
