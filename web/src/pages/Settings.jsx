import { useOutletContext } from "react-router-dom";

import { fmtDate, logout } from "../api.js";
import Icon from "../icons.jsx";

export default function Settings() {
  const user = useOutletContext();

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
            Simülasyon tamamlandığında e-posta bildirimi ve veri silme (DSR) talepleri sonraki fazlarda bu bölümden yönetilecek.
          </p>
          <div className="notice"><Icon name="shield" size={15} /><span>Verileriniz yalnızca kendi altyapımızda saklanır; kişisel veri üçüncü taraflara satılmaz veya reklam amacıyla kullanılmaz.</span></div>
        </div>
      </div>
    </>
  );
}
