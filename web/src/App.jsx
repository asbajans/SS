import { useState } from "react";
import { Link } from "react-router-dom";

export default function App() {
  const [email, setEmail] = useState("");
  return (
    <main className="container">
      <h1>CrowdScope</h1>
      <p className="muted">
        Konu ve senaryonuza göre sentetik topluluk simülasyonu: pazar, kamuoğlu, ürün,
        fiyat, politika veya kurgusal dünyalar — hepsi yerel altyapıda, dışa bağımlılık minimum.
      </p>
      <p className="muted small">
        Bu arayüz örnek bir iskele; tam ürün Faz 4-5'te gelir (bkz. agent.md).
      </p>
      <div className="actions">
        <Link to="/login">Giriş</Link>
        <Link to="/projects">Projeler</Link>
      </div>
      <footer>
        <label>
          <input
            type="email"
            placeholder="bülten e-posta"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <button type="button">Bekleme listesine ekle</button>
        </label>
      </footer>
    </main>
  );
}
