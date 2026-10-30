"""Hata bildirme ve öneri penceresinin (qml/GeriBildirimPenceresi.qml) arka yüzü.

Her bildirim önce bu bilgisayarda bir klasöre JSON olarak yazılır (kök veri klasörü/geri-bildirim/, kişiden bağımsız;
resim varsa yanında aynı adla .jpg), sonra arka planda Sentry'nin "User Feedback" bölümüne gönderilir (yer Sentry; organizasyon adeptus-vn, AB'de). Gönderilen dosyada "gonderildi": true olur; gönderilemeyen (internet yok,
Sentry cevap vermedi) false kalır ve program bir sonraki açılışta ya da bir sonraki bildirimde yeniden dener.
sentry-sdk kullanılmıyor (Python kütüphanesinde geri bildirim işlevi yok): Sentry'nin "envelope"
biçimi elle kuruluyor.
"""
import json
import platform
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import urllib3
from PySide6.QtCore import QObject, QRectF, QUrl, Signal, Slot
from PySide6.QtGui import QImage, QPainter

from . import ag, yoklama
from .youtube import PROGRAM_ADI


# Yalnız gönderme yetkisi olan anahtar (DSN); programın içinde durması ve herkesin görmesi sorun değil
# (docs.sentry.io/concepts/key-terms/dsn-explainer). LVT_SENTRY_DSN ile başka bir proje verilebilir, boş yazı
# göndermeyi kapatır (denemeler).
DSN = "https://e6e444394b1de9b274bcbb97f7aa7d58@o4512326484295680.ingest.de.sentry.io/4512326522699856"
METIN_SINIRI = 4000
IZ_SATIRI = 100   # hata bildirimine eklenen program kaydının (iz.log) son satırları
_havuz = ag.havuz(retries=False, timeout=urllib3.Timeout(connect=10, read=30))


def _dsn():
    import os
    return os.environ.get("LVT_SENTRY_DSN", DSN)


def zarf(kayit, resim_baytlari=None, dsn=None):
    """Sentry'ye gidecek paketi (envelope) kurar: başlık, "feedback" öğesi, resim varsa "attachment" öğesi.
    (adres, başlıklar, gövde) döndürür; DSN boşsa None."""
    dsn = _dsn() if dsn is None else dsn
    if not dsn:
        return None
    sema, kalan = dsn.split("//", 1)
    anahtar, kalan = kalan.split("@", 1)
    sunucu, proje = kalan.split("/", 1)
    eid = uuid.uuid4().hex
    simdi = datetime.now(timezone.utc)
    olay = {"event_id": eid, "timestamp": simdi.timestamp(), "platform": "python", "level": "info",
            "release": "litevideotube@" + PROGRAM_ADI.split("/")[-1],
            "tags": {"tur": kayit["tur"], "sistem": kayit["sistem"], "kod": kayit["kod"] or "paket"},
            "contexts": {"feedback": {"message": f"[{'Hata' if kayit['tur'] == 'hata' else 'Öneri'}] "
                                                 + kayit["metin"][:METIN_SINIRI],
                                      "source": "litevideotube"}}}
    if kayit.get("sayfa"):
        olay["contexts"]["feedback"]["url"] = kayit["sayfa"]
    parcalar = [json.dumps({"event_id": eid, "dsn": dsn, "sent_at": simdi.isoformat().replace("+00:00", "Z")}).encode(),
                json.dumps({"type": "feedback"}).encode(),
                json.dumps(olay, ensure_ascii=False).encode()]
    if kayit.get("iz"):
        # Programın kaydı (28 Ekim; sorun bildirilince ilk bakılacak yer): kişinin yazısı ve resmi
        # sebebi göstermiyor (dört Shorts açılmadı, ekranda donmuş kare vardı; sebep yalnız bu bilgisayardaki kayıtta).
        iz_baytlari = kayit["iz"].encode()
        parcalar.append(json.dumps({"type": "attachment", "length": len(iz_baytlari),
                                    "filename": "iz.log", "content_type": "text/plain"}).encode())
        parcalar.append(iz_baytlari)
    if resim_baytlari:
        parcalar.append(json.dumps({"type": "attachment", "length": len(resim_baytlari),
                                    "filename": "pencere.jpg", "content_type": "image/jpeg"}).encode())
        parcalar.append(resim_baytlari)
    adres = f"{sema}//{sunucu}/api/{proje}/envelope/"
    basliklar = {"Content-Type": "application/x-sentry-envelope", "User-Agent": PROGRAM_ADI,
                 "X-Sentry-Auth": f"Sentry sentry_version=7, sentry_key={anahtar}, sentry_client={PROGRAM_ADI}"}
    return adres, basliklar, b"\n".join(parcalar) + b"\n"


