"""İndirme: video (seçilen boyutta), yalnız ses (m4a ya da MP3) ve metin dökümü, kullanıcının
İndirilenler klasörüne. İşi bilgisayarda yt-dlp yapar, sırayla tek tek (22 Ekim düzeninden).

Neden YouTube'un video adresi verilmiyor: adres birkaç saatte bozuluyor, yavaşlatılıyor, dosya adı
yok, 360p'nin üstünde görüntü ve ses ayrı dosya (yt-dlp ffmpeg ile birleştirir).
Biçim: her boyutta önce H.264 (eski ekran kartları donanımla çözer), yoksa VP9, AV1 son çare; boyut
biçimden önce gelir ("Daso - Meine"de H.264 yalnız 480p'ye kadar var, 720p istenince 480p iniyordu).
Denemelerde LVT_INDIR ile başka klasör verilir (gerçek İndirilenler klasörü dolmasın).
"""
import html
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QStandardPaths, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from . import cozumle
from .ceviri import QT_TR_NOOP, tr
from .cozumle import ytdlp_js, ytdlp_yolu

SES = ("ses", "mp3")
SURUYOR = ("sırada", "hazırlanıyor", "indiriliyor", "tamamlanıyor")
CUMLE_BASINA = 4   # metin dökümünde dört cümlede bir boş satır
# Yayını bitip YouTube'da henüz işlenmekte olan videoda yt-dlp ara ara "The downloaded file is empty"
# ile düşüyor; nadir olduğu için yalnız bu söylenir.
SONRA_DENE = QT_TR_NOOP("Şu an indirilemiyor, daha sonra tekrar deneyin")


def klasor():
    if os.environ.get("LVT_INDIR"):
        return Path(os.environ["LVT_INDIR"])
    return Path(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or Path.home())


def guvenli_ad(baslik):
    return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|]', " ", baslik))[:120].strip()


def tur_adi(tur):
    return {"ses": tr("Ses (m4a)"), "mp3": tr("Ses (MP3)"), "dokum": tr("Metin dökümü")}.get(tur) \
        or tr("Video %1p").replace("%1", tur)


# ---- metin dökümü

def _vtt_saniye(damga):
    s = 0.0
    for p in damga.strip().replace(",", ".").split(":"):
        s = s * 60 + float(p)
    return s


def vtt_satirlari(metin):
    """(başlangıç saniyesi, yazı); otomatik altyazılar her satırı kayarken yineler, yinelenen düşer."""
    satirlar, bas = [], 0.0
    for satir in metin.splitlines():
        satir = satir.strip()
        if "-->" in satir:
            bas = _vtt_saniye(satir.split("-->")[0])
            continue
        if not satir or satir.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        satir = html.unescape(re.sub(r"<[^>]+>", "", satir)).strip()
        if satir and (not satirlar or satir != satirlar[-1][1]):
            satirlar.append((bas, satir))
    return satirlar


def dokum_metni(satirlar):
    """Her cümle ayrı satırda, dört cümlede bir boş satır. Noktalaması olmayan otomatik altyazıda
    cümle yerine altyazı satırları kullanılır."""
    kelimeler = [w for _, s in satirlar for w in s.split()]
    cumleler, simdiki = [], []
    for w in kelimeler:
        simdiki.append(w)
        if w[-1] in ".!?…":
            cumleler.append(" ".join(simdiki))
            simdiki = []
    if simdiki:
        cumleler.append(" ".join(simdiki))
    if len(cumleler) < len(kelimeler) / 40:
        cumleler = [s for _, s in satirlar]
    return "\n\n".join("\n".join(cumleler[i:i + CUMLE_BASINA]) for i in range(0, len(cumleler), CUMLE_BASINA))


class _Is:
    def __init__(self, no, vid, baslik, tur):
        self.no, self.vid, self.baslik, self.tur = no, vid, baslik, tur
        self.durum, self.yol, self.hata = "sırada", "", ""
        self.parca, self.inen, self.toplam, self.kalan = "", 0.0, 0.0, 0.0
        self.dosyalar, self.surec, self.bitis = set(), None, 0.0


