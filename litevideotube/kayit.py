"""Programın kendi kayıtları: izleme geçmişi ve videoların kaldığı yer (tek SQLite dosyası).

Yer: Linux'ta ~/.local/share/LiteVideoTube/kayit.db, Windows'ta %APPDATA%/LiteVideoTube/kayit.db.
Denemelerde LVT_VERI ile başka klasör verilir (gerçek kayıtlar bozulmasın).
"""
import json
import os
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from . import bicim, yoklama
from .ceviri import tr

# Videonun başı ve sonu kaldığı yer sayılmaz: başta kalan baştan açılır, sona yakın olan bitmiş sayılır.
BAS_PAYI = 10.0
SON_PAYI = 15.0
# Geçmişte bir videonun son kaç izlenişinin zamanı tutulur (28 Ekim: en yakın 2-3 kayıt, saatleri yanlarında).
# Yarım saat içinde yeniden açılan aynı izleniş sayılır (yalnız saati güncellenir).
IZLENIS_SAYISI = 3
AYNI_IZLENIS_SN = 30 * 60
def veri_klasoru():
    # Arka plan yoklaması (Qt'siz) aynı dosyayı bulsun diye yer tek yerde: yoklama.py (Qt'nin
    # GenericDataLocation'ıyla aynı klasör).
    return yoklama.veri_klasoru()


def izlenis_yazisi(zamanlar, son, bugun):
    """Son izlenişler, en yenisi önde: bugün yalnız saat ("22:25"), dün "Dün 14:02", son bir haftada gün adı
    ("Cuma 09:15"), daha eskisi tarih ("12 Ekim 09:15"). Gün ve ay adları, saat biçimi ekran dilinde (bicim)."""
    try:
        l = json.loads(zamanlar) if zamanlar else []
    except ValueError:
        l = []
    if not l and son:
        l = [son]
    parcalar = []
    for z in l:
        t = datetime.fromtimestamp(z)
        fark = (bugun - t.date()).days
        saat = bicim.saat(t)
        if fark == 0:
            parcalar.append(saat)
        elif fark == 1:
            parcalar.append(tr("Dün %1").replace("%1", saat))
        elif 1 < fark < 7:
            parcalar.append(bicim.gun_adi(t) + " " + saat)
        else:
            parcalar.append(bicim.gun_ay(t, t.year != bugun.year) + " " + saat)
    return "  ·  ".join(parcalar)