def sentrye_gonder(kayit, resim_baytlari=None):
    """True: Sentry aldı (HTTP 200). Ağ hatası ya da başka cevapta False (bildirim diskte bekler)."""
    z = zarf(kayit, resim_baytlari)
    if z is None:
        return False
    adres, basliklar, govde = z
    try:
        c = _havuz.request("POST", adres, body=govde, headers=basliklar)
    except (urllib3.exceptions.HTTPError, OSError) as e:
        print("Geri bildirim gönderilemedi:", e, file=sys.stderr, flush=True)
        return False
    if c.status != 200:
        print("Geri bildirim gönderilemedi:", c.status, c.data[:300], file=sys.stderr, flush=True)
    return c.status == 200


def _kod_surumu():
    """Geliştirme klasöründen çalışıyorsa git'teki son kaydın kısa adı (hangi kodla olduğu bilinsin); pakette boş."""
    git = Path(__file__).resolve().parent.parent / ".git"
    try:
        bas = (git / "HEAD").read_text().strip()
        if bas.startswith("ref: "):
            bas = (git / bas[5:]).read_text().strip()
        return bas[:7]
    except OSError:
        return ""


def _iz_son_satirlar():
    try:
        satirlar = (yoklama.kok_klasor() / "iz.log").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "".join(x + "\n" for x in satirlar[-IZ_SATIRI:])


def _sistem():
    if sys.platform == "win32":
        s = platform.win32_ver()
        return f"Windows {s[0]} ({s[1]})"
    return f"{platform.system()} {platform.release()}"


def _videoyu_ekle(pencere, resim):
    """Pencerenin resmi (grabWindow) videonun karesini içermiyor: mpv'nin çizdiği yüzey resme girmiyor, video alanı düz
    siyah çıkıyordu (27 Ekim, Xephyr'de oynarken de duraklatılmışken de). Görünen oynatıcının o anki karesi mpv'den
    (altyazısıyla) alınıp resimde videonun yerine, mpv'nin yaptığı gibi en-boy oranı korunarak ortalanıp çizilir.
    Kare alınamazsa resim olduğu gibi kalır."""
    from .oynatici import Oynatici
    for o in pencere.findChildren(Oynatici):
        if not o.isVisible() or o.width() < 2 or o.height() < 2 or o.bos:
            continue
        try:
            k = o.mpv.command("screenshot-raw", "subtitles")
        except Exception:
            continue
        if not k or k.get("format") != "bgr0" or not k.get("w") or not k.get("h"):
            continue
        kare = QImage(k["data"], k["w"], k["h"], k["stride"], QImage.Format_RGB32)
        alan = o.mapRectToScene(QRectF(0, 0, o.width(), o.height()))
        olcek = min(alan.width() / k["w"], alan.height() / k["h"])
        en, boy = k["w"] * olcek, k["h"] * olcek
        hedef = QRectF(alan.x() + (alan.width() - en) / 2, alan.y() + (alan.height() - boy) / 2, en, boy)
        if resim.format() != QImage.Format_RGB32:
            resim = resim.convertToFormat(QImage.Format_RGB32)
        cizer = QPainter(resim)
        cizer.setRenderHint(QPainter.SmoothPixmapTransform)
        cizer.drawImage(hedef, kare)
        cizer.end()
    return resim


