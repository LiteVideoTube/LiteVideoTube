"""Abonelik yoklaması, pencereden bağımsız (Qt yüklemez): program açıkken abonelik.py, kapalıyken arkada.py kullanır.

Kural: önce yalnız RSS (~20-70 KB, kesin yayın zamanı).
RSS yeni video gösterirse ya da RSS bozuksa (404; ara ara oluyor) kanalın 'Videolar' sekmesi okunur (süreler ve
canlı yayınlar oradan). Program açıkken zilli kanallara 15 dakikada bir, izlenen kanallara yarım saatte bir, kalanlara
iki saatte bir bakılır (25 Ekim'e kadar hepsine yarım saatte bir); program kapalıyken kalanlara 5 saatte bir, zilli
kanallara yine 15 dakikada bir. Kanallar tek tek, aralarında ARALIK kadar; RSS art arda bozuk dönerse yavaşlanır.
429 gelirse çağıran bir süre durur (abonelik.py, arkada.py).
"""
import json
import os
import random
import re
import shutil
import sqlite3
import sys
import time
from pathlib import Path

from . import ilgi, youtube

# Kanallara bakma aralığı önemine göre (bir denemede RSS isteklerinin yarısı bozuk dönüyordu, istekler
# azalsın): zil takılan kanal, izlenen kanal (ilgi puanı olan), kalanlar. Önceden açıkken hepsine yarım saatte bir
# (dakikada ~24 kanal); şimdi ~10. Bedeli: az izlenen kanalın yeni videosu en geç iki saatte görünür.
BAKIS_ACIK = {"zil": 15 * 60, "ilgi": 30 * 60, "diger": 2 * 3600}
BAKIS_ARKADA = {"zil": 15 * 60, "ilgi": 5 * 3600, "diger": 5 * 3600}
# İki kanal arası bekleme; RSS art arda bozuk dönerse her bozuk cevapta iki katına çıkar (en çok 8 katı).
ARALIK = 4.0
# RSS bozuk dönünce kanal sayfasına (gzip'le ~41 KB) en çok bu sıklıkla gidilir; 730 kanalda yarım saatte
# bir gitmek saatte ~60 MB ederdi. RSS her bakışta yeniden denenir (rastgele düzeliyor).
SAYFA_ARALIGI = 2 * 3600
# Kayıtta abone_video.canli: 1 şu an canlı, 2 başlamamış yayın (Canlı sekmesinde süresiz ve canlı değil), 0 değil.
# Başlamamış yayına en çok bu kadar süre bakılmaya devam edilir (unutulmuş yayın planları için istek gitmesin).
YAKINDA_EN_COK = 14 * 86400
# Her kanalın 'Canlı' sekmesine en az haftada bir bakılır: 7/24 süren yayınlar RSS'te görünmez (yayın aylar önce
# başlamış, RSS son 15 yüklemeyi verir; 25 Ekim, Ulusal Kanal). Yeni başlayan yayınlar RSS'ten yakalanır.
CANLI_TARAMA = 7 * 86400
# "Yeni" sayılan video: son iki günde yayımlanmış uzun video (abonelik sayfasının "Yeni gelenler" bölümüyle aynı kural).
YENI_YAS = 2 * 86400
# Süresi boş uzun videoya kaç gün geriye kadar bir kez daha bakılır (kanala_bak, eksikler).
EKSIK_YAS = 7 * 86400


def kok_klasor():
    """Programın klasörü; Qt'nin GenericDataLocation'ı ile aynı yer. Linux'ta ~/.local/share/LiteVideoTube,
    Windows'ta %LOCALAPPDATA%/LiteVideoTube. Denemelerde LVT_VERI."""
    if os.environ.get("LVT_VERI"):
        return Path(os.environ["LVT_VERI"])
    if sys.platform == "win32":
        kok = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    elif sys.platform == "darwin":
        kok = os.path.expanduser("~/Library/Application Support")
    else:
        kok = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return Path(kok) / "LiteVideoTube"