class Indirici(QObject):
    degisti = Signal()
    bildirim = Signal(str)       # kısa not (ör. "İndirildi: ...")
    _haber = Signal()

    def __init__(self):
        super().__init__()
        self._isler = []
        self._kilit = threading.Lock()
        self._sira = queue.Queue()
        self._isci = None
        self._haber.connect(self.degisti)
        # İndirme sürerken yüzde saniyede iki kez yenilenir; boştayken saat durur.
        self._saat = QTimer(self)
        self._saat.timeout.connect(self._yokla)
        self._son = None

    def _yokla(self):
        durum = [(i.no, i.durum, round(i.inen)) for i in self._isler]
        if durum != self._son:
            self._son = durum
            self.degisti.emit()
        if not any(i.durum in SURUYOR for i in self._isler):
            self._saat.stop()

    # ---- QML'e açılanlar
    def _liste(self):
        sonuc = []
        for i in reversed(self._isler):
            sonuc.append({"no": i.no, "vid": i.vid, "baslik": i.baslik, "tur": i.tur, "turAdi": tur_adi(i.tur),
                          "durum": i.durum, "suruyor": i.durum in SURUYOR, "yazi": self._yazi(i),
                          "oran": (i.inen / i.toplam) if i.toplam else 0.0, "yol": i.yol,
                          "var": bool(i.yol) and os.path.isfile(i.yol)})
        return sonuc
    isler = Property(list, _liste, notify=degisti)
    suruyor = Property(int, lambda s: sum(1 for i in s._isler if i.durum in SURUYOR), notify=degisti)

    def _yazi(self, i):
        def mb(n):
            return tr("%1 MB").replace("%1", f"{n / 1e6:.0f}") if n >= 1e6 else tr("%1 KB").replace("%1", f"{n / 1e3:.0f}")
        if i.durum == "sırada":
            return tr("Sırada: önceki indirme bitince başlar")
        if i.durum == "hazırlanıyor":
            return tr("Hazırlanıyor…")
        if i.durum == "indiriliyor":
            parca = {"ses": tr("ses"), "görüntü": tr("görüntü")}.get(i.parca, i.parca)
            basi = (tr("İndiriliyor (%1):").replace("%1", parca) if i.tur not in SES and i.parca
                    else tr("İndiriliyor:"))
            yuzde = " " + tr("%%1").replace("%1", f"{i.inen * 100 / i.toplam:.0f}") if i.toplam else ""
            boyut = f" · {mb(i.inen)} / {mb(i.toplam)}" if i.toplam else ""
            kalan = (" · " + tr("kalan %1").replace("%1", f"{int(i.kalan // 60)}:{int(i.kalan % 60):02d}")
                     if i.kalan else "")
            return f"{basi}{yuzde}{boyut}{kalan}"
        if i.durum == "tamamlanıyor":
            return tr("Birleştiriliyor…") if i.tur not in SES else tr("Dönüştürülüyor…")
        if i.durum == "bitti":
            return (tr("İndirildi: %1").replace("%1", os.path.basename(i.yol)) if os.path.isfile(i.yol)
                    else tr("Dosya silinmiş ya da taşınmış"))
        if i.durum == "iptal":
            return tr("İptal edildi")
        if i.hata == SONRA_DENE:
            return tr(SONRA_DENE)
        return tr("İndirilemedi: %1").replace("%1", i.hata) if i.hata else tr("İndirilemedi")

    @Slot(str, str, str)
    def indir(self, vid, baslik, tur):
        """tur: "1080", "720"... ya da "ses", "mp3". Aynı video ve tür zaten sürüyorsa ya da dosyası
        duruyorsa ikinci kez inmez; dosya silinmişse yeniden iner (22 Ekim dersi)."""
        with self._kilit:
            for i in self._isler:
                if i.vid == vid and i.tur == tur and (i.durum in SURUYOR or (i.durum == "bitti" and os.path.isfile(i.yol))):
                    return
            is_ = _Is((self._isler[-1].no + 1) if self._isler else 1, vid, baslik, tur)
            self._isler.append(is_)
            del self._isler[:-30]
            if self._isci is None:
                self._isci = threading.Thread(target=self._calis, daemon=True)
                self._isci.start()
        self._sira.put(is_)
        self.degisti.emit()
        self._saat.start(500)

    @Slot(int)
    def iptal(self, no):
        for i in self._isler:
            if i.no == no and i.durum in SURUYOR:
                i.durum, i.bitis = "iptal", time.time()
                if i.surec and i.surec.poll() is None:
                    i.surec.terminate()
        self.degisti.emit()

    @Slot(int)
    def yeniden(self, no):
        i = next((x for x in self._isler if x.no == no), None)
        if i:
            self.indir(i.vid, i.baslik, i.tur)

    @Slot(int)
    def dosyayiAc(self, no):
        i = next((x for x in self._isler if x.no == no), None)
        if i and os.path.isfile(i.yol):
            QDesktopServices.openUrl(QUrl.fromLocalFile(i.yol))

    @Slot()
    def klasoruAc(self):
        klasor().mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(klasor())))

    @Slot()
    def bitenleriTemizle(self):
        with self._kilit:
            self._isler = [i for i in self._isler if i.durum in SURUYOR]
        self.degisti.emit()

    def dokum_kaydet(self, vid, baslik, dil, vtt):
        """Metin dökümü .txt (Oynatici seçilen altyazının metnini verir). Dönen: dosya yolu."""
        metin = dokum_metni(vtt_satirlari(vtt))
        k = klasor()
        k.mkdir(parents=True, exist_ok=True)
        yol = k / f"{guvenli_ad(baslik) or vid} ({dil}).txt"
        yol.write_text(f"{baslik}\nhttps://www.youtube.com/watch?v={vid}\n\n{metin}\n", encoding="utf-8")
        is_ = _Is((self._isler[-1].no + 1) if self._isler else 1, vid, baslik, "dokum")
        is_.durum, is_.yol, is_.bitis = "bitti", str(yol), time.time()
        self._isler.append(is_)
        self.degisti.emit()
        return str(yol)

    # ---- iş parçacığı
    def _calis(self):
        while True:
            i = self._sira.get()
            if i.durum != "sırada":
                continue
            try:
                self._indir(i)
            except Exception as e:   # işçi ne olursa olsun yaşasın
                i.durum, i.hata = "hata", str(e) or e.__class__.__name__
            i.bitis = time.time()
            self._haber.emit()

    def _indir(self, i):
        i.durum = "hazırlanıyor"
        k = klasor()
        k.mkdir(parents=True, exist_ok=True)
        if i.tur in SES:
            bicim, ad, ek = "ba[ext=m4a]/ba", "%(title).150B.%(ext)s", []
            if i.tur == "mp3":   # YouTube MP3 vermiyor; kalite 2 ≈ 190 kbit/s (m4a 129 kbit/s)
                # Ayrı ad: yt-dlp önce m4a indirip dönüştürünce siliyor; aynı ad olsa kullanıcının
                # daha önce indirdiği "Ses (m4a)" dosyası silinirdi.
                ad = "%(title).150B (MP3).%(ext)s"
                ek = ["-x", "--audio-format", "mp3", "--audio-quality", "2"]
        else:
            # Boyut adı YouTube'unki gibi kısa kenar (yt-dlp'nin "res"i de kısa kenar; dikeyde de doğru).
            bicim = "bv*+ba[ext=m4a]/bv*+ba/b"
            ad = f"%(title).150B ({i.tur}p).%(ext)s"
            ek = ["-S", f"res:{i.tur},vcodec:h264", "--merge-output-format", "mp4"]
        # Önce visionos kimliğiyle (cozumle.HIZLI: YouTube'un TV kimliğindeki ~5 sn'lik reklam beklemesi ve Node yok);
        # olmazsa yt-dlp'nin varsayılanıyla bir kez daha (yarım inen dosyadan sürer).
        for kimlik in ([cozumle.HIZLI, []] if cozumle.HIZLI else [[]]):
            kod = self._calistir(i, bicim, ek, ad, k, kimlik)
            if kod == 0 or i.durum == "iptal":
                break
            if kimlik:
                i.hata, i.durum = "", "hazırlanıyor"
        if i.durum == "iptal":
            for f in i.dosyalar:    # yarım kalan parçalar silinir
                for artik in (f, f + ".part", f + ".ytdl"):
                    if os.path.isfile(artik) and os.path.dirname(os.path.abspath(artik)) == str(k):
                        os.remove(artik)
        elif kod == 0 and i.yol:
            i.durum = "bitti"
            self.bildirim.emit(tr("İndirildi: %1").replace("%1", os.path.basename(i.yol)))
        else:
            i.durum = "hata"

    def _calistir(self, i, bicim, ek, ad, k, kimlik):
        komut = [ytdlp_yolu(), *ytdlp_js(), *kimlik, "--no-playlist", "--no-mtime", "--newline", "--progress",
                 "--progress-delta", "1", "-f", bicim, *ek, "-P", str(k), "-o", ad,
                 "--print", "after_move:LVT-DOSYA|%(filepath)s",
                 "--progress-template", "download:LVT|%(progress.status)s|%(progress.downloaded_bytes)s|"
                 "%(progress.total_bytes)s|%(progress.total_bytes_estimate)s|%(progress.eta)s|"
                 "%(info.vcodec)s|%(progress.filename)s",
                 "https://www.youtube.com/watch?v=" + i.vid]
        bayrak = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        i.surec = subprocess.Popen(komut, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   stdin=subprocess.DEVNULL, creationflags=bayrak, encoding="utf-8", errors="replace")
        for satir in i.surec.stdout:
            satir = satir.rstrip("\n")
            if satir.startswith("LVT|"):
                durum, inen, toplam, tahmin, kalan, vcodec, dosya = (satir.split("|", 7) + [""] * 7)[1:8]
                i.dosyalar.add(dosya)
                i.parca = "ses" if vcodec == "none" else "görüntü"
                i.inen, i.toplam, i.kalan = _sayi(inen), _sayi(toplam) or _sayi(tahmin), _sayi(kalan)
                if i.durum != "iptal":
                    i.durum = "tamamlanıyor" if durum == "finished" else "indiriliyor"
            elif satir.startswith("LVT-DOSYA|"):
                i.yol = satir.split("|", 1)[1]
            elif satir.startswith("ERROR:") and i.hata != SONRA_DENE:   # sonraki hata bunu ezmesin
                i.hata = SONRA_DENE if "downloaded file is empty" in satir else satir[6:].strip()[:200]
        return i.surec.wait()


def _sayi(yazi):
    try:
        return float(yazi)
    except ValueError:
        return 0.0
