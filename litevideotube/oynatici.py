"""Videoyu programın kendi penceresine (OpenGL dokusu) çizen QML öğesi: libmpv'nin çizim arayüzü.

Tuzaklar: Qt'nin çizimi tek iş parçacığında (uygulama.py),
çizim yüzeyine ve mpv'ye verilen işleve referans tutulur, kapanırken önce çizim bağlamı kapanır.
"""
import locale
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication, QNativeInterface, QOpenGLContext
from PySide6.QtOpenGL import QOpenGLFramebufferObject
from PySide6.QtQuick import QQuickFramebufferObject, QQuickOpenGLUtils
import mpv

from . import ag, cozumle, diller, donanim, iz, parca_araci, youtube
from .ceviri import kurulan_dil, tr

KADEMELER = [144, 240, 360, 480, 720, 1080, 1440, 2160]

ALTYAZI_TURLERI = ("elle", "otomatik", "ceviri")
# Makine çevirisi için tarayıcı oturumu sırayla bu tarayıcılardan aranır (abonelik.py ile aynı sıra).
TARAYICILAR = ["firefox", "chrome", "chromium", "brave", "edge", "opera", "vivaldi"]

# Önce H.264, yoksa VP9; AV1 son çare (eski ekran kartları AV1 çözemiyor).
BICIM = ("bv*[height<={h}][vcodec^=avc1]+ba/bv*[height<={h}][vcodec^=vp09]+ba/"
         "bv*[height<={h}]+ba/b[height<={h}]/b")


def _toplam_bellek_mb():
    """Bilgisayarın toplam belleği (MB); okunamazsa 4096."""
    try:
        if sys.platform.startswith("linux"):
            for satir in open("/proc/meminfo"):
                if satir.startswith("MemTotal:"):
                    return int(satir.split()[1]) // 1024
        elif sys.platform == "win32":
            import ctypes

            class _Durum(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + \
                           [(ad, ctypes.c_ulonglong) for ad in ("toplam", "bos", "sayfa", "bos_sayfa", "sanal",
                                                                 "bos_sanal", "bos_genis")]
            d = _Durum()
            d.dwLength = ctypes.sizeof(_Durum)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(d)):
                return d.toplam // 2**20
    except Exception:
        pass
    return 4096


# Önden indirme payı (23 Ekim, tur 3). mpv'nin öntanımlısı 150 MiB ileri + 50 MiB geri ve duraklatılmışken de
# doluyor: 1080p'de program 3 dk'da 268'den 370 MB'a çıktı, video sürdükçe ~470 MB'a gidecekti. Normalde 2 dk
# önden inilir (hızlı internette bol, bellekte ~30 MB); bu oturumda takılma görüldüyse (zayıf internet) bellek
# payının sonuna kadar: duraklatıp videonun yüklenmesini beklemek alışkanlığı işe yarasın (2. ilke). Pay
# bilgisayarın belleğine göre: 2 GB'lık makinede yarısı.
_BELLEK_MB = _toplam_bellek_mb()
ONDEN_MIB = 48 if _BELLEK_MB <= 2560 else 96 if _BELLEK_MB <= 6144 else 150
GERI_MIB = 8 if _BELLEK_MB <= 2560 else 16
ONDEN_SN, ONDEN_SN_ZAYIF = 120, 3600
# Açılamayan video: hemen bir kez sessizce, sonra bu aralıklarla (sn) yeniden denenir, kişi o videonun başında durdukça;
# sonuncusu tekrarlanır (28 Ekim: dört Shorts beş dakika açılmadı, sonra açıldı; program pes etmesin).
YENIDEN_DENEME_SN = [5, 15, 30, 60]
# Video bu kadar saniye oynayınca geçmişe girer (açılıp hemen geçilen sayılmaz).
IZLEME_SN = 3
ZAYIF_SURESI = 1800   # son takılmadan bu kadar sonra internet yeniden iyi sayılır


def _bellegi_geri_ver():
    """Video kapanınca boşalan belleği (önden inen pay, çözücünün tamponları) işletim sistemine geri verir.
    Linux'ta glibc boşalan belleği kendinde tutuyor: videodan abonelik sayfasına dönünce program 333 MB'ta
    kalıyordu, malloc_trim'den sonra 310 MB (28 Ekim ölçümü). Oynarken denendi, kazanç ~1 MB; yalnız
    video kapanınca çağrılır. Windows'un ve başka C kütüphanelerinin bunu yok."""
    try:
        import ctypes
        ctypes.CDLL(None).malloc_trim(0)
    except (OSError, AttributeError):
        pass


def _get_proc_address(_ctx, name):
    ctx = QOpenGLContext.currentContext()
    return ctx.getProcAddress(name) if ctx else 0


class _Cizici(QQuickFramebufferObject.Renderer):
    def __init__(self, oge):
        super().__init__()
        self.oge = oge
        self.ctx = None
        self._gpa = None
        self._fbo = None
        self.gl = None     # kapanışta mpv'nin çizim bağlamı bu OpenGL bağlamı etkinken kapatılır

    def createFramebufferObject(self, size):
        # Çizim yüzeyi her durumda verilir: burada bir hata çıkıp yüzey verilmezse Qt boş yüzeye dokunup programı
        # çökertiyor (28 Ekim 07:22'deki çökme, QQuickFramebufferObject::updatePaintNode; elle hata atılarak denendi).
        # mpv'nin çizim bağlamı kurulamazsa (mpv kapanmışken ya da bağlam zaten varken) video çizilmez, program açık kalır.
        self._fbo = QOpenGLFramebufferObject(size, QOpenGLFramebufferObject.CombinedDepthStencil)
        if self.ctx is None and not self.oge._kapandi:
            try:
                self._baglam_kur()
            except Exception as e:
                iz.yaz(f"çizim bağlamı kurulamadı: {e!r}")
        return self._fbo

    def _baglam_kur(self):
        self._gpa = mpv.MpvGlGetProcAddressFn(_get_proc_address)
        kw = {"opengl_init_params": {"get_proc_address": self._gpa}}
        ni = QGuiApplication.instance().nativeInterface()
        x11 = getattr(QNativeInterface, "QX11Application", None)
        wl = getattr(QNativeInterface, "QWaylandApplication", None)
        if x11 and isinstance(ni, x11):
            kw["x11_display"] = ni.display()
        elif wl and isinstance(ni, wl):
            kw["wl_display"] = ni.display()
        self.ctx = mpv.MpvRenderContext(self.oge.mpv, "opengl", **kw)
        self.gl = QOpenGLContext.currentContext()
        self.ctx.update_cb = self.oge._yeniKare.emit

    def render(self):
        if self.ctx is None:
            return
        fbo = self.framebufferObject()
        self.ctx.render(flip_y=False, opengl_fbo={"w": fbo.width(), "h": fbo.height(), "fbo": fbo.handle()})
        QQuickOpenGLUtils.resetOpenGLState()