# Kişiler: programı birden çok kişi kullanabilir; her kişinin abonelikleri, zili, geçmişi, listeleri
# ve programın kendi sıralaması ayrı. İlk kişinin kayıtları kök klasörde kalır (önceki kayıtlar taşınmaz), sonrakiler
# kisiler/<kimlik>/ altında. Seçim kisiler.json'da; LVT_KISI ile o süreç için başka kişi verilebilir.
def kisiler():
    try:
        with open(kok_klasor() / "kisiler.json", encoding="utf-8") as f:
            k = json.load(f)
        if k.get("liste"):
            return k
    except (OSError, ValueError):
        pass
    return {"secili": "", "liste": [{"id": "", "ad": "Kişi 1"}]}


def kisileri_yaz(k):
    os.makedirs(kok_klasor(), exist_ok=True)
    yol = kok_klasor() / "kisiler.json"
    with open(str(yol) + ".yeni", "w", encoding="utf-8") as f:
        json.dump(k, f, ensure_ascii=False, indent=1)
    os.replace(str(yol) + ".yeni", yol)


def silinenleri_temizle():
    """Silinen kişilerin kayıtları (kisi.py, sil). Yalnız "silinen"de adı geçenlere dokunulur; silinemeyen (açık dosya)
    listede kalır, sonraki açılışta yeniden denenir. İlk kişinin kayıtları kök klasörde, öbürleri kendi klasöründe."""
    k = kisiler()
    kalan = []
    for kimlik in k.get("silinen", []):
        if kimlik:
            klasor = kok_klasor() / "kisiler" / kimlik
            shutil.rmtree(klasor, ignore_errors=True)
            if klasor.exists():
                kalan.append(kimlik)
            continue
        for ad in ("kayit.db", "kayit.db-wal", "kayit.db-shm", "arkada.log"):
            try:
                (kok_klasor() / ad).unlink(missing_ok=True)
            except OSError:
                if kimlik not in kalan:
                    kalan.append(kimlik)
    if kalan != k.get("silinen", []):
        k["silinen"] = kalan
        kisileri_yaz(k)


def secili_kisi():
    if "LVT_KISI" in os.environ:
        return os.environ["LVT_KISI"]
    return kisiler().get("secili", "")


def veri_klasoru():
    """Seçili kişinin kayıtlarının klasörü (kayit.py, abonelik.py, liste.py, arkada.py bunu kullanır)."""
    k = secili_kisi()
    return kok_klasor() / "kisiler" / k if k else kok_klasor()


def db_yolu():
    return str(veri_klasoru() / "kayit.db")


