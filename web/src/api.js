const BASE = import.meta.env.VITE_API_URL ?? "";

export function getToken() {
  return localStorage.getItem("ss_token");
}

export function setToken(t) {
  localStorage.setItem("ss_token", t);
}

export function clearToken() {
  localStorage.removeItem("ss_token");
}

async function request(path, opts = {}) {
  const token = getToken();
  const r = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      ...(opts.body ? { "content-type": "application/json" } : {}),
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });
  if (r.status === 401 && !path.includes("/auth/")) {
    clearToken();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("Oturum süresi doldu");
  }
  let data = null;
  try {
    data = await r.json();
  } catch {
    /* no body */
  }
  if (!r.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Hata ${r.status}`);
  }
  return data;
}

export function api(path, opts = {}) {
  return request(path, opts);
}

export async function login(email, password) {
  const data = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.token);
  return data;
}

export async function register(email, password) {
  const data = await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(data.token);
  return data;
}

export function logout() {
  clearToken();
  window.location.href = "/login";
}

export const TEMPLATES = [
  { key: "market_research", name: "Pazar Araştırması", desc: "Segmentler, rakipler ve fiyat algısı üzerine sentetik tüketici topluluğu." },
  { key: "public_opinion", name: "Kamuoyu & Kriz", desc: "Bir mesele etrafında söylem, güven ve yayılım dinamiklerini simüle edin." },
  { key: "concept_test", name: "Ürün Konsepti", desc: "Özellik önceliklendirme ve JTBD için sanal kullanıcı yorumları." },
  { key: "price_probe", name: "Fiyat Testi", desc: "Ödeme isteği eğrileri ve fiyat kancası tepkilerini ölçün." },
  { key: "policy_review", name: "Politika & Düzenleme", desc: "Paydaş tepkileri, destek–itiraz dengesi ve çatışma haritası." },
  { key: "fiction_review", name: "Kurgusal Dünya", desc: "Karakter tutarlılığı, ilişki dinamikleri ve topluluk tepkisi." },
];

export const PROFILES = [
  { key: "fast", name: "Hızlı", agents_n: 80, rounds: 24, platforms: 1, cost: "~$0,10–0,35", hint: "Hızlı sinyal taraması" },
  { key: "std", name: "Standart", agents_n: 150, rounds: 40, platforms: 2, cost: "~$0,45–1,40", hint: "Önerilen denge" },
  { key: "deep", name: "Derin", agents_n: 250, rounds: 72, platforms: 2, cost: "~$1,15–3,60", hint: "Yüksek derinlik" },
];

export const STAGES = [
  { key: "pending", label: "Kuyrukta" },
  { key: "ingesting", label: "Belge işleme" },
  { key: "ontology", label: "Ontoloji çıkarımı" },
  { key: "population", label: "Ajan popülasyonu" },
  { key: "running", label: "Simülasyon turları" },
  { key: "report", label: "Rapor üretimi" },
  { key: "completed", label: "Tamamlandı" },
];

export const ACTIVE_STATUSES = ["pending", "ingesting", "ontology", "population", "running", "report"];

export function stageIndex(status) {
  const i = STAGES.findIndex((s) => s.key === status);
  return i === -1 ? 0 : i;
}

export function fmtTokens(n) {
  if (n == null) return "0";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function fmtCost(c) {
  const v = Number(c ?? 0);
  return `$${v.toFixed(v >= 1 ? 2 : 4)}`;
}

export function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

export function shortId(id) {
  return id ? String(id).slice(0, 8) : "—";
}

export async function uploadDocument(projectId, file) {
  const token = getToken();
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${BASE}/api/projects/${projectId}/documents`, {
    method: "POST",
    headers: token ? { authorization: `Bearer ${token}` } : {},
    body: fd,
  });
  const data = await r.json().catch(() => null);
  if (!r.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Hata ${r.status}`);
  }
  return data;
}

export async function streamRunEvents(runId, { onStatus, onEvent, signal } = {}) {
  const token = getToken();
  const r = await fetch(`${BASE}/api/runs/${runId}/events/stream`, {
    headers: token ? { authorization: `Bearer ${token}` } : {},
    signal,
  });
  if (!r.ok || !r.body) throw new Error(`SSE Hata ${r.status}`);
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      let evt = "message";
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event: ")) evt = line.slice(7).trim();
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue;
      let parsed;
      try { parsed = JSON.parse(data); } catch { continue; }
      if (evt === "status") onStatus?.(parsed);
      else if (evt === "run_event") onEvent?.(parsed);
      else if (evt === "end") return;
    }
  }
}
