import { Link } from "react-router-dom";

import Icon from "../icons.jsx";

export default function Reports() {
  return (
    <>
      <div className="page-head"><div><h2>Raporlar</h2><p>Tamamlanan simülasyonların kaynakçalı analiz çıktıları.</p></div></div>

      <div className="notice"><Icon name="bell" size={15} /><span>Her raporun üstünde kalıcı simülasyon ibaresi bulunur; çıktılar gerçek anket/kamuoyu ölçümü olarak sunulamaz.</span></div>

      <div className="empty"><span className="empty-icon"><Icon name="doc" size={22} /></span>
        <h3>Rapor kütüphanesi yakında</h3>
        <p>Rapor ajanı (outline → bölümler → Markdown/PDF) sonraki fazda devreye alınacak. O zamana kadar simülasyon durumlarını “Simülasyonlar” ekranından takip edebilirsiniz.</p>
        <Link className="btn btn-primary" to="/app/runs"><Icon name="activity" size={15} /> Simülasyonlara git</Link>
      </div>
    </>
  );
}