def baglan(yol=None):
    # Her iş parçacığı ve süreç kendi bağlantısını açar; program ve arka plan aynı dosyayı paylaşır (WAL).
    yol = yol or db_yolu()
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    db = sqlite3.connect(yol, timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    # WAL'da NORMAL: her yazışta diske zorla yazma (fsync) yok, yalnız birleştirmede; elektrik kesilirse son birkaç
    # yazış kaybolabilir, kayıt bozulmaz (SQLite belgesi). Eski bilgisayarda her yoklamanın fsync'i pencereyi bekletiyordu.
    db.execute("PRAGMA synchronous=NORMAL")
    return db


def tablolari_kur(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS kanal (id TEXT PRIMARY KEY, ad TEXT, son_bakis REAL DEFAULT 0,
            rss_bozuk INTEGER DEFAULT 0, son_sayfa REAL DEFAULT 0, zil INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS abone_video (id TEXT PRIMARY KEY, kanal_id TEXT, baslik TEXT,
            sure TEXT DEFAULT '', yayin REAL DEFAULT 0, yayin_yazi TEXT DEFAULT '', canli INTEGER DEFAULT 0,
            fark REAL);
        CREATE INDEX IF NOT EXISTS abone_video_yayin ON abone_video(yayin DESC);
        CREATE TABLE IF NOT EXISTS ayar (ad TEXT PRIMARY KEY, deger TEXT);
        CREATE TABLE IF NOT EXISTS kanal_resim (kanal_id TEXT PRIMARY KEY, resim TEXT);
        CREATE TABLE IF NOT EXISTS cikilan_kanal (id TEXT PRIMARY KEY, zaman REAL);""")
    sutunlar = [r[1] for r in db.execute("PRAGMA table_info(kanal)")]
    for ad, tanim in (("son_sayfa", "REAL DEFAULT 0"), ("zil", "INTEGER DEFAULT 0"), ("son_canli", "REAL DEFAULT 0"),
                      ("son_giris", "REAL DEFAULT 0")):
        if ad not in sutunlar:
            db.execute(f"ALTER TABLE kanal ADD COLUMN {ad} {tanim}")
    if "son_giris" not in sutunlar and "id" in sutunlar:
        # Mavi nokta ilk açılışta yalnız son iki günde gelenler için yansın (yaklaşık 150 kanal); sonra kanal
        # sayfasına son girişten beri gelenler.
        db.execute("UPDATE kanal SET son_giris = ?", (time.time() - 2 * 86400,))
    if "son_canli" not in sutunlar and "id" in sutunlar:
        # İlk 'Canlı' taraması bir haftaya yayılır (731 kanala birden istek gitmesin); zilli ve izlenen kanallar hemen.
        simdi, ilgili = time.time(), {k for k, p in ilgi.kanal_ilgileri(db).items() if p > 0}
        db.executemany("UPDATE kanal SET son_canli = ? WHERE id = ?",
                       [(0 if zil or kid in ilgili else simdi - random.random() * CANLI_TARAMA, kid)
                        for kid, zil in db.execute("SELECT id, zil FROM kanal").fetchall()])
    # Shorts işareti (25 Ekim): RSS'te bağlantısı /shorts/ olan video. Önceden kaydedilenler kanala bir sonraki
    # bakışta işaretlenir (RSS'te hâlâ duruyorlarsa).
    if "shorts" not in [r[1] for r in db.execute("PRAGMA table_info(abone_video)")]:
        db.execute("ALTER TABLE abone_video ADD COLUMN shorts INTEGER DEFAULT 0")
    if "sure_arandi" not in [r[1] for r in db.execute("PRAGMA table_info(abone_video)")]:
        db.execute("ALTER TABLE abone_video ADD COLUMN sure_arandi REAL DEFAULT 0")
    # İzlenme sayısı (28 Ekim: ana sayfada görünmüyordu): RSS'ten, kanala her bakışta kanalın son 15 videosu için
    # yenilenir; daha eski videolarda son görülen sayı kalır.
    if "izlenme" not in [r[1] for r in db.execute("PRAGMA table_info(abone_video)")]:
        db.execute("ALTER TABLE abone_video ADD COLUMN izlenme INTEGER")
    db.commit()


def ayar(db, ad, vars=None):
    r = db.execute("SELECT deger FROM ayar WHERE ad = ?", (ad,)).fetchone()
    return r[0] if r else vars


def ayar_yaz(db, ad, deger):
    db.execute("INSERT INTO ayar (ad, deger) VALUES (?, ?) ON CONFLICT(ad) DO UPDATE SET deger = excluded.deger",
               (ad, deger))
    db.commit()


def _tur_sql(db, simdi):
    """Kanalın türü SQL ifadesi olarak (0 zil, 1 izlenen, 2 kalan) ve parametreleri."""
    ilgili = [k for k, p in ilgi.kanal_ilgileri(db, simdi).items() if p > 0]
    return (f"CASE WHEN zil = 1 THEN 0 WHEN id IN ({','.join('?' * len(ilgili)) or 'NULL'}) THEN 1 ELSE 2 END",
            ilgili)


def siradaki(db, acik):
    """Sırası gelen bir kanal (id, rss_bozuk, önceki bakış zamanı) ya da None; bakış zamanı hemen yazılır ki aynı kanala iki kez
    (iki iş parçacığı ya da program ile arka plan) bakılmasın. Önce zilli, sonra izlenen kanallar; her türde en eskisi."""
    simdi = time.time()
    b = BAKIS_ACIK if acik else BAKIS_ARKADA
    tur, ilgili = _tur_sql(db, simdi)
    db.execute("BEGIN IMMEDIATE")
    r = db.execute(f"""SELECT id, rss_bozuk, son_bakis FROM kanal
                       WHERE son_bakis < CASE {tur} WHEN 0 THEN ? WHEN 1 THEN ? ELSE ? END
                       ORDER BY {tur}, son_bakis LIMIT 1""",
                   (*ilgili, simdi - b["zil"], simdi - b["ilgi"], simdi - b["diger"], *ilgili)).fetchone()
    if r:
        db.execute("UPDATE kanal SET son_bakis = ? WHERE id = ?", (simdi, r[0]))
    db.commit()
    return r


def geride_kalan(db):
    """Program açıkken sırası iki tur geçmiş zilli ya da izlenen kanal sayısı: program açılınca bunlara yetişene kadar
    abonelik sayfasında "Yeni videolara bakılıyor" yazar. Kalan kanallar sayılmaz (en geç iki saat gecikmesi kabul)."""
    simdi = time.time()
    tur, ilgili = _tur_sql(db, simdi)
    return db.execute(f"""SELECT COUNT(*) FROM kanal WHERE {tur} < 2
                          AND son_bakis < CASE {tur} WHEN 0 THEN ? ELSE ? END""",
                      (*ilgili, *ilgili, simdi - 2 * BAKIS_ACIK["zil"], simdi - 2 * BAKIS_ACIK["ilgi"])).fetchone()[0]


def bekleme(bozuk_ust_uste):
    """İki kanal arası bekleme: RSS art arda bozuk döndükçe yavaşlar (3. bozuktan sonra her biri iki kat, en çok 8 katı)."""
    return ARALIK * min(8, 2 ** max(0, bozuk_ust_uste - 2))


def geri_al(db, kanal_id, onceki):
    """Ağ yokken bakılamayan kanal "bakıldı" sayılmasın: internet gelince hemen sırası gelsin."""
    db.execute("UPDATE kanal SET son_bakis = ? WHERE id = ?", (onceki, kanal_id))
    db.commit()


def kanala_bak(kanal_id, yol=None):
    """Bir kanalın yeni videolarını kayda yazar; (yeni video sayısı, RSS sağlam mı) döner (ilk bakışta gelenler yeni
    sayılmaz).
    Yeni sayılan yalnız "Yeni gelenler" bölümüne girecek olan: Shorts değil, son iki günde yayımlanmış. Önceden
    kayıtta olmayan her video sayılıyordu; RSS bozuk dönünce kanal sayfasından gelen eski videolar (kanal başına
    ~15, yıllık olanlar dahil) ve Shorts da ("928 yeni video geldi", birkaç dakikada yükseliyordu).
    YouTube 429 verirse kanalın sırası geri alınır ve youtube.CokIstek yükselir."""
    try:
        # RSS rastgele bozuk dönebiliyor (aynı kanala 200/404/500); bir kez daha denenir.
        rss = youtube.kanal_rss(kanal_id)
        if rss is None:
            time.sleep(1.0 + random.random())
            rss = youtube.kanal_rss(kanal_id)
        db = baglan(yol)
        bilinen = {x[0] for x in db.execute("SELECT id FROM abone_video WHERE kanal_id = ?", (kanal_id,))}
        yeni = 0
        if rss is not None:
            db.execute("UPDATE kanal SET rss_bozuk = 0, ad = COALESCE(NULLIF(?, ''), ad) WHERE id = ?",
                       (rss["ad"], kanal_id))
            # Bitmiş canlı yayının zamanı RSS'ten değil 'Canlı' sekmesinden (_canlilari_yaz): RSS'in 'published'ı
            # yayınlarda kayıyor (örnek: KRT TV'nin 18 saat önceki yayını RSS'te 5 saat önce).
            for v in rss["videolar"]:
                db.execute("""INSERT INTO abone_video (id, kanal_id, baslik, yayin, fark, shorts, izlenme)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET baslik = excluded.baslik, shorts = excluded.shorts,
                      izlenme = COALESCE(excluded.izlenme, abone_video.izlenme),
                      yayin = CASE WHEN abone_video.yayin_yazi LIKE '%yayınlandı' THEN abone_video.yayin
                                   ELSE excluded.yayin END""",
                           (v["id"], kanal_id, v["baslik"], v["yayin"], time.time(), int(v.get("shorts", False)),
                            v.get("izlenme")))
            sinir = time.time() - YENI_YAS
            yeni = len([v for v in rss["videolar"] if v["id"] not in bilinen and not v["shorts"]
                        and (v["yayin"] or 0) > sinir]) if bilinen else 0
            db.commit()
        else:
            db.execute("UPDATE kanal SET rss_bozuk = 1 WHERE id = ?", (kanal_id,))
            db.commit()
        # Süreler kanalın 'Videolar' sekmesinden: RSS yeni video gösterdiyse ya da RSS bozuksa ve kanal sayfasına
        # son 2 saatte bakılmadıysa. Canlı yayınlar 'Canlı' sekmesinden (önceden 'Videolar'
        # sekmesinde aranıyordu, canlılar orada olmadığı için program hiçbir yayını canlı bilmiyordu): RSS'teki yeni
        # uzun video 'Videolar'da çıkmadıysa, ya da kanalın canlı ya da başlamamış yayını varsa (her bakışta: yayın
        # bitince işaret kalksın, başlayınca konsun).
        son_sayfa, son_canli = db.execute("SELECT son_sayfa, son_canli FROM kanal WHERE id = ?", (kanal_id,)).fetchone() or (0, 0)
        son_sayfa, son_canli = son_sayfa or 0, son_canli or 0
        # Yeni gelen yalnız Shorts ise kanal sayfasına gidilmez: Shorts "Videolar" sekmesinde yok, süresi oradan gelmez.
        rss_yeniler = {v["id"] for v in rss["videolar"] if v["id"] not in bilinen and not v["shorts"]} if rss else set()
        canli_var = db.execute("""SELECT 1 FROM abone_video WHERE kanal_id = ? AND (canli = 1 OR (canli = 2 AND fark > ?))
                                  LIMIT 1""", (kanal_id, time.time() - YAKINDA_EN_COK)).fetchone() is not None
        sayfa = bool(rss_yeniler) or (rss is None and time.time() - son_sayfa > SAYFA_ARALIGI)
        tarama = time.time() - son_canli > CANLI_TARAMA
        # Süresi boş uzun videolar ("bazı videoların süresi gözükmemektedir"; son yedi günde 58 kanalda
        # 235 video). Çoğu yayın: eski kodla ya da RSS bozukken geldikleri için 'Canlı' sekmesine bakılmamıştı. Bir
        # kısmı Shorts (RSS bazı Shorts'u watch?v= bağlantısıyla veriyor, uzun video sanılıyorlar), bir kısmı kanalın
        # gizlediği ya da sildiği video, birkaçı hiç başlamamış yayın. Her biri için bir
        # kez Videolar ve Canlı sekmesine, orada yoksa Shorts sekmesine, sonra kanalın yüklemeler listesine bakılır
        # (sure_arandi: bir daha bakılmasın diye).
        eksikler = [r[0] for r in db.execute("""SELECT id FROM abone_video WHERE kanal_id = ? AND shorts = 0 AND canli = 0
                        AND sure = '' AND sure_arandi = 0 AND yayin > ?""", (kanal_id, time.time() - EKSIK_YAS))]
        sayfa = sayfa or bool(eksikler)
        if sayfa or canli_var or tarama:
            # Kanal sayfası istenirken kayıt kilitli kalmamalı: önce yazılıp bitirilir. Önceden UPDATE'in açtığı
            # yazma işlemi istek boyunca (1-3 sn, yavaş internette daha çok) sürüyordu; programın ana iş parçacığı
            # (yoklama sırası, Abone ol, kaldığı yer) kaydı beklerken pencere donuyordu (düğmeler
            # geç işliyor, Yönet basılı tutunca açılıyor).
            db.execute("UPDATE kanal SET son_sayfa = ? WHERE id = ?", (time.time(), kanal_id))
            db.commit()
            ad, videolar, resim = youtube.kanal_videolari(kanal_id) if sayfa else ("", [], "")
            for v in videolar:
                var = db.execute("SELECT 1 FROM abone_video WHERE id = ?", (v["id"],)).fetchone()
                if var:
                    db.execute("UPDATE abone_video SET sure = ?, canli = ?, yayin_yazi = ? WHERE id = ?",
                               (v["sure"], int(v["canli"]), v["tarih"], v["id"]))
                elif rss is None:
                    yayin = yaklasik_zaman(v["tarih"])
                    db.execute("""INSERT INTO abone_video (id, kanal_id, baslik, sure, yayin, yayin_yazi, canli, fark)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                               (v["id"], kanal_id, v["baslik"], v["sure"], yayin, v["tarih"], int(v["canli"]), time.time()))
                    yeni += 1 if bilinen and yayin > time.time() - YENI_YAS else 0
            if ad:
                db.execute("UPDATE kanal SET ad = ? WHERE id = ?", (ad, kanal_id))
            db.commit()
            if canli_var or tarama or eksikler or rss_yeniler - {v["id"] for v in videolar}:
                canlilar, resim2 = youtube.kanal_canli(kanal_id)
                resim = resim or resim2
                _canlilari_yaz(db, kanal_id, canlilar)
                db.execute("UPDATE kanal SET son_canli = ? WHERE id = ?", (time.time(), kanal_id))
                db.commit()
            if eksikler:
                kalan = {r[0] for r in db.execute(f"""SELECT id FROM abone_video WHERE sure = '' AND canli = 0 AND id IN
                             ({','.join('?' * len(eksikler))})""", eksikler)}
                if kalan:
                    shortslar, _ = youtube.kanal_shorts(kanal_id, yoklama=True)
                    db.executemany("UPDATE abone_video SET shorts = 1 WHERE id = ?",
                                   [(v["id"],) for v in shortslar if v["id"] in kalan])
                    kalan -= {v["id"] for v in shortslar}
                # Hâlâ süresizse yüklemeler listesinden (sekmeleri boş dönen kanallar, ilk 30'dan taşan yayınlar).
                if kalan:
                    for v in youtube.kanal_yuklemeleri(kanal_id):
                        if v["id"] in kalan and re.fullmatch(r"\d+(:\d+)+", v["sure"] or ""):
                            db.execute("UPDATE abone_video SET sure = ?, yayin_yazi = ? WHERE id = ?",
                                       (v["sure"], v["tarih"], v["id"]))
                            _yayin_zamani(db, v)
                            kalan.discard(v["id"])
                # Hiçbir listede yoksa çoğu zaman kanal videoyu gizlemiş ya da silmiş: kayıttan çıkar (YouTube da
                # göstermiyor, tıklayınca açılmıyordu). Başlamamış yayınlar açık sayılır, kalır.
                for i in list(kalan)[:10]:
                    time.sleep(1.0)
                    if youtube.video_var_mi(i) is False:
                        db.execute("DELETE FROM abone_video WHERE id = ?", (i,))
                db.executemany("UPDATE abone_video SET sure_arandi = ? WHERE id = ?",
                               [(time.time(), i) for i in eksikler])
                db.commit()
            if resim:   # sol kenardaki abonelik listesi için
                db.execute("INSERT OR REPLACE INTO kanal_resim (kanal_id, resim) VALUES (?, ?)", (kanal_id, resim))
                db.commit()
        db.close()
        return yeni, rss is not None
    except youtube.CokIstek:
        db = baglan(yol)
        db.execute("UPDATE kanal SET son_bakis = 0 WHERE id = ?", (kanal_id,))  # sonra yeniden
        db.commit()
        db.close()
        raise


def _canlilari_yaz(db, kanal_id, videolar):
    """'Canlı' sekmesinden gelenleri kayda işler: canlı (1), başlamamış (2), bitmiş (0, süresiyle). Kayıtta canlı ya da
    başlamamış görünüp sekmede artık olmayanın işareti kalkar. Kayıtta olmayan canlı yayın eklenir (RSS bozukken)."""
    gorulen = set()
    for v in videolar:
        gorulen.add(v["id"])
        sureli = bool(re.fullmatch(r"\d+(:\d+)+", v["sure"] or ""))
        durum = 1 if v["canli"] else (0 if sureli else 2)
        if db.execute("SELECT 1 FROM abone_video WHERE id = ?", (v["id"],)).fetchone():
            db.execute("UPDATE abone_video SET canli = ?, sure = ?, yayin_yazi = COALESCE(NULLIF(?, ''), yayin_yazi) WHERE id = ?",
                       (durum, v["sure"] if sureli else "", v["tarih"], v["id"]))
            if durum == 0:
                _yayin_zamani(db, v)
        elif durum == 1:
            db.execute("""INSERT INTO abone_video (id, kanal_id, baslik, sure, yayin, yayin_yazi, canli, fark)
                VALUES (?, ?, ?, '', ?, ?, 1, ?)""",
                       (v["id"], kanal_id, v["baslik"], yaklasik_zaman(v["tarih"]), v["tarih"], time.time()))
    eski = [r[0] for r in db.execute("SELECT id FROM abone_video WHERE kanal_id = ? AND canli != 0", (kanal_id,))
            if r[0] not in gorulen]
    # Süresi hâlâ boşsa yeniden aranır (eksikler, kanala_bak). 26 Ekim'e kadar Canlı sekmesi olmayan kanallarda
    # YouTube'un döndürdüğü Shorts sekmesi okunuyor, videolar 'başlamamış' (2) sanılıyordu (youtube._sekme_turu).
    db.executemany("UPDATE abone_video SET canli = 0, sure_arandi = CASE WHEN sure = '' THEN 0 ELSE sure_arandi END WHERE id = ?",
                   [(i,) for i in eski])
    db.commit()


def _yayin_zamani(db, v):
    """Bitmiş yayının zamanı YouTube'un yazdığı gibi ('18 saat önce yayınlandı'); RSS'inki kayıyor. Gün ve üstü kaba
    olduğu için yalnız saat ve altı."""
    if re.search(r"\d+\s*(saniye|dakika|saat) önce yayınlandı", v["tarih"] or ""):
        db.execute("UPDATE abone_video SET yayin = ? WHERE id = ?", (yaklasik_zaman(v["tarih"]), v["id"]))


def yaklasik_zaman(yazi):
    """'3 gün önce' gibi yazıdan yaklaşık zaman (RSS bozukken sıralama için)."""
    m = re.search(r"(\d+)\s*(saniye|sn|dakika|dk|saat|sa|gün|hafta|ay|yıl)", yazi or "")
    if not m:
        return time.time() - 3600
    n, b = int(m.group(1)), m.group(2)
    carpan = {"saniye": 1, "sn": 1, "dakika": 60, "dk": 60, "saat": 3600, "sa": 3600, "gün": 86400,
              "hafta": 7 * 86400, "ay": 30 * 86400, "yıl": 365 * 86400}[b]
    return time.time() - n * carpan
