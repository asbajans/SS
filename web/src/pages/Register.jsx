import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { register } from "../api.js";
import Icon from "../icons.jsx";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await register(email, password);
      nav(sessionStorage.getItem("ss_prompt") ? "/app/projects/new" : "/app");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  }

  return (
    <div className="auth-wrap">
      <aside className="auth-side">
        <Link className="brand" to="/" aria-label="Social Simulator">
          <img src="/logo-light.png" alt="Social Simulator" />
        </Link>
        <div className="stack" style={{ gap: 24 }}>
          <h2>Ücretsiz planla başlayın — ilk simülasyonunuzu hemen çalıştırın.</h2>
          <ul>
            <li><Icon name="check" size={17} /> <span>Aylık 1M token kredisi ve 50 ajana kadar simülasyon</span></li>
            <li><Icon name="check" size={17} /> <span>Altı hazır araştırma şablonu (pazar, kamuoyu, fiyat, politika, konsept, kurgusal dünya)</span></li>
            <li><Icon name="check" size={17} /> <span>Kaynakçalı rapor çıktısı ve simülasyon etiketi</span></li>
          </ul>
        </div>
        <p className="small" style={{ color: "#64748b" }}>
          Tüm çıktılar simülasyon ürünüdür; gerçek anket veya kamuoyu ölçümü değildir.
        </p>
      </aside>

      <div className="auth-form-col">
        <div className="auth-card">
          <h1>Hesap oluşturun</h1>
          <p className="text-2" style={{ marginTop: 6, fontSize: 14 }}>
            E-posta ve şifre yeterli; kart bilgisi gerektirmez.
          </p>
          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email">E-posta</label>
              <input id="email" className="input" type="email" autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="ad@sirket.com" />
            </div>
            <div className="field">
              <label htmlFor="password">Şifre</label>
              <input id="password" className="input" type="password" autoComplete="new-password"
                value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} placeholder="••••••••" />
            </div>
            {error && <p className="error" style={{ marginBottom: 12 }}>{error}</p>}
            <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
              {busy ? "Hesap oluşturuluyor…" : "Hesap oluştur"}
            </button>
          </form>
          <p className="small muted" style={{ textAlign: "center" }}>
            Zaten hesabınız var mı?{" "}
            <Link to="/login" style={{ color: "var(--primary-600)", fontWeight: 600 }}>
              Giriş yapın
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