class Oynatici(QQuickFramebufferObject):
    """QML'de `Oynatici { }`. Durum özellikleri mpv'den izlenir; komutlar yuva (slot) olarak."""
    _yeniKare = Signal()
    _ozellik = Signal(str, object)
    bitti = Signal()
    konumBildirimi = Signal(str, float, float)   # video id, konum, süre
    kaliteDusuruldu = Signal(str)                # zayıf internet yüzünden inilen kalite (ör. "720p")
    kaliteSecildi = Signal(int)                  # kişinin elle seçtiği boy (kalıcı; uygulama.py kayda yazar)
    _cozuldu = Signal(str, object, float)
    _cozulemedi = Signal(str, str)
    bildirim = Signal(str)                       # oynatıcının üstünde kısa not (ör. "Altyazı: Türkçe")
    _altyaziGeldi = Signal(str, str, str)        # video id, anahtar ("tur:i"), metin
    _altyaziGelmedi = Signal(str, str, str)      # video id, anahtar, sebep ("giris" ya da hata metni)
    _dosyaYuklendi = Signal()
    _oynamaBasladi = Signal()
    izlemeBasladi = Signal(str)                  # video gerçekten oynadı (IZLEME_SN): geçmişe girer (Ana.qml)
    _hataylaBitti = Signal()

    # Sık değişen iki özellik (zaman ve önden inen pay) izlenmez, yalnız gerektiğinde sorulur
    # (zamanAraligi); her video karesinde Python'dan geçmesinler.
    IZLENEN = {"duration": "sure", "pause": "durakli", "hwdec-current": "cozucu",
               "volume": "ses", "mute": "sessiz", "speed": "hiz", "paused-for-cache": "bekliyor",
               "eof-reached": "sonda", "video-params/h": "yukseklik", "video-params/aspect": "oran",
               "idle-active": "bos", "loop-file": "dongu"}

    def __init__(self, parent=None):
        super().__init__(parent)
        locale.setlocale(locale.LC_NUMERIC, "C")
        self._d = {"konum": 0.0, "sure": 0.0, "durakli": False, "cozucu": "", "ses": 100.0,
                   "sessiz": False, "hiz": 1.0, "bekliyor": False, "inmis": 0.0, "sonda": False,
                   "yukseklik": 0, "oran": 0.0, "bos": True, "dongu": "no"}
        self._cizici = None
        self._kapandi = False   # kapat()'tan sonra mpv'ye yeni çizim bağlamı kurulmaz
        secenek = dict(vo="libmpv", hwdec="auto-safe", config=False, input_default_bindings=False, osc=False,
                       # Adresleri program kendisi çözer (cozumle.py); mpv'nin ytdl eklentisi kapalı.
                       ytdl=False,
                       # Kaldığı yer kaydını program kendisi tutar; mpv'ninki kapalı (22 Ekim kazası).
                       save_position_on_quit=False, resume_playback=False,
                       keep_open="yes", volume_max=100, cache="yes",
                       cache_secs=ONDEN_SN, demuxer_max_bytes=f"{ONDEN_MIB}MiB",
                       # Önden payın boş kalanı geriye verilmesin (öntanımlı öyle; geri pay 16 yerine ~90 MiB oluyordu).
                       demuxer_max_back_bytes=f"{GERI_MIB}MiB", demuxer_donate_buffer=False,
                       # Adres yine de erken istenirse (ör. süresi dolup yeniden açılınca) 403'te bekleyip dener.
                       stream_lavf_o="reconnect=1,reconnect_on_http_error=403,reconnect_delay_max=8",
                       # Küçültme ve büyütme basit yoldan (bilinear): ekran kartının çizim yükü %27'den %12'ye,
                       # toplam güç 2,4'ten 1,3 W'a indi; görüntü farkı ancak 3 kat büyütmede seçiliyor (28 Ekim).
                       profile="fast",
                       # Kaydedilen karede renk etiketi (gAMA, cICP) olmasın: resim görüntüleyiciler etiketi görünce
                       # koyu tonları açıyor, kare ekranda görünenden parlak açılıyordu; pikseller aynıydı (29 Ekim).
                       screenshot_tag_colorspace=False)
        if ag.PROXY:
            secenek["http_proxy"] = ag.PROXY   # sistemin proxy'si (ag.py); yerel sunucu no_proxy'de
        if os.environ.get("LVT_LOG"):
            secenek["log_file"] = os.environ["LVT_LOG"]
        for kv in filter(None, os.environ.get("LVT_MPV", "").split(",")):
            k, v = kv.split("=", 1)
            k = k.replace("-", "_")
            if k.endswith("_append"):  # açılıştan önce "-append" kabul edilmiyor; elle eklenir
                k = k[:-len("_append")]
                v = (secenek[k] + "," + v) if secenek.get(k) else v
            secenek[k] = v
        # mpv'nin kendi hata satırları da iz.log'a (açılamayan dosyanın asıl sebebi, ör. HTTP 403); yalnız "error" düzeyi.
        # Nvidia kartı olmayan makinede her videoda gelen CUDA arama satırları yazılmaz.
        def mpv_hatasi(duzey, kaynak, metin):
            if "cuda" not in metin.lower():
                iz.yaz(f"mpv {kaynak}: {metin.strip()}")
        self.mpv = mpv.MPV(log_handler=mpv_hatasi, loglevel="error", **secenek)
        donanim.sina()   # ekran kartı VP9'u çözebiliyorsa VP9 seçilir (cozumle._sira)
        self._ozellik.connect(self._ozellik_geldi, Qt.QueuedConnection)
        self._yeniKare.connect(self.update, Qt.QueuedConnection)
        for ad in self.IZLENEN:
            self.mpv.observe_property(ad, lambda n, v: self._ozellik.emit(n, v))
        self.cizim_sayisi = 0
        self._son_konum = 0.0   # son bilinen yer (5 sn'de bir); dosya hatayla kapanınca mpv yeri bilmiyor
        self._kimlik = ""
        self._cozum = None
        self._kalite = self._ses = -1
        self._kaliteler, self._kalite_secili, self._sesler, self._ses_secili = [], -1, [], -1
        self._hata, self._cozuluyor = "", False
        self._hata_baslik = ""
        # Başlamamış canlı yayın ya da prömiyer: başlayınca video kendiliğinden yeniden açılır.
        self._baslayinca = QTimer(self)
        self._baslayinca.setSingleShot(True)
        self._baslayinca.timeout.connect(lambda: self._kimlik and self.ac(self._kimlik, 0.0))
        # Zayıf internet (eski mpv düzenindeki zayif-internet.lua kuralı):
        # ilk takılmada biriktirme payı 1 sn'den 4 sn'ye; 45 sn içinde ikinci takılmada bir kademe
        # düşük kalite; düşük kalite sonraki videolara taşınır; 10 dk takılmasız geçerse yeni videoda
        # bir kademe yukarı; video ortasında yükseltme yok; elle seçilen kalite ezilmez; canlıda kapalı.
        self._takilmalar = []
        self._son_takilma = 0.0
        self._ust_sinir = None          # oturum boyunca düşürülmüş üst boyut (ör. 720)
        self._elle_secildi = False
        # Kişinin elle seçtiği kalitenin boyu (ör. 480): sonraki videolar da en çok bu boyda açılır (28 Ekim: interneti
        # düşük olan kotasını yettirmeye çalışır). 0: seçilmemiş, varsayılan sınır. uygulama.py kayıttan verir ve saklar.
        self.kaliciSinir = 0
        self._atlama_hedef = 0.0        # son açılışın ya da atlamanın videodaki yeri (sn)
        self._cozuldu.connect(self._cozuldu_geldi, Qt.QueuedConnection)
        self._cozulemedi.connect(self._cozulemedi_geldi, Qt.QueuedConnection)
        # Altyazı: YouTube'daki gibi kapalı başlar. İnen metin bellekte tutulur; kalite ya da ses
        # değişince dosya yeniden açılır ve dış altyazılar gider, seçili olan yeniden eklenir.
        self._altyazilar = {t: [] for t in ALTYAZI_TURLERI}
        self._altyazi_secili = ""       # "elle:0" gibi; "" kapalı
        self._altyazi_bekleyen = ""     # iniyor
        self._altyazi_durum = ""        # "", "iniyor", "giris" (makine çevirisi giriş istiyor), "oturum" (tarayıcıda oturum yok) ya da hata
        self._altyazi_metin = {}
        self._altyazi_sid = {}
        self._altyaziGeldi.connect(self._altyazi_geldi, Qt.QueuedConnection)
        self._altyaziGelmedi.connect(self._altyazi_gelmedi, Qt.QueuedConnection)
        self._dosyaYuklendi.connect(self._dosya_yuklendi, Qt.QueuedConnection)

        @self.mpv.event_callback("file-loaded")
        def _yuklendi(_olay):
            self._dosyaYuklendi.emit()

        # Geçmiş (28 Ekim): video açılınca değil, IZLEME_SN oynayınca geçmişe girer. Önceden açılmayan
        # videolar, Shorts'ta üstünden geçilenler ve geri gelen sekmeler de "izlendi" sayılıyordu.
        self._izlenen = ""        # bu açılışta geçmişe yazılan video
        self._oynayan = ""        # görüntüsü gelip oynamaya başlayan video
        self._ayni_izleme = False # ac() iç sebeple (adres yenileme) çağrıldı: yeni izleme sayılmaz
        # Açılamayan ya da oynarken kopan video bir kez kendiliğinden yeniden açılır (28 Ekim); yine
        # olmazsa "Yeniden dene" kutusu çıkar. Önceden hiçbir şey olmuyordu, ekranda donmuş kare kalıyordu.
        self._yeniden_denenen = ""
        self._son_hata = ""
        self._deneme_sayisi = 0
        self._deneme_zamani = 0.0
        self._deneme_saati = QTimer(self)
        self._deneme_saati.setSingleShot(True)
        self._deneme_saati.timeout.connect(self._otomatik_dene)
        self._geri_sayim = QTimer(self)
        self._geri_sayim.setInterval(1000)
        self._geri_sayim.timeout.connect(self._geri_sayim_yaz)
        self._izleme_saati = QTimer(self)
        self._izleme_saati.setSingleShot(True)
        self._izleme_saati.setInterval(IZLEME_SN * 1000)
        self._izleme_saati.timeout.connect(self._izleme_doldu)
        self._oynamaBasladi.connect(self._oynama_basladi, Qt.QueuedConnection)

        @self.mpv.event_callback("playback-restart")
        def _basladi(_olay):
            self._oynamaBasladi.emit()

        # Oynarken açılamayan dosya: adresin süresi dolmuşsa (~6 saat) yeniden çözülür.
        self._hataylaBitti.connect(self._hatayla_bitti, Qt.QueuedConnection)

        @self.mpv.event_callback("end-file")
        def _bitti(olay):
            if getattr(getattr(olay, "data", None), "reason", None) == mpv.MpvEventEndFile.ERROR:
                # Sebep iz.log'a (28 Ekim: dört Shorts arka arkaya hiç oynamadı, ekranda donmuş kare kaldı, kayıtta iz yoktu).
                kod = getattr(olay.data, "error", 0)
                try:
                    sebep = mpv.ErrorCode.human_readable(kod)
                except Exception:
                    sebep = str(kod)
                iz.yaz(f"dosya hatayla kapandı: {sebep} ({self._kimlik})")
                self._son_hata = sebep
                self._hataylaBitti.emit()
        self._tazele_kalite = None    # yeniden çözülünce aynı boyut ve altyazı korunur
        self._tazele_altyazi = ""
        self._durakli_ac = False   # acDurakli: çözülünce duraklatılmış açılır
        self._canli_ipucu = False  # canliIpucu: sıradaki video listede canlı görünüyordu
        # Oynarken 5 sn'de bir kaldığı yer bildirilir; çökme ya da elektrik kesilmesinde de kayıp az olsun.
        self._kayit_saati = QTimer(self)
        self._kayit_saati.timeout.connect(lambda: None if self._d["durakli"] else self.konumuBildir())
        self._kayit_saati.start(5000)
        self._saat = QTimer(self)
        self._saat.timeout.connect(self._zamani_sor)
        self._aralik = 0

    def _zamani_sor(self):
        for ad, anahtar in (("time-pos", "konum"), ("demuxer-cache-time", "inmis")):
            try:
                deger = self.mpv._get_property(ad)
            except Exception:  # dosya yokken mpv hata verir
                deger = None
            self._ozellik_geldi_ad(anahtar, deger)

    def _aralik_al(self):
        return self._aralik

    def _aralik_ver(self, ms):
        """0: zaman sorulmaz (çubuk gizli); örneğin 250: saniyede 4 kez."""
        if ms == self._aralik:
            return
        self._aralik = ms
        if ms > 0:
            self._zamani_sor()
            self._saat.start(ms)
        else:
            self._saat.stop()
        self.zamanAraligiDegisti.emit()

    zamanAraligiDegisti = Signal()
    zamanAraligi = Property(int, _aralik_al, _aralik_ver, notify=zamanAraligiDegisti)

    def _pay_al(self):
        return self.__dict__.get("_pay", 22)

    def _pay_ver(self, deger):
        deger = max(0, min(600, int(deger)))
        if deger == self._pay_al():
            return
        self._pay = deger
        self.mpv["sub-margin-y"] = deger
        self.altyaziPayiDegisti.emit()

    altyaziPayiDegisti = Signal()
    # Altyazının alt kenardan uzaklığı (mpv sub-margin-y); çubuk görünürken çubuğun üstüne çıkar.
    altyaziPayi = Property(int, _pay_al, _pay_ver, notify=altyaziPayiDegisti)

    def _takildi(self):
        """Oynarken önden inen pay bitti (paused-for-cache). Video açılınca ya da atlanınca ilk dolum
        sayılmaz: yalnız atlanan yerden en az 3 sn oynadıktan sonraki bekleme zayıf internettir.
        Önceden açılışın ve atlamanın ilk 3 sn'si saatle atlanıyordu; açılış 5 sn, inmemiş yere atlama
        8 sn sürebildiği için ilk dolum yine sayılıyor, bir video (açılış ve bir
        atlama) bir kademe düşük kalitede yeniden açılıyordu. Atlarken mpv'nin konumu hedefi gösterir."""
        c = self._cozum
        konum = self.mpv.time_pos
        if c is None or c["canli"] or c["tek_adres"] or konum is None or konum - self._atlama_hedef < 3:
            return
        iz.yaz("takıldı")
        simdi = time.time()
        if simdi - self._son_takilma > ZAYIF_SURESI:
            self.mpv["cache-secs"] = ONDEN_SN_ZAYIF   # zayıf internet: bellek payının sonuna kadar önden
        self._son_takilma = simdi
        self._takilmalar = [t for t in self._takilmalar if simdi - t < 45] + [simdi]
        if len(self._takilmalar) == 1:
            self.mpv["cache-pause-wait"] = 4
            return
        if self._elle_secildi:
            return
        # 45 sn içinde ikinci takılma: bir kademe düşük kalite (büyütülmüş kopyalar atlanır).
        simdiki = c["kaliteler"][self._kalite]["yukseklik"]
        for i in range(self._kalite + 1, len(c["kaliteler"])):
            k = c["kaliteler"][i]
            if k["yukseklik"] < simdiki and not k["buyutulmus"]:
                self._kalite = i
                self._ust_sinir = k["yukseklik"]
                self._takilmalar = []
                self._kaliteler_ver(self._kaliteler, i)
                self.kaliteDusuruldu.emit(k["ad"])
                self._yukle(self.mpv.time_pos or 0.0, bool(self._d["durakli"]))
                return

    def _ozellik_geldi(self, ad, deger):
        self._ozellik_geldi_ad(self.IZLENEN[ad], deger)

    def _ozellik_geldi_ad(self, anahtar, deger):
        if deger is None:
            deger = {"konum": 0.0, "sure": 0.0, "inmis": 0.0, "yukseklik": 0, "oran": 0.0, "cozucu": ""}.get(anahtar, self._d[anahtar])
        if deger == self._d[anahtar]:
            return
        ilk_bitis = anahtar == "sonda" and deger and not self._d["sonda"]
        if anahtar == "cozucu":
            iz.yaz(f"çözücü {deger or 'yok'}")
        self._d[anahtar] = deger
        getattr(self, anahtar + "Degisti").emit()
        if anahtar == "durakli" and deger:
            self.konumuBildir()
        if anahtar == "durakli":
            self._izleme_bak()
        if anahtar == "bekliyor" and deger:
            self._takildi()
        if ilk_bitis:
            self.bitti.emit()

    def createRenderer(self):
        self.window().setPersistentGraphics(True)
        self.window().setPersistentSceneGraph(True)
        self._cizici = _Cizici(self)
        return self._cizici

    # Her özelliğin kendi haber sinyali var: zaman her karede değişiyor, öbür bağlar boşuna yeniden
    # hesaplanmasın.
    konumDegisti = Signal(); sureDegisti = Signal(); durakliDegisti = Signal(); cozucuDegisti = Signal()
    sesDegisti = Signal(); sessizDegisti = Signal(); hizDegisti = Signal(); bekliyorDegisti = Signal()
    inmisDegisti = Signal(); sondaDegisti = Signal(); yukseklikDegisti = Signal(); bosDegisti = Signal()
    oranDegisti = Signal()
    donguDegisti = Signal()

    konum = Property(float, lambda s: float(s._d["konum"]), notify=konumDegisti)
    sure = Property(float, lambda s: float(s._d["sure"]), notify=sureDegisti)
    durakli = Property(bool, lambda s: bool(s._d["durakli"]), notify=durakliDegisti)
    cozucu = Property(str, lambda s: str(s._d["cozucu"] or ""), notify=cozucuDegisti)
    ses = Property(float, lambda s: float(s._d["ses"]), notify=sesDegisti)
    sessiz = Property(bool, lambda s: bool(s._d["sessiz"]), notify=sessizDegisti)
    hiz = Property(float, lambda s: float(s._d["hiz"]), notify=hizDegisti)
    bekliyor = Property(bool, lambda s: bool(s._d["bekliyor"]), notify=bekliyorDegisti)
    inmis = Property(float, lambda s: float(s._d["inmis"] or 0.0), notify=inmisDegisti)
    sonda = Property(bool, lambda s: bool(s._d["sonda"]), notify=sondaDegisti)
    yukseklik = Property(int, lambda s: int(s._d["yukseklik"] or 0), notify=yukseklikDegisti)
    oran = Property(float, lambda s: float(s._d["oran"] or 0.0), notify=oranDegisti)   # en / boy (video yokken 0)
    bos = Property(bool, lambda s: bool(s._d["bos"]), notify=bosDegisti)
    dongu = Property(bool, lambda s: s._d["dongu"] not in (False, "no"), notify=donguDegisti)

    @Slot(bool)
    def goruntu(self, acik):
        """Pencere uzun süre küçültülmüşken görüntü çözülmez, yalnız ses sürer (Ana.qml). Küçültülmüş pencerede oynarken
        işlemci %9'dan %2,7'ye iniyor; geri açınca ses 1-2 sn duruyor, görüntü 0,2-2 sn sonra geliyor (28 Ekim, tur 2;
        5 dakikadan sonra olsun, liste dinleyen için). vid seçeneği sonraki videolarda da geçerli kalır."""
        try:
            self.mpv["vid"] = "auto" if acik else "no"
            iz.yaz("görüntü " + ("açık" if acik else "kapalı (pencere küçültülmüş)"))
        except Exception as e:   # mpv kapanırken
            iz.yaz(f"görüntü değiştirilemedi: {e}")

    @Slot(bool)
    def canliIpucu(self, var):
        """Sıradaki ac() için: video listede canlı görünüyordu (Ana.qml videoAc); adres önce canlı yolundan sorulur."""
        self._canli_ipucu = var

    @Slot(str, float)
    def ac(self, video_id, baslangic=0.0):
        """Videoyu açar; baslangic > 0 ise oradan (kaldığı yer). Önceki videonun yeri bildirilir.
        Adresler arka planda çözülür (yt-dlp, 1-5 sn); bu arada yükleniyor işareti döner."""
        self._durakli_ac = False
        self.konumuBildir()
        iz.yaz(f"aç {video_id} {baslangic:.0f} sn")
        # Listede canlı görünen ya da az önce canlı açılmış (adres yenileniyor) video: cozumle.coz canli_ipucu.
        canli_ipucu = self._canli_ipucu or (video_id == self._kimlik and bool(self._cozum and self._cozum["canli"]))
        self._canli_ipucu = False
        if video_id != self._kimlik:
            self._son_konum = 0.0
        self._deneme_saati.stop()
        self._geri_sayim.stop()
        if not self._ayni_izleme or video_id != self._kimlik:
            self._izlenen = ""
            self._yeniden_denenen = ""
            self._deneme_sayisi = 0
        self._ayni_izleme = False
        self._oynayan = ""
        self._izleme_saati.stop()
        self._kimlik = video_id
        self._cozum = None
        self.canliDegisti.emit()
        self._baslayinca.stop()
        self._hata_ver("")
        self._kaliteler_ver([], -1)
        self._sesler_ver([], -1)
        self._altyazi_sifirla({t: [] for t in ALTYAZI_TURLERI})
        self.mpv.command_async("stop")
        self._cozuluyor_ver(True)

        def is_():
            try:
                c = cozumle.coz(video_id, canli_ipucu=canli_ipucu)
                cozumle.bekle(c["acilis"])
                self._cozuldu.emit(video_id, c, float(baslangic))
            except Exception as e:
                self._cozulemedi.emit(video_id, str(e) or e.__class__.__name__)
        threading.Thread(target=is_, daemon=True).start()

    @Slot(str, float)
    def acDurakli(self, video_id, baslangic):
        """Videoyu açar ama oynatmaz (program açılınca sekmeler geri gelirken: ses birden çalmasın)."""
        self.ac(video_id, baslangic)
        self._durakli_ac = True

    def _cozuldu_geldi(self, video_id, c, baslangic):
        if video_id != self._kimlik:
            return  # kullanıcı bu arada başka videoya geçti
        if os.environ.get("LVT_GECERLILIK_SN"):   # sınama: adresin ömrünü kısaltır
            c["gecerlilik"] = time.time() + float(os.environ["LVT_GECERLILIK_SN"])
        self._cozum = c
        self.canliDegisti.emit()
        self._takilmalar = []
        self._elle_secildi = False
        # Canlı yayın takılınca 5 sn birikmeden sürmez (yayın biraz geriye çekilir, kısa
        # yavaşlamalarda tekrar tekrar durmaz). Kaldığı yer yok.
        self.mpv["cache-pause-wait"] = 5 if c["canli"] else 1
        self.mpv["cache-secs"] = ONDEN_SN_ZAYIF if time.time() - self._son_takilma < ZAYIF_SURESI else ONDEN_SN
        if c["canli"]:
            baslangic = 0.0
        en_cok = self.kaliciSinir or cozumle.VARSAYILAN_UST
        if self._ust_sinir and time.time() - self._son_takilma > 600:
            # 10 dk takılmadan geçti: bu videoda bir kademe yukarı.
            yukari = [h for h in KADEMELER if h > self._ust_sinir]
            self._ust_sinir = yukari[0] if yukari and yukari[0] < en_cok else None
        # Takılınca inilen boy kişinin seçtiğinden de aşağı inebilir, yukarı çıkmaz.
        self._kalite = cozumle.varsayilan_kalite(c["kaliteler"], min(self._ust_sinir or en_cok, en_cok))
        if self._tazele_kalite:   # süresi dolan adres yeniden çözüldü: kullanıcının boyutu kalsın
            ayni = [i for i, k in enumerate(c["kaliteler"]) if k["ad"] == self._tazele_kalite]
            if ayni:
                self._kalite, self._elle_secildi = ayni[0], True
            self._tazele_kalite = None
        self._ses = 0 if c["sesler"] else -1
        self._kaliteler_ver([{"ad": k["ad"], "bicim": k["bicim"], "buyutulmus": k["buyutulmus"]}
                             for k in c["kaliteler"]], self._kalite)
        self._sesler_ver([self._ses_adi(x) for x in c["sesler"]], self._ses)
        self._altyazi_sifirla(c.get("altyazilar") or {t: [] for t in ALTYAZI_TURLERI})
        self._yukle(baslangic, self._durakli_ac)
        self._durakli_ac = False
        if self._tazele_altyazi:
            self.altyaziSec(self._tazele_altyazi)
            self._tazele_altyazi = ""

    def _cozulemedi_geldi(self, video_id, metin):
        if video_id != self._kimlik:
            return
        self._cozuluyor_ver(False)
        self._hata_ver(metin)
        _, _, bekle = cozumle.hata_turkce(metin)
        if 0 < bekle <= 2 * 86400:
            self._baslayinca.start(bekle * 1000)

    def _oynama_basladi(self):
        self._oynayan = self._kimlik
        self._yeniden_denenen = ""   # açıldı: sonraki kopuşta yeniden baştan (önce sessiz deneme, sonra 5 sn)
        self._deneme_sayisi = 0
        self._izleme_bak()

    def _izleme_bak(self):
        if self._oynayan == self._kimlik and self._izlenen != self._kimlik and not self._d["durakli"]:
            if not self._izleme_saati.isActive():
                self._izleme_saati.start()
        else:
            self._izleme_saati.stop()

    def _izleme_doldu(self):
        if self._oynayan == self._kimlik and self._izlenen != self._kimlik and not self._d["durakli"]:
            self._izlenen = self._kimlik
            self.izlemeBasladi.emit(self._kimlik)

    def _ses_adi(self, x):
        ad = tr("Ses") if x["dil"] == "?" else diller.dil_adi(x["dil"])
        if x["ozgun"]:
            return tr("%1 (özgün)").replace("%1", ad)
        elif x["dublaj"]:
            return tr("%1 (dublaj)").replace("%1", ad)
        return ad

    def _yukle(self, baslangic, durakli):
        """Seçili kalite ve sesle dosyayı (yeniden) açar."""
        c = self._cozum
        if c is None:
            return
        if c["tek_adres"]:
            video, ses, basliklar = c["tek_adres"], None, c["basliklar"]
        else:
            k = c["kaliteler"][self._kalite]
            video, basliklar = k["url"], k["basliklar"]
            secili_ses = c["sesler"][self._ses] if self._ses >= 0 else None
            ses = secili_ses["url"] if secili_ses else None
            if k.get("parca_sn"):
                # Yayını bitmiş, YouTube'da henüz işlenen video: saniyelik parçalar, DASH listesiyle.
                parcali_ses = secili_ses if secili_ses and secili_ses.get("parca_sn") else None
                video = cozumle.dash_dosyasi(c["sure"], k, parcali_ses)
                if parcali_ses:
                    ses = None
        # YouTube tek parça isteği kısıyor: dosyalar programın aracısından 8 MB'lık parçalarla, tam hızla iner (parca_araci).
        parca_araci.tam_unut()
        video = parca_araci.tam_kayit(video, basliklar)
        ses = parca_araci.tam_kayit(ses, basliklar) if ses else ses
        self.mpv["audio-files"] = [ses] if ses else []
        iz.yaz(f"yükle {'tek adres' if c['tek_adres'] else c['kaliteler'][self._kalite]['ad']} {baslangic:.0f} sn")
        ua = basliklar.get("User-Agent")
        if ua:
            self.mpv["user-agent"] = ua
        self.mpv["http-header-fields"] = [f"{a}: {b}" for a, b in basliklar.items() if a != "User-Agent"]
        self.mpv["force-media-title"] = c["baslik"]
        self.mpv["start"] = f"{baslangic:.1f}" if baslangic > 0 else "none"
        self.mpv.pause = durakli
        self._altyazi_sid = {}   # dış altyazılar yeni dosyayla gider; seçili olan yüklenince eklenir
        self.mpv.command_async("loadfile", video)
        self._atlama_hedef = baslangic
        self._cozuluyor_ver(False)

    @Slot(int)
    def kaliteSec(self, i):
        if self._cozum is None or not (0 <= i < len(self._cozum["kaliteler"])) or i == self._kalite:
            return
        self._kalite = i
        self._elle_secildi = True
        self.kaliciSinir = self._cozum["kaliteler"][i]["yukseklik"]
        self._ust_sinir = None
        self._kaliteler_ver(self._kaliteler, i)
        self.kaliteSecildi.emit(self.kaliciSinir)
        self._yukle(self.mpv.time_pos or 0.0, bool(self._d["durakli"]))

    @Slot()
    def siniriKaldir(self):
        """Elle seçilmiş kalıcı sınır kalkar; sonraki videolar varsayılan sınırla açılır (oynayan video değişmez)."""
        self.kaliciSinir = 0
        self.kalitelerDegisti.emit()
        self.kaliteSecildi.emit(0)

    @Slot(int)
    def sesSec(self, i):
        if self._cozum is None or not (0 <= i < len(self._cozum["sesler"])) or i == self._ses:
            return
        self._ses = i
        self._sesler_ver(self._sesler, i)
        self._yukle(self.mpv.time_pos or 0.0, bool(self._d["durakli"]))

    @Slot()
    def yenidenDene(self):
        """Hata kutusundaki "Yeniden dene": YouTube kilidi hatırlanmışsa unutulur (cozumle.kilidi_unut)."""
        if self._kimlik:
            cozumle.kilidi_unut()
            self.ac(self._kimlik, self._simdiki_konum() if self._cozum and not self._cozum["canli"] else 0.0)

    # Altyazı
    def _altyazi_sifirla(self, liste):
        self._altyazilar = liste
        self._altyazi_secili = self._altyazi_bekleyen = self._altyazi_durum = ""
        self._altyazi_metin, self._altyazi_sid = {}, {}
        self.altyazilarDegisti.emit()

    def _altyazi_bul(self, anahtar):
        tur, _, i = anahtar.partition(":")
        liste = self._altyazilar.get(tur) or []
        return liste[int(i)] if i.isdigit() and int(i) < len(liste) else None

    @Slot(str)
    def altyaziSec(self, anahtar):
        """anahtar "elle:0", "otomatik:0", "ceviri:12"; "" kapatır."""
        if not anahtar:
            self._altyazi_secili = self._altyazi_bekleyen = self._altyazi_durum = ""
            self.mpv["sid"] = "no"
            self.altyazilarDegisti.emit()
            return
        a = self._altyazi_bul(anahtar)
        if a is None:
            return
        if anahtar in self._altyazi_metin:
            self._altyazi_goster(anahtar)
            return
        self._altyazi_bekleyen, self._altyazi_durum = anahtar, "iniyor"
        self.altyazilarDegisti.emit()
        kimlik = self._kimlik

        def is_():
            try:
                r = youtube._havuz.request("GET", a["url"])
                if r.status == 429 and a["tur"] == "ceviri":
                    self._altyaziGelmedi.emit(kimlik, anahtar, "giris")
                elif r.status != 200 or not r.data.startswith(b"WEBVTT"):
                    self._altyaziGelmedi.emit(kimlik, anahtar, f"YouTube {r.status} döndü")
                else:
                    self._altyaziGeldi.emit(kimlik, anahtar, r.data.decode("utf-8", "replace"))
            except Exception as e:
                self._altyaziGelmedi.emit(kimlik, anahtar, str(e) or e.__class__.__name__)
        threading.Thread(target=is_, daemon=True).start()

    @Slot(str)
    def altyaziOturumla(self, anahtar):
        """Makine çevirisi: YouTube girişsiz vermiyor (429, Temmuz 2025'ten beri). Kullanıcı isterse
        bilgisayarındaki tarayıcının YouTube oturumuyla yt-dlp indirir (~10 sn). Oturum yalnız bu
        istek için okunur, saklanmaz."""
        a = self._altyazi_bul(anahtar)
        if a is None or not self._kimlik:
            return
        self._altyazi_bekleyen, self._altyazi_durum = anahtar, "iniyor"
        self.altyazilarDegisti.emit()
        kimlik = self._kimlik

        def is_():
            klasor = Path(tempfile.mkdtemp(prefix="lvt-altyazi-"))
            bayrak = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            try:
                for t in TARAYICILAR:
                    try:
                        subprocess.run([cozumle.ytdlp_yolu(), *cozumle.ytdlp_js(), "--cookies-from-browser", t, "--skip-download",
                                        "--write-auto-subs", "--sub-langs", a["kod"], "--sub-format", "vtt",
                                        "--no-warnings", "--no-playlist", "-o", str(klasor / "a"),
                                        "https://www.youtube.com/watch?v=" + kimlik],
                                       capture_output=True, timeout=60, creationflags=bayrak)
                    except (OSError, subprocess.TimeoutExpired):
                        continue
                    dosya = next(klasor.glob("*.vtt"), None)
                    if dosya:
                        self._altyaziGeldi.emit(kimlik, anahtar, dosya.read_text("utf-8", "replace"))
                        return
                iz.yaz("altyazı oturumla da inmedi (denenen: " + ", ".join(TARAYICILAR) + ")")
                self._altyaziGelmedi.emit(kimlik, anahtar, "oturum")
            finally:
                shutil.rmtree(klasor, ignore_errors=True)
        threading.Thread(target=is_, daemon=True).start()

    def _altyazi_geldi(self, kimlik, anahtar, metin):
        if kimlik != self._kimlik:
            return
        # Satır yeri ayarları (YouTube'un otomatik altyazılarında "align:start position:0%") silinir:
        # yoksa mpv altyazının yerini sabit sayıyor, çubuk görünürken üste çıkaramıyor.
        metin = re.sub(r"(?m)^(\S+ --> \S+)[ \t].*$", r"\1", metin)
        self._altyazi_metin[anahtar] = metin
        if self._altyazi_bekleyen == anahtar:
            self._altyazi_goster(anahtar)

    def _altyazi_gelmedi(self, kimlik, anahtar, sebep):
        if kimlik != self._kimlik or self._altyazi_bekleyen != anahtar:
            return
        # Ekranda yalnız kısa cümle (AltyaziMenusu); ham hata metni iz.log'a (açıklama ayıklama).
        if sebep not in ("giris", "oturum"):
            iz.yaz("altyazı inmedi: " + sebep)
        self._altyazi_durum = sebep
        self.altyazilarDegisti.emit()

    def _altyazi_goster(self, anahtar):
        a = self._altyazi_bul(anahtar)
        sid = self._altyazi_sid.get(anahtar)
        if sid is not None:
            self.mpv["sid"] = sid
        else:
            # memory://: metin doğrudan mpv'ye verilir, diske dosya yazılmaz.
            self.mpv.command("sub-add", "memory://" + self._altyazi_metin[anahtar], "select", a["ad"], a["kod"])
            self._altyazi_sid[anahtar] = self.mpv.sid
        self._altyazi_secili, self._altyazi_bekleyen, self._altyazi_durum = anahtar, "", ""
        self.altyazilarDegisti.emit()

    def _dosya_yuklendi(self):
        if self._altyazi_secili and self._altyazi_secili in self._altyazi_metin:
            self._altyazi_goster(self._altyazi_secili)

    @Slot()
    def altyaziAcKapa(self):
        """c tuşu (YouTube gibi): açıksa kapatır; kapalıysa kullanıcının dilinde (ekran dili) elle yazılmış, yoksa
        İngilizce elle yazılmış, yoksa otomatik (konuşmanın dili), yoksa ilk elle yazılmış altyazı."""
        if self._altyazi_secili or self._altyazi_bekleyen:
            self.altyaziSec("")
            self.bildirim.emit(tr("Altyazı kapalı"))
            return
        elle, oto = self._altyazilar.get("elle") or [], self._altyazilar.get("otomatik") or []
        for kosul in (lambda: [i for i, a in enumerate(elle) if a["kod"].split("-")[0] == kurulan_dil()],
                      lambda: [i for i, a in enumerate(elle) if a["kod"].split("-")[0] == "en"]):
            bulunan = kosul()
            if bulunan:
                self.altyaziSec(f"elle:{bulunan[0]}")
                self.bildirim.emit(tr("Altyazı: %1").replace("%1", elle[bulunan[0]]["ad"]))
                return
        if oto:
            self.altyaziSec("otomatik:0")
            self.bildirim.emit(tr("Altyazı: %1 (otomatik)").replace("%1", oto[0]["ad"]))
        elif elle:
            self.altyaziSec("elle:0")
            self.bildirim.emit(tr("Altyazı: %1").replace("%1", elle[0]["ad"]))
        else:
            self.bildirim.emit(tr("Bu videoda altyazı yok"))

    dokumHazir = Signal(str, str, str, str)   # video id, başlık, dil kodu, WebVTT metni (indirme.py kaydeder)

    @Slot()
    def dokumKaydet(self):
        """Metin dökümü: açık altyazı varsa o, yoksa kullanıcının dilinde (önce elle yazılmış), yoksa konuşmanın
        dili (otomatik), yoksa ilk elle yazılmış. Metin inince dokumHazir yayılır."""
        anahtar = self._altyazi_secili
        if not anahtar:
            elle, oto = self._altyazilar.get("elle") or [], self._altyazilar.get("otomatik") or []
            kendi = [i for i, a in enumerate(elle) if a["kod"].split("-")[0] == kurulan_dil()]
            anahtar = f"elle:{kendi[0]}" if kendi else "otomatik:0" if oto else "elle:0" if elle else ""
        a = self._altyazi_bul(anahtar) if anahtar else None
        if a is None or not self._kimlik:
            self.bildirim.emit(tr("Bu videonun altyazısı yok, metin dökümü çıkarılamıyor"))
            return
        kimlik, baslik = self._kimlik, (self._cozum or {}).get("baslik") or self._kimlik
        if anahtar in self._altyazi_metin:
            self.dokumHazir.emit(kimlik, baslik, a["kod"], self._altyazi_metin[anahtar])
            return

        def is_():
            try:
                r = youtube._havuz.request("GET", a["url"])
                if r.status == 200 and r.data.startswith(b"WEBVTT"):
                    self.dokumHazir.emit(kimlik, baslik, a["kod"], r.data.decode("utf-8", "replace"))
                else:
                    iz.yaz(f"metin dökümü inmedi: YouTube {r.status} döndü")
                    self.bildirim.emit(tr("Metin dökümü inmedi"))
            except Exception as e:
                iz.yaz("metin dökümü inmedi: " + (str(e) or e.__class__.__name__))
                self.bildirim.emit(tr("Metin dökümü inmedi"))
        threading.Thread(target=is_, daemon=True).start()

    altyazilarDegisti = Signal()
    altyaziElle = Property(list, lambda s: [a["ad"] for a in s._altyazilar.get("elle") or []], notify=altyazilarDegisti)
    altyaziOtomatik = Property(list, lambda s: [a["ad"] for a in s._altyazilar.get("otomatik") or []], notify=altyazilarDegisti)
    altyaziCeviri = Property(list, lambda s: [a["ad"] for a in s._altyazilar.get("ceviri") or []], notify=altyazilarDegisti)
    seciliAltyazi = Property(str, lambda s: s._altyazi_secili, notify=altyazilarDegisti)
    bekleyenAltyazi = Property(str, lambda s: s._altyazi_bekleyen, notify=altyazilarDegisti)
    altyaziDurum = Property(str, lambda s: s._altyazi_durum, notify=altyazilarDegisti)

    # QML'e açılan liste ve durumlar

    def _kaliteler_ver(self, liste, secili):
        self._kaliteler, self._kalite_secili = liste, secili
        self.kalitelerDegisti.emit()

    def _sesler_ver(self, liste, secili):
        self._sesler, self._ses_secili = liste, secili
        self.seslerDegisti.emit()

    def _hata_ver(self, metin):
        """metin: yt-dlp'nin (çoğu zaman İngilizce) hata metni. Kullanıcıya Türkçesi gösterilir."""
        self._hata_baslik, self._hata, _ = cozumle.hata_turkce(metin) if metin else ("", "", 0)
        # Asıl (İngilizce, teknik) metin ekranda değil, günlükte (kullanıcı okumaz).
        if metin:
            print("Video açılamadı:", metin, file=sys.stderr, flush=True)
        self.hataDegisti.emit()

    def _cozuluyor_ver(self, b):
        self._cozuluyor = b
        self.cozuluyorDegisti.emit()

    kalitelerDegisti = Signal(); seslerDegisti = Signal(); hataDegisti = Signal(); cozuluyorDegisti = Signal()
    canliDegisti = Signal()
    canli = Property(bool, lambda s: bool(s._cozum and s._cozum["canli"]), notify=canliDegisti)
    kaliteler = Property(list, lambda s: s._kaliteler, notify=kalitelerDegisti)
    seciliKalite = Property(int, lambda s: s._kalite_secili, notify=kalitelerDegisti)
    # Elle seçilen kalite sonraki videolar için de sınır olur (28 Ekim). Görünmediği için 720p'de kalıp "görüntü puslu"
    # sanıldı (29 Ekim); kalite menüsünün altında yazılır. Varsayılanla aynıysa 0.
    kaliciSinirYazi = Property(int, lambda s: s.kaliciSinir if s.kaliciSinir != cozumle.VARSAYILAN_UST else 0,
                               notify=kalitelerDegisti)
    sesler = Property(list, lambda s: s._sesler, notify=seslerDegisti)
    seciliSes = Property(int, lambda s: s._ses_secili, notify=seslerDegisti)
    hata = Property(str, lambda s: s._hata, notify=hataDegisti)
    hataBaslik = Property(str, lambda s: s._hata_baslik, notify=hataDegisti)
    cozuluyor = Property(bool, lambda s: s._cozuluyor, notify=cozuluyorDegisti)

    def konumuBildir(self):
        """Kaldığı yer kaydı için şimdiki yeri bildirir (kayit.konumKaydet'e bağlı). Canlı yayında
        kaldığı yer tutulmaz (yoksa yayının en eski noktasına atlıyordu; 22 Ekim)."""
        if not self._kimlik or (self._cozum and self._cozum["canli"]):
            return
        try:
            konum, sure = self.mpv.time_pos, self.mpv.duration
        except Exception:
            return
        if konum is not None and sure:
            self._son_konum = float(konum)
            self.konumBildirimi.emit(self._kimlik, float(konum), float(sure))

    def _simdiki_konum(self):
        """Videonun şimdiki yeri. _d["konum"] yalnız oynatıcı çubuğu görünürken güncellenir (zamanAraligi);
        çubuk gizliyken eski kalır. F5 bu yüzden videoyu baştan açıyordu (23 Ekim, tur 3)."""
        try:
            konum = self.mpv.time_pos
        except Exception:
            konum = None
        return float(konum) if konum is not None else max(self._son_konum, self._d["konum"] or 0.0)

    def _suresi_doldu(self):
        c = self._cozum
        return bool(c and c.get("gecerlilik") and time.time() > c["gecerlilik"] - 120)

    def _tazele(self, konum, durakli=False, not_=None):
        """Adresin süresi dolmuş: aynı videoyu aynı yerden, aynı boyut ve altyazıyla yeniden çözer."""
        if 0 <= self._kalite < len(self._kaliteler) and self._elle_secildi:
            self._tazele_kalite = self._kaliteler[self._kalite]["ad"]
        self._tazele_altyazi = self._altyazi_secili
        self.bildirim.emit(not_ or tr("Video adresi yenileniyor…"))
        self._ayni_izleme = True
        self.ac(self._kimlik, max(0.0, konum))

    @Slot()
    def yenile(self):
        """F5 (tarayıcı alışkanlığı): video kaldığı yerden, aynı boyut ve altyazıyla yeniden açılır."""
        if self._kimlik:
            canli = bool(self._cozum and self._cozum["canli"])
            self._tazele(0.0 if canli else self._simdiki_konum(), not_=tr("Video yeniden açılıyor…"))

    def _hatayla_bitti(self):
        if not self._kimlik:
            return
        if self._suresi_doldu():
            self._tazele(self._simdiki_konum())
        elif self._yeniden_denenen != self._kimlik:
            self._yeniden_denenen = self._kimlik
            iz.yaz(f"kendiliğinden yeniden açılıyor ({self._kimlik})")
            self._tazele(self._simdiki_konum(), not_=tr("Video yeniden açılıyor…"))
        else:
            bekle = YENIDEN_DENEME_SN[min(self._deneme_sayisi, len(YENIDEN_DENEME_SN) - 1)]
            self._deneme_sayisi += 1
            iz.yaz(f"yeniden açılamadı, {bekle} sn sonra yeniden denenecek ({self._kimlik})")
            print("Video açılamadı:", self._son_hata, file=sys.stderr, flush=True)
            self._deneme_zamani = time.time() + bekle
            self._deneme_saati.start(bekle * 1000)
            self._geri_sayim.start()
            self._geri_sayim_yaz()

    def _geri_sayim_yaz(self):
        kalan = max(1, round(self._deneme_zamani - time.time()))
        self._hata_baslik = ""
        self._hata = tr("Video açılamadı. %n sn sonra yeniden denenecek.", None, kalan)
        self.hataDegisti.emit()

    def _otomatik_dene(self):
        self._geri_sayim.stop()
        if self._kimlik:
            self._tazele(self._simdiki_konum(), not_=tr("Video yeniden açılıyor…"))

    @Slot()
    def durdurOynat(self):
        if self._d["durakli"] and self._suresi_doldu():
            # Uzun duraklatmadan sonra (~6 saat) eski adres açılmaz: önce yeniden çözülür.
            self._tazele(self._simdiki_konum())
            return
        if self._d["sonda"]:
            self._atlama_hedef = 0.0
            self.mpv.command_async("seek", 0, "absolute")
            self.mpv.pause = False
        else:
            self.mpv.cycle("pause")

    @Slot(float)
    def git(self, saniye):
        iz.yaz(f"atla {saniye:.0f} sn")
        self._atlama_hedef = max(0.0, saniye)
        if self._suresi_doldu():
            self._tazele(saniye)
            return
        self.mpv.command_async("seek", max(0.0, saniye), "absolute+exact")

    @Slot(float)
    def ileriGeri(self, saniye):
        iz.yaz(f"atla {saniye:+.0f} sn")
        self._atlama_hedef = max(0.0, (self.mpv.time_pos or 0.0) + saniye)
        if self._suresi_doldu():
            self._tazele((self.mpv.time_pos or 0.0) + saniye)
            return
        self.mpv.command_async("seek", saniye, "relative+exact")

    @Slot(float)
    def sesAyarla(self, deger):
        self.mpv.volume = max(0.0, min(100.0, deger))
        if deger > 0:
            self.mpv.mute = False

    @Slot()
    def sessizDegistir(self):
        self.mpv.cycle("mute")

    @Slot(float)
    def hizAyarla(self, deger):
        self.mpv.speed = round(max(0.1, min(4.0, deger)), 2)

    @Slot()
    def donguDegistir(self):
        self.mpv.loop_file = "no" if self._d["dongu"] not in (False, "no") else "inf"

    # ---- sağ tık menüsü (YouTube alışkanlığı)
    @Slot(bool, result=str)
    def baglanti(self, anli):
        """Videonun YouTube bağlantısı; anli: izleyen o saniyeden başlar."""
        if not self._kimlik:
            return ""
        adres = self._kimlik if "://" in self._kimlik else "https://www.youtube.com/watch?v=" + self._kimlik
        if anli and not (self._cozum and self._cozum["canli"]):
            adres += ("&" if "?" in adres else "?") + f"t={int(self._simdiki_konum())}s"
        return adres

    @Slot(bool)
    def baglantiKopyala(self, anli):
        adres = self.baglanti(anli)
        if adres:
            QGuiApplication.clipboard().setText(adres)
            self.bildirim.emit(tr("Bu andaki bağlantı kopyalandı") if anli else tr("Bağlantı kopyalandı"))

    @Slot(str)
    def kareKaydet(self, baslik):
        """O anki kare İndirilenler klasörüne PNG olarak (videonun kendi boyutunda, altyazısız)."""
        from . import indirme
        s = int(self._simdiki_konum())
        ad = f"{indirme.guvenli_ad(baslik or self._kimlik) or 'video'} {s // 60}-{s % 60:02d}.png"
        yol = str(indirme.klasor() / ad)
        try:
            self.mpv.command("screenshot-to-file", yol, "video")
        except (SystemError, RuntimeError) as e:
            iz.yaz("kare kaydedilemedi: " + (str(e) or e.__class__.__name__))
            self.bildirim.emit(tr("Kare kaydedilemedi"))
            return
        self.bildirim.emit(tr("Kare kaydedildi: %1").replace("%1", ad))

    @Slot(result="QVariantMap")
    def istatistik(self):
        """İstatistik panelinin satırları: eski bilgisayarda videonun neden takıldığını anlamak için."""
        def oku(ad, varsayilan=None):
            try:
                d = getattr(self.mpv, ad)
            except (AttributeError, RuntimeError, SystemError):
                return varsayilan
            return varsayilan if d is None else d
        p = oku("video_params", {}) or {}
        hw = oku("hwdec_current", "") or ""
        return {
            "boyut": f"{p.get('w', 0)}×{p.get('h', 0)}" if p.get("w") else "-",
            # video_format kısa ad (vp9, h264, av1); video_codec çözücünün adı ("Google VP9" ilk sözüyle "Google" görünüyordu).
            "bicim": {"h264": "H.264", "vp9": "VP9", "av1": "AV1", "hevc": "H.265"}.get(
                str(oku("video_format", "") or ""), str(oku("video_format", "-") or "-").upper()),
            "cozen": tr("ekran kartı (%1)").replace("%1", hw) if hw not in ("", "no") else tr("işlemci"),
            "atlanan": int(oku("frame_drop_count", 0)) + int(oku("decoder_frame_drop_count", 0)),
            "onden": round(float(oku("demuxer_cache_duration", 0.0)), 1),
            "hiz": int(oku("cache_speed", 0)) // 1024,
        }

    @Slot()
    def durdur(self):
        self.konumuBildir()
        self._deneme_saati.stop()
        self._geri_sayim.stop()
        if self._hata:
            self._hata_ver("")
        self._kimlik = ""
        self._cozuluyor_ver(False)
        self.mpv.command_async("stop")
        # mpv dosyayı kendi iş parçacıklarında kapatıyor (1 sn'den kısa); boşalan bellek ondan sonra geri verilir.
        if sys.platform.startswith("linux"):
            QTimer.singleShot(3000, _bellegi_geri_ver)

    def kapat(self):
        """Önce çizim bağlamı, sonra mpv; ters sırada çıkışta çöküyor."""
        self.konumuBildir()
        self._kapandi = True
        if self._cizici is not None and self._cizici.ctx is not None:
            # mpv çizim bağlamını kapatırken pencerenin OpenGL bağlamı etkin olmalı (libmpv render.h);
            # kapanışta etkin değil (denendi), çizicinin kurulurken tuttuğu bağlam etkin yapılır.
            gl, pen = self._cizici.gl, self.window()
            etkin = bool(gl and pen and gl.makeCurrent(pen))
            self._cizici.ctx.free()
            if etkin:
                gl.doneCurrent()
            self._cizici.ctx = None
        self.mpv.terminate()
        cozumle.dash_temizle()
        parca_araci.durdur()
