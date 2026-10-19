import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { login, register } from "../api.js";
import Icon from "../icons.jsx";

const BULLETS = [
  "Yüzlerce sentetik ajan; kişilik, hafıza ve davranış mantığıyla",
  "Pazar, kamuoyu, fiyat, politika ve kurgusal dünya şablonları",
  "Olay kayıtlarına dayalı, simülasyon etiketli kaynakçalı raporlar",
  "Verileriniz yalnızca sizin altyapınızda; dış bağımlılık minimum",
];

export default function Login({ mode = "login" }) {
  const isReg = mode === "register";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isReg) await register(email, password);
      else await login(email, password);
      nav("/app");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <aside className="auth-side">
        <div className="brand" style={{ padding: 0 }}>
          <span className="brand-mark">CS</span>
          <span className="brand-name">CrowdScope</span>
        </div>
        <div className="stack" style={{ gap: 22 }}>
          <h2>Topluluk araştırmasını simülasyonla yapın — saha olmadan, hızlı ve tekrarlanabilir.</h2>
          <ul>
            {BULLETS.map((b) => (
              <li key={b}><Icon name="check" size={17} /> <span>{b}</span></li>
            ))}
          </ul>
        </div>
        <p className="small" style={{ color: "#64748b" }}>
          Tüm çıktılar simülasyon ürünüdür; gerçek kamuoyu ölçümü değildir.
        </p>
      </aside>

      <div className="auth-form-col">
        <div className="auth-card">
          <div className="auth-tabs">
            <Link to="/login" className={!isReg ? "active" : ""}>Giriş</Link>
            <Link to="/register" className={isReg ? "active" : ""}>Kayıt</Link>
          </div>
          <div>
            <h1>{isReg ? "Hesap oluştur" : "Tekrar hoş geldiniz"}</h1>
            <p className="text-2" style={{ marginTop: 6, fontSize: 14 }}>
              {isReg
                ? "Ücretsiz planla ilk simülasyonunuzu hemen çalıştırın."
                : "Simülasyon panelinize devam etmek için giriş yapın."}
            </p>
          </div>
          <form onSubmit={submit}>
            <div className="field">
              <label htmlFor="email">E-posta</label>
              <input
                id="email" className="input" type="email" autoComplete="email"
                value={email} onChange={(e) => setEmail(e.target.value)} required
                placeholder="ad@sirket.com"
              />
            </div>
            <div className="field">
              <label htmlFor="password">Şifre</label>
              <input
                id="password" className="input" type="password"
                autoComplete={isReg ? "new-password" : "current-password"}
                value={password} onChange={(e) => setPassword(e.target.value)}
                required minLength={6}
                placeholder="••••••••"
              />
            </div>
            {error && <p className="error" style={{ marginBottom: 12 }}>{error}</p>}
            <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
              {busy ? "Bekleyin…" : isReg ? "Hesap oluştur" : "Giriş yap"}
            </button>
          </form>
          <p className="small muted" style={{ textAlign: "center" }}>
            Devam ederek Kullanım Şartları ve Gizlilik Bildirimi&apos;ni kabul etmiş olursunuz.
          </p>
        </div>
      </div>
    </div>
  );
}
