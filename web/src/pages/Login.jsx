import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login } from "../api.js";
import { flushServerEvents, trackEvent } from "../analytics.js";
import GoogleAuth from "../components/GoogleAuth.jsx";
import Icon from "../icons.jsx";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await login(email, password);
      trackEvent("login", { signup_method: "email", method: "email" });
      flushServerEvents();
      nav("/app");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  const onGoogleSuccess = useCallback((data) => {
    const method = data?.signup_method || "google";
    trackEvent(data?.is_new ? "sign_up" : "login", {
      signup_method: method,
      method,
      plan: "free",
    });
    flushServerEvents();
    nav(sessionStorage.getItem("ss_prompt") ? "/app/projects/new" : "/app");
  }, [nav]);

  const onGoogleError = useCallback((err) => {
    setError(err.message);
  }, []);

  return (
    <div className="auth-wrap">
      <aside className="auth-side">
        <Link className="brand" to="/" aria-label="Social Simulator">
          <img src="/logo-light.png" alt="Social Simulator" />
        </Link>
        <div className="stack" style={{ gap: 24 }}>
          <h2>Topluluk araştırmasını simülasyonla yapın — saha olmadan, hızlı ve tekrarlanabilir.</h2>
          <ul>
            <li><Icon name="check" size={17} /> <span>Yüzlerce sentetik ajan; kişilik, hafıza ve davranış mantığıyla</span></li>
            <li><Icon name="check" size={17} /> <span>Pazar, kamuoyu, fiyat, politika ve kurgusal dünya şablonları</span></li>
            <li><Icon name="check" size={17} /> <span>Olay kayıtlarına dayalı, simülasyon etiketli kaynakçalı raporlar</span></li>
            <li><Icon name="check" size={17} /> <span>Verileriniz yalnızca sizin altyapınızda; dış bağımlılık minimum</span></li>
          </ul>
        </div>
        <p className="small" style={{ color: "#64748b" }}>
          Tüm çıktılar simülasyon ürünüdür; gerçek kamuoyu ölçümü değildir.
        </p>
      </aside>

      <div className="auth-form-col">
        <div className="auth-card">
          <h1>Giriş yapın</h1>
          <p className="text-2" style={{ marginTop: 6, fontSize: 14 }}>
            Simülasyon panelinize devam etmek için giriş yapın.
          </p>
          <GoogleAuth onSuccess={onGoogleSuccess} onError={onGoogleError} lang="tr" />
          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email">E-posta</label>
              <input id="email" className="input" type="email" autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="ad@sirket.com" />
            </div>
            <div className="field">
              <label htmlFor="password">Şifre</label>
              <input id="password" className="input" type="password" autoComplete="current-password"
                value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} placeholder="••••••••" />
            </div>
            {error && <p className="error" style={{ marginBottom: 12 }}>{error}</p>}
            <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
              {busy ? "Giriş yapılıyor…" : "Giriş yap"}
            </button>
          </form>
          <p className="small muted" style={{ textAlign: "center" }}>
            Henüz hesabınız yok mu?{" "}
            <Link to="/register" style={{ color: "var(--primary-600)", fontWeight: 600 }}>
              Kayıt olun
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
