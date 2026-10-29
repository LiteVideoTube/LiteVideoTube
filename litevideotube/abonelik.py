"""Abonelikler: hesapsız, programın kendi kaydında. Kanal listesi bir kez alınır (tarayıcının YouTube
oturumundan ya da eski LiteVideoTube'dan), sonra kanallar arka planda yoklanır.

Yoklama kuralı yoklama.py'de (program açıkken kanallara yarım saatte bir, zilli kanallara 15 dakikada bir;
program kapalıyken arkada.py). 429 gelirse 10 dakika durulur, her yeni 429'da süre ikiye katlanır. İçe alma
tek yönlü: yalnız ekler, silmez, YouTube hesabına hiçbir şey yazmaz.
"""
import datetime
import json
import os
import random
import re
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from . import arkada, bicim, diller, ilgi, tarayici, youtube, yoklama
from .ceviri import QT_TR_NOOP, kurulan_dil, tr
from .cozumle import ytdlp_js, ytdlp_yolu

ESZAMANLI = 1   # kanallara tek tek, aralarında yoklama.bekleme kadar (hız düşsün)
# Zilli kanalların yeni videoları abonelik sayfasının başında ayrı gösterilir: bu kadar yeni olanlar, en çok ZIL_EN_COK
# tane; bölüm satır satır aşağı uzar (iki gün azdı, "arttıralım"; zilli kanallar seyrek yüklüyor).
ZIL_YENI = 7 * 86400
ZIL_EN_COK = 24
# Yeni gelenler bölümü: son bakıştan beri gelen ve son iki günde yayımlanmış videolar, en çok BOLUM tane.
YENI_YAS = yoklama.YENI_YAS
BOLUM = 12
# Shorts: yalnız güncel olanlar; bir kanalın bütün Shorts'ları kanal sayfasının Shorts bölümünde.
NOKTA_YAS = 7 * 86400          # mavi nokta: son yedi günde yayımlanmış video
SHORTS_YAS = 3 * 86400          # abonelik sayfasındaki Shorts şeridi: son üç gün
DEVAM = 120                     # "Bütün abonelikler" aşağı inildikçe bu kadar daha (abonelik.devami)
# Abonelik sayfasının kart satırı: abone_video v JOIN kanal k.
KART_SUTUNLARI = ("v.id, v.baslik, k.ad, v.kanal_id, v.sure, v.yayin, v.yayin_yazi, v.canli, v.fark, k.zil, v.shorts, "
                  "v.izlenme")
KESFET_SHORTS_YAS = 7 * 86400   # Keşfet: ilgili kanalların son bir haftası
KESFET_ARALIK = 3 * 3600        # ilgili kanalların Shorts ve video listesine en çok üç saatte bir bakılır
KESFET_KANAL_BASINA = 2         # Keşfet'te bir kanalın en son uzun videolarından kaçı (28 Ekim; sayfa doldurulmasın)
GUNDEM_ARALIGI = 30 * 60        # aboneliği olmayanın sayfasındaki gündem en çok yarım saatte bir yenilenir
TARAYICILAR = ["firefox", "chrome", "chromium", "brave", "edge", "opera", "vivaldi"]
# Telefondan ya da tarayıcıdan YouTube'da abone olunan kanallar: program günde bir kez aynı yoldan
# listeyi kendiliğinden okur, yalnız yeni kanalları ekler. Programda abonelikten çıkılan kanal geri eklenmez
# (cikilan_kanal); YouTube'da çıkılan kanal programdan silinmez.
# yt-dlp'nin abonelik listesinde girişsiz sayıldığı hatalar (girişsiz feed/channels: "Failed to resolve url").
GIRISSIZ = re.compile(r"Failed to resolve url|Sign in|login|not logged", re.I)
ESITLEME_ARALIGI = 86400
ESITLEME_GECIKME = 120 * 1000   # program açıldıktan iki dakika sonra (eski makinede açılış ağırlaşmasın)


# Sol kenardaki listede alfabetik sıra Türkçe abeceyle (ç c'den sonra, ı i'den önce...). Ekran dili Türkçe değilse
# büyük-küçük harf ve işaret gözetmeyen sıra (diller.duz_sira).
_ABECE = "abcçdefgğhıijklmnoöprsştuüvwxyz"


def abece_anahtari(ad):
    if kurulan_dil() != "tr":
        return diller.duz_sira(ad)
    s = (ad or "").replace("I", "ı").replace("İ", "i").lower()
    return [1000 + _ABECE.index(c) if c in _ABECE else ord(c) for c in s]


def kucuk_resim(adres, boy=48):
    """Kanal resminin küçük hâli (=s176-c-k-... -> =s48-c-k-...); eski makinede büyük resim inmesin. Yuvarlak kesmeyi
    (=s48-cc) sunucu yalnız bazı resimlerde yapıyor (25 Ekim: MrBeast, Ruhi Cenet kare geldi); yuvarlağı QML keser."""
    return re.sub(r"=s\d+-", f"=s{boy}-", adres or "")


