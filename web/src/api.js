const BASE = import.meta.env.VITE_API_URL ?? "";

export async function login(email, password) {
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? "giriş başarısız");
  const data = await r.json();
  localStorage.setItem("crowdscope_token", data.token);
  return data;
}

export async function api(path, opts = {}) {
  const token = localStorage.getItem("crowdscope_token");
  const r = await fetch(`${BASE}${path}`, {
    ...opts,
    headers: {
      "content-type": "application/json",
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...(opts.headers ?? {}),
    },
  });
  if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText);
  return r.json();
}