class Kayit(QObject):
    gecmisDegisti = Signal()
    konumlarDegisti = Signal()

    def __init__(self):
        super().__init__()
        klasor = veri_klasoru()
        klasor.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(klasor / "kayit.db"), timeout=10)
        self.db.execute("PRAGMA synchronous=NORMAL")   # kaldığı yer sık yazılıyor; her yazışta fsync yok (yoklama.baglan)
        self.db.execute("""CREATE TABLE IF NOT EXISTS gecmis (
            id TEXT PRIMARY KEY, baslik TEXT, kanal TEXT, kanal_id TEXT, sure_yazi TEXT,
            sure REAL DEFAULT 0, konum REAL DEFAULT 0, son REAL)""")
        # Son izlenişlerin zamanı (JSON, en yenisi önde); eski kayıtlarda yalnız son açılış biliniyor.
        if "zamanlar" not in [r[1] for r in self.db.execute("PRAGMA table_info(gecmis)")]:
            self.db.execute("ALTER TABLE gecmis ADD COLUMN zamanlar TEXT")
            self.db.execute("UPDATE gecmis SET zamanlar = '[' || son || ']' WHERE son IS NOT NULL")
        # Kullanıcının seçtiği ayarlar (ör. görünüm menüsü); program kapanınca da unutulmaz.
        self.db.execute("CREATE TABLE IF NOT EXISTS ayar (ad TEXT PRIMARY KEY, deger TEXT)")
        # İzlenen videonun yanında YouTube'un önerdiği kanallar: programın kendi sıralaması için (ilgi.py).
        self.db.execute("""CREATE TABLE IF NOT EXISTS oneri_kanal (
            video_id TEXT, kanal_id TEXT, ad TEXT, PRIMARY KEY (video_id, kanal_id))""")
        # Kanalların resmi (abonelik sayfasındaki "İlgini çekebilir"): video sayfasıyla ve önerilerle zaten
        # gelen cevaptan alınır, ek istek yapılmaz; izlendikçe dolar.
        self.db.execute("CREATE TABLE IF NOT EXISTS kanal_resim (kanal_id TEXT PRIMARY KEY, resim TEXT)")
        self.db.commit()
        # Küçük resimlerdeki ilerleme çubuğu için bellekte: id -> oran (0-1).
        self._oran = {r[0]: r[1] / r[2] for r in self.db.execute(
            "SELECT id, konum, sure FROM gecmis WHERE sure > 0 AND konum > 0")}

    # QML bağları ilerleme çizgilerini yenilesin diye: her konum değişiminde artar.
    def _surum(self):
        return self.__dict__.setdefault("_s", 0)
    surum = Property(int, _surum, notify=konumlarDegisti)

    def _yenile(self):
        self._s = self._surum() + 1
        self.konumlarDegisti.emit()

    @Slot(str, result=str)
    def ayar(self, ad):
        r = self.db.execute("SELECT deger FROM ayar WHERE ad = ?", (ad,)).fetchone()
        return r[0] if r else ""

    @Slot(str, str)
    def ayarYaz(self, ad, deger):
        self.db.execute("INSERT INTO ayar (ad, deger) VALUES (?, ?) ON CONFLICT(ad) DO UPDATE SET deger = excluded.deger",
                        (ad, deger))
        self.db.commit()

    @Slot("QVariantMap")
    def izlendi(self, v):
        """Video birkaç saniye oynayınca geçmişe girer (en üste çıkar; oynatici.py, IZLEME_SN). Kaldığı yer korunur;
        son IZLENIS_SAYISI izlenişin zamanı tutulur."""
        if not v.get("id") or "://" in v["id"]:
            return
        simdi = time.time()
        r = self.db.execute("SELECT zamanlar FROM gecmis WHERE id = ?", (v["id"],)).fetchone()
        try:
            zamanlar = json.loads(r[0]) if r and r[0] else []
        except ValueError:
            zamanlar = []
        if zamanlar and simdi - zamanlar[0] < AYNI_IZLENIS_SN:
            zamanlar[0] = simdi
        else:
            zamanlar.insert(0, simdi)
        zamanlar = json.dumps(zamanlar[:IZLENIS_SAYISI])
        self.db.execute("""INSERT INTO gecmis (id, baslik, kanal, kanal_id, sure_yazi, son, zamanlar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET son = excluded.son, zamanlar = excluded.zamanlar,
              baslik = COALESCE(NULLIF(excluded.baslik, ''), gecmis.baslik),
              kanal = COALESCE(NULLIF(excluded.kanal, ''), gecmis.kanal),
              kanal_id = COALESCE(excluded.kanal_id, gecmis.kanal_id),
              sure_yazi = COALESCE(NULLIF(excluded.sure_yazi, ''), gecmis.sure_yazi)""",
                        (v["id"], v.get("baslik") or "", v.get("kanal") or "", v.get("kanal_id"),
                         v.get("sure") or "", simdi, zamanlar))
        self.db.commit()
        self.gecmisDegisti.emit()

    @Slot(str, "QVariantMap")
    def bilgiTamamla(self, video_id, v):
        """Video sayfası gelince başlık ve kanal geçmişte tamamlanır (bağlantıdan açılanlar için)."""
        self.db.execute("UPDATE gecmis SET baslik = COALESCE(NULLIF(?, ''), baslik), "
                        "kanal = COALESCE(NULLIF(?, ''), kanal), kanal_id = COALESCE(?, kanal_id) WHERE id = ?",
                        (v.get("baslik") or "", v.get("kanal") or "", v.get("kanal_id"), video_id))
        # İlk 20 önerinin kanalları (sayfanın ilk gördüğü kısım); kendi kanalı ilgili sayılmaz.
        oneriler = [(video_id, o["kanal_id"], o.get("kanal") or "") for o in (v.get("oneriler") or [])[:20]
                    if o.get("kanal_id") and o["kanal_id"] != v.get("kanal_id")]
        self.db.executemany("INSERT OR IGNORE INTO oneri_kanal (video_id, kanal_id, ad) VALUES (?, ?, ?)", oneriler)
        resimler = [(x.get("kanal_id"), x.get("kanal_resim")) for x in [v] + list(v.get("oneriler") or [])]
        self.db.executemany("INSERT OR REPLACE INTO kanal_resim (kanal_id, resim) VALUES (?, ?)",
                            [r for r in resimler if r[0] and r[1]])
        self.db.commit()
        self.gecmisDegisti.emit()

    @Slot(str, float, float)
    def konumKaydet(self, video_id, konum, sure):
        if not video_id or "://" in video_id or sure <= 0:
            return
        if konum < BAS_PAYI or konum > sure - SON_PAYI:
            konum = 0.0 if konum < BAS_PAYI else sure  # bitmiş: tam dolu çubuk, açılınca baştan
        self.db.execute("UPDATE gecmis SET konum = ?, sure = ? WHERE id = ?", (konum, sure, video_id))
        self.db.commit()
        eski = self._oran.get(video_id)
        self._oran[video_id] = konum / sure
        if eski != self._oran[video_id]:
            self._yenile()

    @Slot(str, result=float)
    def baslangic(self, video_id):
        """Video açılırken nereden başlasın: kaldığı yer, yoksa ya da bitmişse 0."""
        r = self.db.execute("SELECT konum, sure FROM gecmis WHERE id = ?", (video_id,)).fetchone()
        if not r or not r[1] or r[0] >= r[1] - SON_PAYI:
            return 0.0
        return float(r[0])

    @Slot(str, result=float)
    def oran(self, video_id):
        return self._oran.get(video_id, 0.0)

    @Slot(result=list)
    def gecmis(self):
        return self.gecmisAra("")

    @Slot(str, result=list)
    def gecmisAra(self, sorgu):
        """Günlere göre: [{'gun': 'Bugün', 'videolar': [...]}, ...]. Sorgu verilirse (geçmiş sayfasındaki arama
        kutusu) yalnız başlığında ya da kanal adında bütün sözcükleri geçenler, bütün geçmişte;
        büyük-küçük harf farkı gözetilmez (Türkçede I/ı, İ/i; bicim.turkce_mi)."""
        bugun = date.today()
        adlar = {bugun: tr("Bugün"), bugun - timedelta(days=1): tr("Dün")}
        turkce = bicim.turkce_mi(sorgu)
        sozcukler = bicim.kucuk(sorgu, turkce).split()
        gunler = []
        satirlar = self.db.execute("SELECT id, baslik, kanal, kanal_id, sure_yazi, sure, konum, son, zamanlar "
                                   "FROM gecmis ORDER BY son DESC" + ("" if sozcukler else " LIMIT 2000"))
        for r in satirlar:
            if sozcukler:
                metin = bicim.kucuk((r[1] or "") + " " + (r[2] or ""), turkce)
                if not all(w in metin for w in sozcukler):
                    continue
            g = datetime.fromtimestamp(r[7]).date()
            ad = adlar.get(g) or bicim.gun_ay(g, g.year != bugun.year)
            if not gunler or gunler[-1]["gun"] != ad:
                gunler.append({"gun": ad, "videolar": []})
            gunler[-1]["videolar"].append({
                "id": r[0], "baslik": r[1], "kanal": r[2], "kanal_id": r[3], "sure": r[4],
                "resim": f"https://i.ytimg.com/vi/{r[0]}/mqdefault.jpg",
                "oran": (r[6] / r[5]) if r[5] else 0.0, "kaldigi": r[6] if r[5] and r[6] < r[5] else 0.0,
                "zamanlar": izlenis_yazisi(r[8], r[7], bugun)})
        return gunler

    @Slot(str)
    def sil(self, video_id):
        self.db.execute("DELETE FROM gecmis WHERE id = ?", (video_id,))
        self.db.execute("DELETE FROM oneri_kanal WHERE video_id = ?", (video_id,))   # geçmişle birlikte gider
        self.db.commit()
        self._oran.pop(video_id, None)
        self.gecmisDegisti.emit()
        self._yenile()

    @Slot()
    def hepsiniSil(self):
        self.db.execute("DELETE FROM gecmis")
        self.db.execute("DELETE FROM oneri_kanal")
        self.db.commit()
        self._oran.clear()
        self.gecmisDegisti.emit()
        self._yenile()