def goreli_zaman(ts):
    """'3 saat önce' gibi; YouTube'un kendi yazısı yoksa yayın zamanından."""
    if not ts:
        return ""
    fark = max(0, time.time() - ts)
    if fark < 3600:
        return tr("%n dakika önce", None, max(1, int(fark // 60)))
    if fark < 86400:
        return tr("%n saat önce", None, max(1, int(fark // 3600)))
    if fark < 7 * 86400:
        return tr("%n gün önce", None, max(1, int(fark // 86400)))
    if fark < 30 * 86400:
        return tr("%n hafta önce", None, max(1, int(fark // (7 * 86400))))
    if fark < 365 * 86400:
        return tr("%n ay önce", None, max(1, int(fark // (30 * 86400))))
    return tr("%n yıl önce", None, int(fark // (365 * 86400)))



def izlenme_yazisi(n):
    """YouTube'un Türkçe kısaltması: 878, 1,2 B, 18 B, 5,8 Mn, 2,3 Mr görüntüleme (aşağı yuvarlanır). Ondalık ayırıcı
    ekran dilinin (İngilizcede 1.2K)."""
    if n is None:
        return ""
    if n < 1000:
        return tr("%n görüntüleme", None, n)
    for bolen, yazi in ((10 ** 9, QT_TR_NOOP("%1 Mr görüntüleme")), (10 ** 6, QT_TR_NOOP("%1 Mn görüntüleme")),
                        (1000, QT_TR_NOOP("%1 B görüntüleme"))):
        if n >= bolen:
            x = n / bolen
            sayi = str(int(x)) if x >= 10 or int(x * 10) % 10 == 0 else f"{int(x)}{bicim.ondalik()}{int(x * 10) % 10}"
            return tr(yazi).replace("%1", sayi)


def kart(r, simdi, yeni=False):
    """Abonelik sayfasındaki video kartının bilgisi (KART_SUTUNLARI satırından)."""
    return {"id": r[0], "baslik": r[1], "kanal": r[2], "kanal_id": r[3], "sure": r[4] or "",
            # Canlı ve başlamamış yayında RSS'in sayısı izleyici değil, gösterilmez.
            "izlenme": izlenme_yazisi(r[11]) if not r[7] else "",
            "tarih": planlanan(r[6], simdi) if r[7] == 2 else goreli_zaman(r[5]) or kayitli_yazi(r[6]),
            "canli": r[7] == 1, "yakinda": r[7] == 2, "yeni": yeni, "yayin": r[5] or 0,
            "resim": f"https://i.ytimg.com/vi/{r[0]}/mqdefault.jpg"}


def kayitli_yazi(yazi):
    """Kayıttaki YouTube yazısı (yayin_yazi): yoklama onu hep Türkçe ister (youtube.YOKLAMA_DILI); başka ekran dilinde
    gösterilmez."""
    return yazi if kurulan_dil() == "tr" else ""


def planlanan(yazi, simdi):
    """Başlamamış yayının bilgi satırı (sıradan video gibi "5 saat önce" görünüyordu).
    YouTube'un yazısı "28.10.2026 18:00 tarihi için planlandı" (youtube._baglam saat farkıyla, bilgisayarın saati)."""
    m = re.search(r"(\d\d)\.(\d\d)\.(\d{4}) (\d\d):(\d\d)", yazi or "")
    if not m:
        return tr("Canlı yayına girecek")
    g, a, y, sa, dk = (int(x) for x in m.groups())
    zaman = time.mktime((y, a, g, sa, dk, 0, 0, 0, -1))
    if zaman <= simdi:   # saati geçti, yayın henüz başlamadı
        return tr("Canlı yayına girecek")
    bugun = time.localtime(simdi)
    gun_farki = (datetime.date(y, a, g) - datetime.date(bugun.tm_year, bugun.tm_mon, bugun.tm_mday)).days
    gun = tr("bugün") if gun_farki == 0 else tr("yarın") if gun_farki == 1 else bicim.gun_ay(datetime.date(y, a, g))
    return tr("Canlı yayına girecek · %1 %2").replace("%1", gun).replace("%2", bicim.saat((sa, dk)))


class Abonelik(QObject):
    kanallarDegisti = Signal()
    yeniVideolar = Signal(int)        # sayfa en son gösterildiğinden beri gelen video sayısı
    durumDegisti = Signal()
    iceAlindi = Signal(int, str)      # eklenen kanal sayısı, açıklama
    _ice_alindi = Signal(int, str)
    # Hiçbir tarayıcıda YouTube girişi yok: Firefox penceresi açılır (tarayici.py, FirefoxYardimi).
    girisBulunamadi = Signal(bool)    # True: Firefox'ta giriş çerezleri var ama YouTube girişsiz sayıyor
    _giris_bulunamadi = Signal(bool)
    # Firefox'ta girilen hesapta abonelik yok: başka hesapla girmek önerilir (tarayici.py).
    hesaptaAbonelikYok = Signal()
    _hesapta_abonelik_yok = Signal()
    _kanal_bitti = Signal(str, int)
    _sira_bos = Signal()

    def __init__(self):
        super().__init__()
        self.db_yolu = yoklama.db_yolu()
        os.makedirs(os.path.dirname(self.db_yolu), exist_ok=True)
        db = self._baglan()
        yoklama.tablolari_kur(db)
        db.close()
        self._kilit = threading.Lock()
        self._bekle_bitis = 0.0      # 429 sonrası durma
        self._bekle_sure = 600.0
        self._calisan = 0
        self._sonraki = 0.0          # sıradaki kanala en erken bakılacak an
        self._bozuk = 0              # art arda bozuk dönen RSS sayısı
        self._ag_yok = False
        self._geride = 0             # sırası iki tur geçmiş zilli ya da izlenen kanal (yoklama.geride_kalan)
        db = self._baglan()
        self._son_basari = db.execute("SELECT MAX(son_bakis) FROM kanal").fetchone()[0] or 0.0
        db.close()
        self._yeni = 0
        self._bakilan = 0
        self._ice_alindi.connect(self._ice_alindi_geldi)
        self._giris_bulunamadi.connect(self.girisBulunamadi)
        self._hesapta_abonelik_yok.connect(self.hesaptaAbonelikYok)
        self._kanal_bitti.connect(self._kanal_bitti_geldi)
        self._sira_bos.connect(self._sira_bos_geldi)
        self._program_isareti = 0.0
        self._gundem = []            # aboneliği olmayan kişinin sayfasındaki gündem (youtube.gundem)
        self._gundem_zamani = 0.0
        self._gundem_aliniyor = False
        self._gundem_geldi.connect(self._gundem_yaz)
        self._oneri_devam = None     # gündemin ardı: önerilerin sonraki partisinin anahtarı
        self._tohumlar = []          # önerileri bitince sıradaki videonun önerilerine geçilir
        self._gosterilen = set()
        self._devam_aliniyor = False
        self._gundem_devam_geldi.connect(self._gundem_devam_yaz)
        self._saat = QTimer(self)
        self._saat.timeout.connect(self._sirayi_isle)
        self._saat.start(1500)
        self._esitleme_saati = QTimer(self)
        self._esitleme_saati.timeout.connect(self._esitle_gerekirse)
        self._esitleme_saati.start(3600 * 1000)
        QTimer.singleShot(ESITLEME_GECIKME, self._esitle_gerekirse)
        # Bilgisayar açılınca arka plan yoklaması başlasın mı (kullanıcının seçimi ve abonelik varsa).
        self._baslangici_guncelle()

    def _baglan(self):
        # Her iş parçacığı kendi bağlantısını açar (sqlite3 bağlantıları iş parçacıkları arasında paylaşılmaz).
        return yoklama.baglan(self.db_yolu)

    # ---- program kapalıyken yoklama (arkada.py)
    def _arkada_al(self):
        db = self._baglan()
        acik = arkada.acik_mi(db)
        db.close()
        return acik

    def _arkada_ver(self, acik):
        db = self._baglan()
        yoklama.ayar_yaz(db, "arkada_yoklama", "1" if acik else "0")
        db.close()
        self._baslangici_guncelle()
        self.arkadaDegisti.emit()

    arkadaDegisti = Signal()
    # Abonelik sayfasındaki seçenek: "Program kapalıyken de yeni videolara bak" (varsayılan açık).
    arkadaYoklama = Property(bool, _arkada_al, _arkada_ver, notify=arkadaDegisti)

    def _baslangici_guncelle(self):
        arkada.baslangica_yaz(self._arkada_al() and self._kanal_sayisi() > 0)

    def kapanirken(self, arkadayi_baslat=True):
        """Program kapanırken: yoklamayı arka plana bırakır (seçenek açıksa ve abonelik varsa). arkadayi_baslat False:
        güncelleme kurulacak, arka plan parçasını kurulumdan sonra yeni sürüm başlatır (guncelleme.py)."""
        db = self._baglan()
        yoklama.ayar_yaz(db, "program", "")
        db.close()
        if self._arkada_al() and self._kanal_sayisi() > 0:
            self._baslangici_guncelle()
            if arkadayi_baslat:
                arkada.baslat()

    # ---- QML'e açılanlar
    def _kanal_sayisi(self):
        db = self._baglan()
        n = db.execute("SELECT COUNT(*) FROM kanal").fetchone()[0]
        db.close()
        return n
    kanalSayisi = Property(int, _kanal_sayisi, notify=kanallarDegisti)
    bakilan = Property(int, lambda s: s._bakilan, notify=durumDegisti)

    def _durum_al(self):
        """Abonelik sayfasının başındaki tek satır; yalnız liste eskimiş olabilecekken (sade, doğrudan
        anlaşılır gösterge). Her şey yolundayken boş: programın iç durumu gösterilmez. YouTube'un geçici aksaması
        (429, RSS'in art arda bozuk dönmesi) de gösterilmez: önceden "YouTube şu an cevap vermiyor" yazılıyordu, oysa
        çoğu zaman yalnız RSS bozuktu ve videolar kanal sayfasından gelmeye devam ediyordu; yazı kişiyi boşuna
        tedirgin ediyordu (28 Ekim). Yoklama kendiliğinden yavaşlayıp sürer."""
        simdi = time.time()
        liste = (" " + tr("Liste %1ki hâliyle.").replace("%1", goreli_zaman(self._son_basari))
                 if self._son_basari and simdi - self._son_basari > 120 else "")
        if self._ag_yok:
            return tr("İnternet yok.") + liste
        if simdi < self._bekle_bitis or self._bozuk >= 5:
            return ""
        if self._geride:
            return tr("Yeni videolara bakılıyor…")
        return ""
    durum = Property(str, _durum_al, notify=durumDegisti)
    yeni = Property(int, lambda s: s._yeni, notify=yeniVideolar)

    @Slot(result="QVariantMap")
    def akis(self):
        """Abonelik sayfası, yukarıdan aşağı: şu an canlı, zil taktığın kanallar (son iki gün), yeni
        gelenler (sayfaya son bakıştan beri gelenler; önceden "N yeni video geldi, göster"e basınca hangilerinin yeni
        olduğu görünmüyordu), izlediklerine göre (ilgi duyulan kanalların son üç günü, ilgi.py; önceden akışa karışıyordu,
        öne çıktığı görünmüyordu), sonra kalanlar zamana göre. İzlenen video (geçmişte olan) düşer. Bir video yalnız bir
        bölümde. Zil canlının hemen altında: zil kişinin kendi seçimi, öbür bölümlerin önünde gelir;
        önceden zilli kanalın yeni videosu önce "Yeni gelenler"de işaretsiz çıkıp sonraki açılışta zil bölümüne kayıyordu,
        en çok izlenen kanalın zilli videosu da "İzlediklerine göre"ye düşüp zil bölümüne hiç girmiyordu."""
        simdi = time.time()
        db = self._baglan()
        son_bakis = float(yoklama.ayar(db, "abonelik_son_bakis") or simdi)
        yoklama.ayar_yaz(db, "abonelik_son_bakis", str(simdi))
        # Şu an canlı: izlenmiş olsa da yayın sürdükçe durur; kanal başına bir yayın (7/24 yayın
        # yapan kanallar şeridi doldurmasın), zilli kanallar önde.
        canlilar, canli_kanal = [], set()
        for r in db.execute(f"""SELECT {KART_SUTUNLARI} FROM abone_video v JOIN kanal k ON k.id = v.kanal_id WHERE v.canli = 1
                ORDER BY k.zil DESC, v.yayin DESC"""):
            if r[3] not in canli_kanal:
                canli_kanal.add(r[3])
                canlilar.append(r)
        canli_idler = {r[0] for r in canlilar}
        # Baştaki bölümlerin baktığı son üç gün (Shorts, izlediklerine göre, yeni gelenler). Önceden en yeni 600 video
        # okunuyordu; 731 kanallık bir kayıtta bu 1,8 gündü, "son üç gün" diyen bölümler fiilen iki günü görüyordu.
        hepsi = db.execute(f"""SELECT {KART_SUTUNLARI} FROM abone_video v JOIN kanal k ON k.id = v.kanal_id
            WHERE v.id NOT IN (SELECT id FROM gecmis) AND v.yayin > ? ORDER BY v.yayin DESC""",
            (simdi - max(SHORTS_YAS, ilgi.ONE_ALMA_EN_COK, YENI_YAS),)).fetchall()
        # Shorts uzun videolarla karışmaz, ayrı şeritte durur (YouTube'daki gibi).
        satirlar = [r for r in hepsi if not r[10] and r[0] not in canli_idler]
        shorts = [r for r in hepsi if r[10] and (r[5] or 0) > simdi - SHORTS_YAS][:24]
        # Zilliler ayrı sorgudan: yukarıdaki son 600 video (çok abonelikte iki günden kısa bir süre) haftayı kapsamıyor.
        zil_satirlari = db.execute(f"""SELECT {KART_SUTUNLARI} FROM abone_video v JOIN kanal k ON k.id = v.kanal_id
            WHERE k.zil = 1 AND NOT COALESCE(v.shorts, 0) AND v.yayin > ? AND v.id NOT IN (SELECT id FROM gecmis)
            ORDER BY v.yayin DESC""", (simdi - ZIL_YENI,)).fetchall()
        puan = ilgi.kanal_ilgileri(db)
        db.close()
        self._yeni = 0
        self.yeniVideolar.emit(0)
        alindi = set(canli_idler)

        def al(satir):
            alindi.add(satir[0])
            return satir
        zilliler = [al(r) for r in zil_satirlari if r[0] not in canli_idler][:ZIL_EN_COK]
        # Kanal sayfasından geriye doğru dolan eski videolar yeni sayılmaz: yalnız son iki günde yayımlananlar.
        yeniler = [al(r) for r in satirlar if r[0] not in alindi and (r[8] or 0) > son_bakis and (r[5] or 0) > simdi - YENI_YAS][:BOLUM]
        ilgiler, kanal_sayisi = [], {}
        for r in ilgi.sirala([r for r in satirlar if r[0] not in alindi and puan.get(r[3], 0.0) > 0
                              and (r[5] or 0) > simdi - ilgi.ONE_ALMA_EN_COK], puan, kanal=lambda r: r[3], yayin=lambda r: r[5]):
            if len(ilgiler) < BOLUM and kanal_sayisi.get(r[3], 0) < ilgi.KANAL_BASINA:
                kanal_sayisi[r[3]] = kanal_sayisi.get(r[3], 0) + 1
                ilgiler.append(al(r))
        # "Bütün abonelikler"in başı; devamı aşağı inildikçe gelir (devami).
        digerleri = [r for r in satirlar if r[0] not in alindi][:400]

        def shorts_sozluk(r):
            return {"id": r[0], "baslik": r[1], "kanal": r[2], "kanal_id": r[3], "sure": "", "izlenme": izlenme_yazisi(r[11]),
                    "tarih": goreli_zaman(r[5]) or kayitli_yazi(r[6]), "canli": False, "shorts": True, "resim": youtube.shorts_resmi(r[0])}
        return {"canlilar": [kart(r, simdi) for r in canlilar], "yeniler": [kart(r, simdi, True) for r in yeniler],
                "ilgiler": [kart(r, simdi) for r in ilgiler], "zilliler": [kart(r, simdi) for r in zilliler],
                "digerleri": [kart(r, simdi) for r in digerleri],
                "shorts": [shorts_sozluk(r) for r in shorts]}

    @Slot("QVariantList", float, result="QVariantList")
    def devami(self, gorulen, son_yayin):
        """"Bütün abonelikler"in sıradaki partisi ("aşağı indikçe göstersek"): sayfada
        gösterilen en eski videodan (son_yayin) eskiler ya da aynı andakiler, izlenmemiş uzun videolar, sayfada
        olmayan en yeni DEVAM tanesi; bitince boş. Önceden sayfa en yeni 400 videoda bitiyordu (731 kanallık bir
        kayıtta 1,8 gün)."""
        gorulen = set(gorulen or [])
        simdi = time.time()
        db = self._baglan()
        satirlar = db.execute(f"""SELECT {KART_SUTUNLARI} FROM abone_video v JOIN kanal k ON k.id = v.kanal_id
            WHERE NOT COALESCE(v.shorts, 0) AND v.yayin <= ? AND v.id NOT IN (SELECT id FROM gecmis)
            ORDER BY v.yayin DESC LIMIT ?""", (son_yayin, DEVAM + len(gorulen))).fetchall()
        db.close()
        return [kart(r, simdi) for r in satirlar if r[0] not in gorulen][:DEVAM]

    @Slot("QVariantList", result="QVariantList")
    def shortsDevami(self, gorulen):
        """Shorts görünümünde abonelik Shorts'larının sıradaki partisi (24'te duruyordu): son üç
        günün izlenmemiş Shorts'larından listede olmayan en yeni 24'ü; bitince boş."""
        gorulen = set(gorulen or [])
        db = self._baglan()
        satirlar = db.execute("""SELECT v.id, v.baslik, k.ad, v.kanal_id, v.yayin, v.yayin_yazi FROM abone_video v
            JOIN kanal k ON k.id = v.kanal_id WHERE v.shorts = 1 AND v.yayin > ? AND v.id NOT IN (SELECT id FROM gecmis)
            ORDER BY v.yayin DESC""", (time.time() - SHORTS_YAS,)).fetchall()
        db.close()
        return [{"id": r[0], "baslik": r[1], "kanal": r[2], "kanal_id": r[3], "sure": "", "izlenme": "",
                 "tarih": goreli_zaman(r[4]) or r[5], "canli": False, "shorts": True, "resim": youtube.shorts_resmi(r[0])}
                for r in satirlar if r[0] not in gorulen][:24]

    # ---- Sol kenardaki abonelik listesi
    kenarDegisti = Signal()

    @Slot(result="QVariantList")
    def kenarListesi(self):
        """Bütün abonelikler, sırayla: izlediğin kanallar (ilgi puanına göre, ilgi.py: sık ve yakın zamanda izlenen
        önde), yeni videosu olanlar (mavi nokta; en yenisi üstte), kalanlar Türkçe abeceyle. Mavi nokta: kanal
        sayfasına son girişten (kanal.son_giris) beri gelen, son yedi günde yayımlanmış, izlenmemiş uzun video;
        Shorts yakmaz (son üç günde 362 Shorts vardı, listenin yarısı mavi olurdu). Canlı yayındaki kanalın resminde
        kırmızı halka."""
        simdi = time.time()
        db = self._baglan()
        puan = ilgi.kanal_ilgileri(db, simdi)
        resim = dict(db.execute("SELECT kanal_id, resim FROM kanal_resim"))
        yeni = dict(db.execute("""SELECT v.kanal_id, MAX(v.yayin) FROM abone_video v JOIN kanal k ON k.id = v.kanal_id
            WHERE v.shorts = 0 AND v.canli = 0 AND v.yayin > ? AND v.fark > k.son_giris
              AND v.id NOT IN (SELECT id FROM gecmis) GROUP BY v.kanal_id""", (simdi - NOKTA_YAS,)))
        canli = {r[0] for r in db.execute("SELECT DISTINCT kanal_id FROM abone_video WHERE canli = 1")}
        kanallar = db.execute("SELECT id, ad FROM kanal").fetchall()
        db.close()

        def sira(k):
            if puan.get(k[0], 0) > 0:
                return (0, -puan[k[0]], [])
            if k[0] in yeni:
                return (1, -yeni[k[0]], [])
            return (2, 0, abece_anahtari(k[1]))
        return [{"id": k[0], "ad": k[1] or "", "resim": kucuk_resim(resim.get(k[0])), "nokta": k[0] in yeni,
                 "canli": k[0] in canli} for k in sorted(kanallar, key=sira)]

    @Slot(str, str)
    def kanalaGirildi(self, kanal_id, resim):
        """Kanal sayfası açıldı: mavi nokta söner; sayfadan gelen resim saklanır (listede baş harf yerine resim)."""
        db = self._baglan()
        db.execute("UPDATE kanal SET son_giris = ? WHERE id = ?", (time.time(), kanal_id))
        if resim:
            db.execute("INSERT OR REPLACE INTO kanal_resim (kanal_id, resim) VALUES (?, ?)", (kanal_id, resim))
        db.commit()
        db.close()
        self.kenarDegisti.emit()

    @Slot(str, result="QVariantMap")
    def canliYayin(self, kanal_id):
        """Kanalın şu an süren yayını (kanal sayfasındaki kırmızı halka; tıklayınca yayın açılır) ya da boş."""
        db = self._baglan()
        r = db.execute("SELECT id, baslik FROM abone_video WHERE kanal_id = ? AND canli = 1 ORDER BY yayin DESC LIMIT 1",
                       (kanal_id,)).fetchone()
        db.close()
        return {"id": r[0], "baslik": r[1], "kanal_id": kanal_id, "canli": True} if r else {}

    # ---- Keşfet'in Shorts'ları: abone olmadığın, ilgini çekebilecek kanalların güncel Shorts'ları. Program
    # bu kanallara yoklamada bakmadığı için her kanalın yalnız-Shorts RSS'i istenir (kanal başına bir istek, en çok
    # 10 kanal, üç saatte bir); sonuç kayda yazılır, sayfa açılınca kayıttan gösterilir.
    # ---- gündem: aboneliği olmayan kişinin abonelik sayfası boş durmasın (youtube.gundem)
    gundemDegisti = Signal()
    _gundem_geldi = Signal(list)

    @Slot(result=list)
    def gundem(self):
        return self._gundem

    @Slot()
    def gundemYenile(self):
        """Sayfa açılınca: yarım saatten eskiyse arka planda yeniden alınır; gelmezse eldeki kalır."""
        if self._gundem_aliniyor or (self._gundem and time.time() - self._gundem_zamani < GUNDEM_ARALIGI):
            return
        self._gundem_aliniyor = True

        def is_():
            try:
                bolumler = youtube.gundem()
            except Exception:   # YouTube'un biçimi değişirse sayfa yine açılsın, sonra yeniden denensin
                bolumler = []
            self._gundem_geldi.emit(bolumler)
        threading.Thread(target=is_, daemon=True).start()

    gundemDevamGeldi = Signal(list)
    _gundem_devam_geldi = Signal(list)

    @Slot()
    def gundemDevami(self):
        """Gündemin ardı, aşağı inildikçe (28 Ekim: "aşağısı, ardı gelmiyor"): son izlenen videonun (yoksa
        gündemin ilk videosunun) önerileri, partiler bitince gösterilenlerden birinin önerileri; böylece sonu gelmez.
        Canlı yayınlar ve Shorts alınmaz (ızgara yatay kart), aynı video iki kez gösterilmez."""
        if self._devam_aliniyor:
            return
        self._devam_aliniyor = True

        def is_():
            yeni = []
            try:
                for _ in range(3):   # bir partide hepsi görülmüşse sıradakine
                    if self._oneri_devam:
                        videolar, self._oneri_devam = youtube.oneri_devami(self._oneri_devam)
                    else:
                        tohum = self._sonraki_tohum()
                        if not tohum:
                            break
                        s = youtube.video_sayfasi(tohum)
                        videolar, self._oneri_devam = s["oneriler"], s["oneri_devam"]
                    for v in videolar:
                        if v["id"] in self._gosterilen or v.get("canli") or v.get("shorts") or not v.get("sure"):
                            continue
                        self._gosterilen.add(v["id"])
                        self._tohumlar.append(v["id"])
                        yeni.append(v)
                    if yeni:
                        break
            except Exception:   # internet yok ya da biçim değişti: sonraki inişte yeniden denenir
                pass
            self._gundem_devam_geldi.emit(yeni)
        threading.Thread(target=is_, daemon=True).start()

    def _sonraki_tohum(self):
        if not self._gosterilen:   # ilk parti: son izlenen video, yoksa gündemin ilk videosu
            for b in self._gundem:
                self._gosterilen.update(v["id"] for v in b["videolar"])
            db = self._baglan()
            r = db.execute("SELECT id FROM gecmis ORDER BY son DESC LIMIT 1").fetchone() \
                if db.execute("SELECT 1 FROM sqlite_master WHERE name = 'gecmis'").fetchone() else None
            db.close()
            if r:
                return r[0]
            return next((b["videolar"][0]["id"] for b in self._gundem if b["videolar"]), None)
        if not self._tohumlar:
            return None
        return self._tohumlar.pop(random.randrange(len(self._tohumlar)))

    def _gundem_devam_yaz(self, videolar):
        self._devam_aliniyor = False
        self.gundemDevamGeldi.emit(videolar)

    def _gundem_yaz(self, bolumler):
        self._gundem_aliniyor = False
        if bolumler:
            self._gundem, self._gundem_zamani = bolumler, time.time()
            self.gundemDegisti.emit()

    kesfetDegisti = Signal()

    def _kesfet_tablosu(self, db):
        db.execute("""CREATE TABLE IF NOT EXISTS kesfet_short (id TEXT PRIMARY KEY, kanal_id TEXT, kanal TEXT,
            baslik TEXT, yayin REAL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS kesfet_video (id TEXT PRIMARY KEY, kanal_id TEXT, kanal TEXT,
            baslik TEXT, yayin REAL, izlenme INTEGER)""")

    @Slot(result=list)
    def kesfetVideolar(self):
        """Keşfet'in "Videolar" bölümü: ilgili kanalların (abone olunmamış) en son KESFET_KANAL_BASINA uzun videosu,
        izlenmemiş olanlar, en yenisi önde. Süre RSS'te yok, kartta gösterilmez."""
        kanallar = [k["id"] for k in self.ilgiliKanallar()]
        if not kanallar:
            return []
        db = self._baglan()
        self._kesfet_tablosu(db)
        satirlar = db.execute(f"""SELECT id, kanal_id, kanal, baslik, yayin, izlenme FROM kesfet_video
            WHERE kanal_id IN ({",".join("?" * len(kanallar))}) AND id NOT IN (SELECT id FROM gecmis)
            ORDER BY yayin DESC""", kanallar).fetchall()
        db.close()
        sonuc, sayi = [], {}
        for r in satirlar:
            if sayi.get(r[1], 0) < KESFET_KANAL_BASINA:
                sayi[r[1]] = sayi.get(r[1], 0) + 1
                sonuc.append({"id": r[0], "kanal_id": r[1], "kanal": r[2], "baslik": r[3], "sure": "",
                              "izlenme": izlenme_yazisi(r[5]), "tarih": goreli_zaman(r[4]), "canli": False,
                              "resim": f"https://i.ytimg.com/vi/{r[0]}/mqdefault.jpg"})
        return sonuc

    @Slot(result=list)
    def kesfetShorts(self):
        kanallar = [k["id"] for k in self.ilgiliKanallar()]
        if not kanallar:
            return []
        db = self._baglan()
        self._kesfet_tablosu(db)
        simdi = time.time()
        satirlar = db.execute(f"""SELECT id, kanal_id, kanal, baslik, yayin FROM kesfet_short
            WHERE kanal_id IN ({",".join("?" * len(kanallar))}) AND yayin > ? AND id NOT IN (SELECT id FROM gecmis)
            ORDER BY yayin DESC""", (*kanallar, simdi - KESFET_SHORTS_YAS)).fetchall()
        db.close()
        sonuc, sayi = [], {}
        for r in satirlar:
            if sayi.get(r[1], 0) < 3:   # bir kanal şeridi doldurmasın
                sayi[r[1]] = sayi.get(r[1], 0) + 1
                sonuc.append({"id": r[0], "kanal_id": r[1], "kanal": r[2], "baslik": r[3], "sure": "", "izlenme": "",
                              "tarih": goreli_zaman(r[4]), "canli": False, "shorts": True,
                              "resim": youtube.shorts_resmi(r[0])})
        return sonuc[:30]

    @Slot()
    def kesfetYenile(self):
        """Keşfet açılınca: son bakış üç saatten eskiyse ilgili kanalların Shorts ve uzun video listesine arka planda
        bakılır (kanal başına iki istek, aralıklı)."""
        db = self._baglan()
        son = float(yoklama.ayar(db, "kesfet_son") or 0)
        db.close()
        self._kesfet_tablosu(db := self._baglan())
        videosuz = db.execute("SELECT 1 FROM kesfet_video LIMIT 1").fetchone() is None   # ilk açılış: üç saat beklenmez
        db.close()
        if (time.time() - son < KESFET_ARALIK and not videosuz) or getattr(self, "_kesfet_suruyor", False):
            return
        self._kesfet_suruyor = True
        kanallar = [k["id"] for k in self.ilgiliKanallar()]

        def is_():
            try:
                for i, kanal_id in enumerate(kanallar):
                    if i:
                        time.sleep(1.5)   # istekler arka arkaya yığılmasın (24 Ekim kilidi)
                    try:
                        rss = youtube.kanal_rss(kanal_id, yalniz_shorts=True)
                        time.sleep(1.5)
                        uzun = youtube.kanal_rss(kanal_id, yalniz_uzun=True)
                    except youtube.CokIstek:
                        break
                    except Exception:
                        continue
                    db = self._baglan()
                    self._kesfet_tablosu(db)
                    if rss:
                        db.executemany("""INSERT OR REPLACE INTO kesfet_short (id, kanal_id, kanal, baslik, yayin)
                            VALUES (?, ?, ?, ?, ?)""", [(v["id"], kanal_id, v["kanal"], v["baslik"], v["yayin"])
                                                        for v in rss["videolar"]])
                    if uzun:
                        db.executemany("""INSERT OR REPLACE INTO kesfet_video (id, kanal_id, kanal, baslik, yayin, izlenme)
                            VALUES (?, ?, ?, ?, ?, ?)""", [(v["id"], kanal_id, v["kanal"], v["baslik"], v["yayin"],
                                                            v["izlenme"]) for v in uzun["videolar"]])
                    db.commit()
                    db.close()
                db = self._baglan()
                self._kesfet_tablosu(db)
                db.execute("DELETE FROM kesfet_short WHERE yayin < ?", (time.time() - 30 * 86400,))
                db.execute("DELETE FROM kesfet_video WHERE yayin < ?", (time.time() - 30 * 86400,))
                db.commit()
                yoklama.ayar_yaz(db, "kesfet_son", str(time.time()))
                db.close()
            finally:
                self._kesfet_suruyor = False
                self.kesfetDegisti.emit()
        threading.Thread(target=is_, daemon=True).start()

    @Slot(result=list)
    def ilgiliKanallar(self):
        """Abone olunmamış, izlediklerine göre ilgini çekebilecek kanallar (ilgi.py), bilinen resimleriyle."""
        db = self._baglan()
        try:
            kanallar = ilgi.ilgili_kanallar(db)
            resim = dict(db.execute("SELECT kanal_id, resim FROM kanal_resim"))
        except sqlite3.OperationalError:   # oneri_kanal ya da kanal_resim henüz kurulmadıysa (kayit.py kurar)
            return []
        finally:
            db.close()
        for k in kanallar:
            k["resim"] = resim.get(k["id"], "")
        return kanallar

    @Slot(str, result=bool)
    def zilli(self, kanal_id):
        db = self._baglan()
        r = db.execute("SELECT zil FROM kanal WHERE id = ?", (kanal_id,)).fetchone()
        db.close()
        return bool(r and r[0])

    @Slot(str)
    def zilDegistir(self, kanal_id):
        """Kanal sayfasındaki zil: zilli kanala 15 dakikada bir bakılır (program kapalıyken de), yeni videoları
        abonelik sayfasının başında ayrı durur. Yalnız programda kalır, YouTube hesabına yazılmaz."""
        db = self._baglan()
        db.execute("UPDATE kanal SET zil = 1 - COALESCE(zil, 0) WHERE id = ?", (kanal_id,))
        db.commit()
        db.close()
        self.kanallarDegisti.emit()

    @Slot()
    def tarayicidanAl(self):
        threading.Thread(target=self._tarayicidan_al, daemon=True).start()

    def _esitle_gerekirse(self):
        """Saatte bir bakılır: abonelik varsa ve son okuma bir günden eskiyse liste arka planda yeniden okunur."""
        db = self._baglan()
        son = float(yoklama.ayar(db, "abonelik_esitleme") or 0)
        db.close()
        if self._kanal_sayisi() and time.time() - son > ESITLEME_ARALIGI:
            threading.Thread(target=self._tarayicidan_al, kwargs={"sessiz": True}, daemon=True).start()

    @Slot(str, result=bool)
    def aboneMi(self, kanal_id):
        db = self._baglan()
        var = db.execute("SELECT 1 FROM kanal WHERE id = ?", (kanal_id,)).fetchone() is not None
        db.close()
        return var

    @Slot(str, str)
    def aboneOl(self, kanal_id, ad):
        """Kanal sayfasındaki düğme: yalnız programın kaydına eklenir (YouTube hesabına yazılmaz);
        son bakışı 0 olduğu için yoklama sırasına hemen girer."""
        if kanal_id.startswith("UC"):
            db = self._baglan()
            db.execute("DELETE FROM cikilan_kanal WHERE id = ?", (kanal_id,))
            db.commit()
            db.close()
            self._ekle([(kanal_id, ad)])
            self.kanallarDegisti.emit()
            self._baslangici_guncelle()

    @Slot(str)
    def abonelikBirak(self, kanal_id):
        db = self._baglan()
        db.execute("DELETE FROM abone_video WHERE kanal_id = ?", (kanal_id,))
        db.execute("DELETE FROM kanal WHERE id = ?", (kanal_id,))
        # Günlük okuma bu kanalı YouTube'dan geri eklemesin.
        db.execute("INSERT OR REPLACE INTO cikilan_kanal (id, zaman) VALUES (?, ?)", (kanal_id, time.time()))
        db.commit()
        db.close()
        self.kanallarDegisti.emit()

    # ---- içe alma
    def _ekle(self, kanallar, zilliler=frozenset()):
        """Yalnız ekler. YouTube'da zili açık kanal yeni ekleniyorsa programda da zilli başlar; programda
        önceden olan kanalın zili değişmez (programda takılan ya da çıkarılan zil korunur)."""
        db = self._baglan()
        once = db.execute("SELECT COUNT(*) FROM kanal").fetchone()[0]
        var_olan = {r[0] for r in db.execute("SELECT id FROM kanal")}
        db.executemany("INSERT OR IGNORE INTO kanal (id, ad) VALUES (?, ?)", kanallar)
        zillenen = zilliler - var_olan
        db.executemany("UPDATE kanal SET zil = 1 WHERE id = ?", [(i,) for i in zillenen])
        db.commit()
        sonra = db.execute("SELECT COUNT(*) FROM kanal").fetchone()[0]
        db.close()
        return sonra - once, len(zillenen)

    @staticmethod
    def _zilliler(klasor):
        """yt-dlp'nin kaydettiği abonelik sayfalarından (--write-pages) zili "Tüm bildirimler"de olan kanallar.
        "Kişiselleştirilmiş" YouTube'un varsayılanı ve algoritmasına bağlı, zil sayılmaz."""
        zilli = set()
        for ad in os.listdir(klasor):
            if not ad.endswith(".dump"):
                continue
            with open(os.path.join(klasor, ad), encoding="utf-8", errors="replace") as f:
                metin = f.read()
            try:
                if metin.lstrip().startswith("{"):
                    veri = json.loads(metin)
                else:
                    m = re.search(r"ytInitialData\"?\]?\s*=\s*(\{.*?\});\s*</script>", metin, re.S)
                    veri = json.loads(m.group(1)) if m else None
            except ValueError:
                continue
            yigin = [veri]
            while yigin:
                o = yigin.pop()
                if isinstance(o, list):
                    yigin.extend(o)
                elif isinstance(o, dict):
                    k = o.get("channelRenderer")
                    if isinstance(k, dict) and k.get("channelId") and "NOTIFICATIONS_ACTIVE" in Abonelik._zil_durumu(k):
                        zilli.add(k["channelId"])
                    yigin.extend(o.values())
        return zilli

    @staticmethod
    def _zil_durumu(kanal):
        """Kanal kartındaki zil düğmesinin şimdiki durumunun simgesi (NOTIFICATIONS_ACTIVE, _NONE, _OFF)."""
        yigin = [kanal]
        while yigin:
            o = yigin.pop()
            if isinstance(o, list):
                yigin.extend(o)
            elif isinstance(o, dict):
                z = o.get("subscriptionNotificationToggleButtonRenderer")
                if isinstance(z, dict):
                    for s in z.get("states") or []:
                        if s.get("stateId") == z.get("currentStateId"):
                            return ((s.get("state") or {}).get("buttonRenderer") or {}).get("icon", {}).get("iconType", "")
                    return ""
                yigin.extend(o.values())
        return ""

    def _tarayicidan_al(self, sessiz=False):
        """yt-dlp tarayıcının YouTube çerezleriyle youtube.com/feed/channels'ı okur; çerezler yalnız
        bu bilgisayarda kalır, hiçbir yere kaydedilmez. Okunan sayfalar zil durumu için geçici bir
        klasöre yazılır (yt-dlp'nin JSON'unda zil yok) ve hemen silinir. sessiz: günlük kendiliğinden okuma;
        önce son başarılı tarayıcı denenir, programda çıkılan kanallar eklenmez, yalnız yeni kanal
        geldiyse sayfada yazı çıkar, okunamazsa hiçbir şey yazmaz (ertesi gün yeniden).
        Çerez dosyası olmayan tarayıcı denenmez. Firefox'un çerezleri önce kopyalanıp birleştirilir (tarayici.py,
        girisli_kopya: açık Firefox'ta az önce yapılan giriş yalnız -wal dosyasında); girişi yoksa denenmez."""
        bayrak = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        firefox_girisli = False      # Firefox'ta giriş var ama liste okunamadı
        # Firefox'ta giriş çerezleri duruyor ama YouTube girişsiz sayıyor (çıkış yapılmış ya da süresi dolmuş; 28 Ekim:
        # Firefox'ta hesaptan çıkıldıktan sonra çerezler kaldı, yt-dlp "Failed to resolve url" dedi).
        firefox_gecersiz = False
        bos = ""                     # giriş var, listede kanal yok: hangi tarayıcıda
        db = self._baglan()
        onceki = yoklama.ayar(db, "abonelik_tarayici") or ""
        if sessiz:
            yoklama.ayar_yaz(db, "abonelik_esitleme", str(time.time()))   # başarısız da olsa günde bir deneme
        cikilan = {r[0] for r in db.execute("SELECT id FROM cikilan_kanal")} if sessiz else set()
        db.close()
        for t in ([onceki] if onceki in TARAYICILAR else []) + [x for x in TARAYICILAR if x != onceki]:
            if t != "firefox" and not tarayici.chromium_cerezi_var(t):
                continue
            with tempfile.TemporaryDirectory(prefix="lvt-abonelik-") as gecici:
                sayfalar = os.path.join(gecici, "sayfalar")
                os.mkdir(sayfalar)
                kaynak = t
                if t == "firefox":
                    os.mkdir(os.path.join(gecici, "firefox"))
                    kopya = tarayici.girisli_kopya(os.path.join(gecici, "firefox"))
                    if not kopya:
                        continue
                    kaynak = "firefox:" + kopya
                try:
                    r = subprocess.run([ytdlp_yolu(), *ytdlp_js(), "--cookies-from-browser", kaynak, "--flat-playlist", "-J",
                                        "--no-warnings", "--write-pages", "https://www.youtube.com/feed/channels"],
                                       capture_output=True, text=True, timeout=120, creationflags=bayrak, cwd=sayfalar)
                except (OSError, subprocess.TimeoutExpired):
                    firefox_girisli |= t == "firefox"
                    continue
                zilliler = self._zilliler(sayfalar) if r.returncode == 0 else set()
            if r.returncode != 0 or not r.stdout.strip():
                if t == "firefox" and GIRISSIZ.search(r.stderr or ""):
                    firefox_gecersiz = True
                else:
                    firefox_girisli |= t == "firefox"
                continue
            girdiler = json.loads(r.stdout).get("entries") or []
            kanallar = [(e.get("id") or e.get("channel_id"), e.get("title") or e.get("channel") or "")
                        for e in girdiler if (e.get("id") or "").startswith("UC")]
            if not kanallar:
                bos = bos or t
                continue
            db = self._baglan()
            yoklama.ayar_yaz(db, "abonelik_tarayici", t)
            yoklama.ayar_yaz(db, "abonelik_esitleme", str(time.time()))
            db.close()
            if sessiz:
                # Tarayıcıda başka bir hesap açıksa (Yönet menüsündeki "yeni kişi olarak") onun abonelikleri bu kişiye
                # eklenmesin: okunan listenin yarısından azı zaten kayıtlıysa başka hesap sayılır, hiçbir şey eklenmez.
                db = self._baglan()
                kayitli = {r[0] for r in db.execute("SELECT id FROM kanal")}
                db.close()
                if len({k[0] for k in kanallar} & kayitli) * 2 < len(kanallar):
                    return
                eklenen, zillenen = self._ekle([k for k in kanallar if k[0] not in cikilan], zilliler)
                if eklenen:
                    self._ice_alindi.emit(eklenen, tr("YouTube hesabında abone olduğun %n yeni kanal eklendi.", None, eklenen))
                return
            eklenen, zillenen = self._ekle(kanallar, zilliler)
            zil = " " + tr("YouTube'da zili açık %n yeni kanal programda da zilli.", None, zillenen) if zillenen else ""
            okundu = tr("%1 tarayıcısındaki YouTube hesabından %n kanal okundu.", None, len(kanallar))
            self._ice_alindi.emit(eklenen, okundu.replace("%1", t.capitalize()) + zil)
            return
        if sessiz:
            return
        if bos == "firefox":
            self._hesapta_abonelik_yok.emit()
        elif bos:
            self._ice_alindi.emit(-1, tr("%1 tarayıcısındaki YouTube hesabında abone olduğun kanal görünmüyor.").replace("%1", bos.capitalize()))
        elif not tarayici.internet_var():
            self._ice_alindi.emit(-1, tr("İnternet yok. Bağlanınca yeniden dene."))
        elif firefox_girisli:
            self._ice_alindi.emit(-1, tr("Firefox'taki YouTube girişi bulundu ama abonelik listesi okunamadı. "
                                         "Biraz sonra yeniden dene."))
        else:
            self._giris_bulunamadi.emit(firefox_gecersiz)

    def _ice_alindi_geldi(self, eklenen, metin):
        self.kanallarDegisti.emit()
        self._baslangici_guncelle()
        self.iceAlindi.emit(eklenen, metin)

    # ---- yoklama (kural yoklama.py'de)
    def _sirayi_isle(self):
        """1,5 sn'de bir: boşta iş parçacığı varsa sırası gelen kanallardan birine baktırır. Dakikada bir
        "program açık" işareti yazılır; arka plan yoklaması (arkada.py) bunu görünce bekler. Kayda yazan her şey
        iş parçacığında: pencerenin iş parçacığı kaydı beklerse pencere donar (düğmeler geç işliyordu)."""
        simdi = time.time()
        isaret = simdi - self._program_isareti > 60
        if isaret:
            self._program_isareti = simdi
            self.durumDegisti.emit()   # "Liste 5 dakika önceki hâliyle" ilerlesin
        if simdi < self._bekle_bitis or simdi < self._sonraki or self._calisan >= ESZAMANLI:
            if isaret:
                threading.Thread(target=self._isaret_yaz, args=(simdi,), daemon=True).start()
            return
        self._calisan += 1
        threading.Thread(target=self._sirali_bak, args=(simdi if isaret else 0,), daemon=True).start()

    def _isaret_yaz(self, simdi):
        db = self._baglan()
        yoklama.ayar_yaz(db, "program", f"{os.getpid()} {simdi}")
        db.close()

    def _sirali_bak(self, isaret):
        try:
            if isaret:
                self._isaret_yaz(isaret)
            db = self._baglan()
            r = yoklama.siradaki(db, acik=True)
            self._geride = yoklama.geride_kalan(db) if r else 0
            db.close()
        except sqlite3.Error:
            r = None
        if r:
            self._kanala_bak(*r)
        else:
            self._sira_bos.emit()

    def _sira_bos_geldi(self):
        self._calisan -= 1
        self._sonraki = time.time() + 15   # sırası gelen yok; kaydı 1,5 sn'de bir sorgulamaya gerek yok
        self.durumDegisti.emit()

    def _kanala_bak(self, kanal_id, _rss_bozuk, onceki):
        yeni = 0
        try:
            yeni, rss_saglam = yoklama.kanala_bak(kanal_id, self.db_yolu)
            self._bekle_sure = 600.0
            self._ag_yok = False
            self._bozuk = 0 if rss_saglam else self._bozuk + 1
            if rss_saglam:
                self._son_basari = time.time()
        except youtube.CokIstek:
            self._ag_yok = False
            self._bekle_bitis = time.time() + self._bekle_sure
            self._bekle_sure *= 2
        except arkada.AG_HATALARI:
            self._ag_yok = True
            # İnternet yok: kanal "bakıldı" sayılmaz, bir dakika sonra yeniden.
            db = self._baglan()
            yoklama.geri_al(db, kanal_id, onceki)
            db.close()
            self._bekle_bitis = time.time() + 60
        except Exception:
            pass  # tek kanalın hatası yoklamayı durdurmaz; sırası gelince yeniden denenir
        self._sonraki = time.time() + yoklama.bekleme(self._bozuk)
        self._kanal_bitti.emit(kanal_id, yeni)

    def _kanal_bitti_geldi(self, kanal_id, yeni):
        self._calisan -= 1
        self._bakilan += 1
        self.durumDegisti.emit()
        if yeni:
            self._yeni += yeni
            self.yeniVideolar.emit(self._yeni)
            self.kenarDegisti.emit()