class GeriBildirim(QObject):
    # Bir bildirimin gönderilme sonucu (kaydedilen dosyanın yolu, gönderildi mi); arka plandan gelir. Pencere bunu
    # beklemiyor: diske yazılan bildirim "Gönderildi." sayılır, gidemezse sonra kendiliğinden gider.
    gonderildi = Signal(str, bool)

    def __init__(self, parent=None, bekleyenleri_gonder=True):
        super().__init__(parent)
        self._taslak = None    # resimAl'ın aldığı, henüz bir bildirime eklenmemiş resim
        self._kilit = threading.Lock()   # aynı dosya iki iş parçacığından birden gönderilmesin
        if bekleyenleri_gonder:
            self._arkada_gonder(None)

    @staticmethod
    def _klasor():
        return yoklama.kok_klasor() / "geri-bildirim"

    @Slot(result=str)
    def klasor(self):
        return str(self._klasor())

    @Slot(str, str, str, bool, bool, result=str)
    def gonder(self, tur, metin, sayfa, resimli, kayitli):
        """tur: "hata" ya da "oneri"; sayfa: açık sayfanın adresi (kişi işareti kaldırdıysa boş); resimli: pencerenin
        resmi (resimAl) eklensin mi; kayitli: programın kaydının (iz.log) son satırları eklensin mi.
        Kaydedilen dosyanın yolunu, olmazsa boş yazı döndürür."""
        kayit = {"tur": tur, "metin": metin.strip(), "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "program": PROGRAM_ADI, "kod": _kod_surumu(), "sistem": _sistem(), "sayfa": sayfa,
                 "iz": _iz_son_satirlar() if kayitli else "", "resim": "", "gonderildi": False}
        resim = self._taslak if resimli else None
        try:
            yol = self._ilet(kayit, resim)
        except OSError as e:
            print("Geri bildirim kaydedilemedi:", e, file=sys.stderr, flush=True)
            return ""
        self._arkada_gonder(Path(yol))
        return yol

    def _arkada_gonder(self, yol):
        """yol'daki bildirimi ve daha önce gönderilememiş olanları arka planda Sentry'ye gönderir (pencere beklemez)."""
        threading.Thread(target=self._bekleyenleri_gonder, args=(yol,), daemon=True).start()

    def _bekleyenleri_gonder(self, once=None):
        with self._kilit:
            try:
                yollar = sorted(self._klasor().glob("*.json"))
            except OSError:
                return
            if once is not None:   # yeni bildirim önce gitsin
                yollar = [once] + [y for y in yollar if y != once]
            for y in yollar:
                try:
                    with open(y, encoding="utf-8") as f:
                        kayit = json.load(f)
                    if kayit.get("gonderildi"):
                        continue
                    resim = (y.parent / kayit["resim"]).read_bytes() if kayit.get("resim") else None
                except (OSError, ValueError, KeyError):
                    continue
                tamam = sentrye_gonder(kayit, resim)
                if tamam:
                    kayit["gonderildi"] = True
                    try:
                        with open(y, "w", encoding="utf-8") as f:
                            json.dump(kayit, f, ensure_ascii=False, indent=1)
                    except OSError:
                        pass
                if y == once:
                    self.gonderildi.emit(str(y), tamam)
                if not tamam:
                    return   # internet yoksa öbürlerini de boşuna deneme; sonraki açılışta yeniden

    def _ilet(self, kayit, resim=None):
        """Bildirim önce bu bilgisayarda bir dosyaya yazılır (resim varsa yanında aynı adla .jpg); gönderme sonra."""
        klasor = self._klasor()
        klasor.mkdir(parents=True, exist_ok=True)
        ad = time.strftime("%Y-%m-%d_%H%M%S") + "_" + kayit["tur"]
        yol = klasor / (ad + ".json")
        i = 2
        while yol.exists():
            yol = klasor / f"{ad}_{i}.json"
            i += 1
        if resim is not None and resim.exists():
            resim.replace(yol.with_suffix(".jpg"))
            kayit["resim"] = yol.with_suffix(".jpg").name
            self._taslak = None
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(kayit, f, ensure_ascii=False, indent=1)
        return str(yol)

    # Pencerenin resmi: pencere açılmadan hemen önce alınır (resimde bildirme penceresi görünmesin), JPEG
    # olarak geçici dosyaya yazılır; kişi "resmi de ekle"yi işaretlerse bildirimle aynı adla klasöre taşınır.
    # Resimde ekranda ne varsa (abonelikler, izlenenler) görünür; bu yüzden işaret kapalı başlar ve resim
    # gönderilmeden önce pencerede gösterilir. Çizim ve örtme aracı yok.
    @Slot(QObject, result=str)
    def resimAl(self, pencere):
        self.resimBirak()
        try:
            t = time.time()
            resim = _videoyu_ekle(pencere, pencere.grabWindow())
            klasor = self._klasor()
            klasor.mkdir(parents=True, exist_ok=True)
            for eski in klasor.glob("_taslak_*.jpg"):   # program kapanırken pencere açıksa kalmış olabilir
                eski.unlink(missing_ok=True)
            yol = klasor / f"_taslak_{int(t * 1000)}.jpg"
            if resim.isNull() or not resim.save(str(yol), "JPG", 85):
                return ""
            self._taslak = yol
            print(f"geri bildirim resmi {resim.width()}x{resim.height()} {yol.stat().st_size // 1024} KB "
                  f"{(time.time() - t) * 1000:.0f} ms", file=sys.stderr, flush=True)
            return QUrl.fromLocalFile(str(yol)).toString()
        except Exception as e:  # resim alınamazsa pencere yine açılır, yalnız resim seçeneği çıkmaz
            print("Pencerenin resmi alınamadı:", e, file=sys.stderr, flush=True)
            return ""

    @Slot()
    def resimBirak(self):
        """Kaydedilmeyen taslak resim silinir (pencere kapanınca ya da yeni resim alınınca)."""
        if self._taslak:
            try:
                self._taslak.unlink()
            except OSError:
                pass
            self._taslak = None
