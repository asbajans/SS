import { useState } from "react";
import { useOutletContext } from "react-router-dom";

import { api, logout } from "../api.js";
import Icon from "../icons.jsx";

export default function Settings() {
  const user = useOutletContext();
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [requested, setRequested] = useState(false);

  async function requestDeletion() {
    setBusy(true);
    setError(null);
    try {
      await api("/api/privacy/requests", { method: "POST" });
      setRequested(true);
      setTimeout(() => logout(), 2500);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head"><div><h2>Ayarlar</h2><p>Hesap bilgileri ve oturum yönetimi.</p></div></div>

      <div className="grid-2">
        <div className="card card-pad stack">
          <h3>Hesap</h3>
          <dl className="kv">
            <dt>E-posta</dt><dd>{user?.email}</dd>
            <dt>Plan</dt><dd style={{ textTransform: "capitalize" }}>{user?.plan ?? "free"}</dd>
            <dt>Yönetici</dt><dd>{user?.is_admin ? "Evet" : "Hayır"}</dd>
            <dt>Kullanıcı ID</dt><dd className="mono small">{user?.id}</dd>
          </dl>
          <div className="row"><button className="btn btn-danger" type="button" onClick={logout}><Icon name="logout" size={15} /> Oturumu kapat</button></div>
        </div>

        <div className="card card-pad stack">
          <h3>Bildirimler &amp; veri</h3>
          <p className="text-2" style={{ fontSize: 13.5 }}>
            Simülasyon tamamlandığında e-posta bildirimi sonraki fazda eklenecek. Veri silme (DSR)
            talebinizi aşağıdan hemen oluşturabilirsiniz.
          </p>
          <div className="notice"><Icon name="shield" size={15} /><span>Verileriniz yalnızca kendi altyapımızda saklanır; kişisel veri üçüncü taraflara satılmaz veya reklam amacıyla kullanılmaz.</span></div>

          <div style={{ borderTop: "1px solid var(--line, #e5e7eb)", paddingTop: 14, marginTop: 4 }}>
            <h4 style={{ color: "#b91c1c" }}>Hesabı ve verileri sil</h4>
            <p className="small muted">
              Bu işlem geri alınamaz: hesabınız, projeleriniz, belgeleriniz, ajanlarınız, simülasyon
              olayları/raporları ve depolama dosyalarınız silinir; token kullanım kayıtları kişiye
              bağlanamaz hale getirilir.
            </p>
            {requested ? (
              <p className="ok-box">Silme talebiniz alındı; oturumunuz kapatılıyor.</p>
            ) : (
              <>
                <div className="field">
                  <label htmlFor="confirmdel">Onay için SİL yazın</label>
                  <input id="confirmdel" className="input" value={confirm} placeholder="SİL" onChange={(e) => setConfirm(e.target.value)} />
                </div>
                {error && <p className="error">{error}</p>}
                <div className="row">
                  <button className="btn btn-danger" type="button" disabled={busy || confirm.trim().toLocaleUpperCase("tr-TR") !== "SİL"} onClick={requestDeletion}>
                    <Icon name="shield" size={15} /> {busy ? "Gönderiliyor…" : "Hesabımı ve verilerimi sil"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
