"""LiteVideoTube'un açılışı: Qt ayarları, QML türleri, pencere."""
import inspect
import os
import re
import signal
import sys
import time
from pathlib import Path

# Paketlenmiş programda (Windows kurulum klasörü) yardımcı programlar exe'nin yanında: libmpv-2.dll,
# yt-dlp.exe, ffmpeg.exe (indirmede birleştirme ve MP3), deno.exe (yt-dlp'nin YouTube için istediği
# JavaScript çalıştırıcısı). PATH'e eklenir ki python-mpv ve yt-dlp bulsun; mpv yüklenmeden önce.
if getattr(sys, "frozen", False):
    # Pencereli exe'de çıktı kanalı yok (sys.stdout None); print ve uyarılar hata vermesin.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    _yan = os.path.dirname(sys.executable)
    os.environ["PATH"] = _yan + os.pathsep + os.environ.get("PATH", "")
    if os.path.isfile(os.path.join(_yan, "yt-dlp.exe")):
        os.environ.setdefault("LVT_YTDL", os.path.join(_yan, "yt-dlp.exe"))

# Bu ayarlar Qt yüklenmeden önce yapılmalı.
if sys.platform.startswith("linux"):
    # X11'de ekran kartıyla doğrudan çözme (vaapi) EGL ister; Qt'nin varsayılanı GLX.
    os.environ.setdefault("QT_XCB_GL_INTEGRATION", "xcb_egl")
    # glibc yeni iş parçacıklarına ayrı bellek alanı açıyor (bu makinede 27'ye kadar); mpv her videoda iş
    # parçacığı açıp kapattığı için alanlarda boş ama geri verilmeyen bellek birikiyordu: 10 video aç/kapada
    # 245 → 380 MB ve artıyordu, 2 alanla 312 MB'ta duruyor (28 Ekim, araclar/gezinme/sizinti.py).
    # Kullanıcı MALLOC_ARENA_MAX vermişse o geçerli (glibc onu kendisi okur).
    if "MALLOC_ARENA_MAX" not in os.environ:
        try:
            import ctypes
            ctypes.CDLL(None).mallopt(-8, 2)   # M_ARENA_MAX
        except (OSError, AttributeError):
            pass
# Çizim tek iş parçacığında: mpv'yi çizen Python kodu Qt'nin çizim iş parçacığında çalışırsa
# Python kilidiyle donma olabiliyor (23 Ekim).
os.environ.setdefault("QSG_RENDER_LOOP", "basic")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PySide6.QtCore import Q_ARG, QBuffer, QCoreApplication, QEvent, QMetaObject, QObject, QPointF, QTimer, QUrl, Slot
from PySide6.QtGui import QGuiApplication, QImage, QImageReader
from PySide6.QtNetwork import QNetworkProxy
from PySide6.QtQml import QQmlApplicationEngine, QQmlImageProviderBase, qmlRegisterType
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow, QSGRendererInterface


def _kaynakta_pyside(modul):
    try:
        yol = inspect.getsourcefile(modul)
    except TypeError:   # sys gibi yerleşik modül
        return False
    if not yol:
        return False
    try:
        with open(yol, "rb") as f:
            return b"PySide6" in f.read()
    except OSError:
        return False


# PySide içe alınan her modülün kaynağında "PySide6" geçiyor mu diye bakıyor (programın kullanmadığı
# __feature__ desteği için) ve bunu inspect.getsource ile yaptığından her dosyanın metni linecache'te
# kalıyordu: 147 dosya, ~7 MB (28 Ekim ölçümü). Aynı denetim dosyayı belleğe almadan yapılır; PySide'ın
# iç yapısı değişirse eski hâli kalır.
try:
    import shibokensupport.feature as _pyside_ozellik
    if callable(getattr(_pyside_ozellik, "_mod_uses_pyside", None)):
        _pyside_ozellik._mod_uses_pyside = _kaynakta_pyside
except ImportError:
    pass

from . import ag, ceviri, iz, program_simgesi, yoklama
from .ceviri import tr
from .abonelik import Abonelik
from .geribildirim import GeriBildirim
from .guncelleme import Guncelleme
from .indirme import Indirici
from .kayit import Kayit
from . import kisi
from .kisi import Kisiler
from .liste import Listeler
from .oynatici import Oynatici
from .tarayici import FirefoxYardimi
from .veri import Veri
from .yenilikler import Yenilikler

KLASOR = Path(__file__).resolve().parent


class Pano(QObject):
    """QML panodan okuyamıyor (yalnız TextEdit üstünden); Ctrl+V ile bağlantı açmak için."""

    @Slot(result=str)
    def oku(self):
        return QGuiApplication.clipboard().text()


class KoyuSimgeler(QQuickImageProvider):
    """Açık görünümde simgelerin koyusu (Renk.qml, simge): "image://koyu/<ad>" beyaz çizilmiş simgeler/<ad>.svg'yi
    koyu çizer. Simgelerin ikinci bir takımı tutulmasın, yeni simge eklenince unutulmasın diye. Renkli simgeler
    (zilin mavisi, kalbin kırmızısı) olduğu gibi kalır. "image://koyu/<ad>/<renk>" (renk: altı haneli onaltılık)
    beyazı o renge çevirir; bölüm başlıklarının renkli simgeleri (Renk.qml, simgeRenkli)."""

    def __init__(self):
        super().__init__(QQmlImageProviderBase.ImageType.Image)

    def requestImage(self, ad, boy, istenen):
        ad, _, renk = ad.partition("/")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", renk):
            renk = "0f0f0f"
        yol = KLASOR / "simgeler" / (os.path.basename(ad) + ".svg")
        try:
            metin = yol.read_bytes().replace(b'fill="#ffffff"', b'fill="#' + renk.encode() + b'"')
        except OSError:
            return QImage()
        tampon = QBuffer()
        tampon.setData(metin)
        okuyucu = QImageReader(tampon, b"svg")
        if istenen.isValid() and istenen.width() > 0:
            okuyucu.setScaledSize(istenen)
        resim = okuyucu.read()
        if boy is not None:
            boy.setWidth(resim.width())
            boy.setHeight(resim.height())
        return resim


class OdakBekcisi(QObject):
    """Tıklamadan sonra klavye yalnız yazı kutusunda kalır; başka her yere tıklayınca tuşlar kısayollara
    (videoya) döner. Önceden arama kutusuna yazıp sayfaya tıklayınca harfler kutuya gitmeyi
    sürdürüyordu; İndir ya da Kaydet'e basınca boşluk videoyu durdurmak yerine o düğmenin menüsünü
    yeniden açıyordu. Sayfadaki öğeler tıklamayı kendileri karşıladığı için QML'deki TapHandler basışı
    göremiyordu; pencerenin olay süzgeci her basışı görür.

    Odak tıklama bittikten sonra (bırakınca) alınır. Önceden basar basmaz alınıyordu: düğme basılıyken odağını
    kaybedince tıklama sayılmıyordu; boş yere tıkladıktan sonra Yönet, Abone ol ve onay penceresinin düğmeleri ancak
    uzun basınca ya da hiç çalışmıyordu (Xephyr'de insan gibi 150 ms basılı tıklamayla görüldü, bekçi
    kapatılınca düzeldi). Açık bir menünün ya da pencerenin (Popup) içindeki odağa da dokunulmaz."""

    def __init__(self, pencere):
        super().__init__(pencere)
        self.pencere = pencere
        self._onceki = None
        self._basilan = QPointF()
        self._menude = False
        pencere.installEventFilter(self)

    def eventFilter(self, nesne, olay):
        if olay.type() == QEvent.MouseButtonPress:
            self._onceki = self.pencere.activeFocusItem()
            self._basilan = QPointF(olay.scenePosition())
            self.pencere.setProperty("sonBasis", self._basilan)   # sağ tık menüsü burada açılır (MenuKutusu.popup)
            self._menude = self._acik_menude(self._basilan)
        elif olay.type() == QEvent.MouseButtonRelease:
            yer = QPointF(olay.scenePosition())
            basilan, onceki, menude = self._basilan, self._onceki, self._menude
            QTimer.singleShot(0, lambda: self._bak(yer, basilan, onceki, menude))   # tıklama yerine ulaşıp bittikten sonra
        return False

    def _acik_menude(self, yer):
        """Basılan yer açık bir menünün ya da pencerenin (Popup) içinde mi."""
        for ust in self.pencere.contentItem().childItems():   # menüler pencerenin Overlay katmanında
            if "Overlay" not in ust.metaObject().className():
                continue
            for oge in ust.childItems():
                if oge.isVisible() and "PopupItem" in oge.metaObject().className() and oge.contains(oge.mapFromScene(yer)):
                    return True
        return False

    @staticmethod
    def _acilir(oge):
        """Öğe bir menünün ya da pencerenin (Popup) içindeyse o Popup, değilse None."""
        while oge is not None:
            if "PopupItem" in oge.metaObject().className():
                return oge.parent()   # QQuickPopupItem'ın sahibi Popup'ın kendisi
            oge = oge.parentItem()
        return None

    def _bak(self, yer, basilan, onceki, menude=False):
        # Seçili yazının dışına basıldıysa seçim kalkar. Bırakılan yere bakılmaz: sağdan sola seçen kişi fareyi
        # yazının solunda bırakır, seçim bırakınca kalkıyordu ("sağdan sola seçilince ... kalkıyor").
        # Menünün içine basış sayılmaz: yazının sağ tık menüsünde "Hepsini seç" seçtiği yazıyı hemen geri bırakıyordu.
        if not menude:
            self.pencere.basildi(basilan.x(), basilan.y())
        oge = self.pencere.activeFocusItem()
        if oge is None:
            return   # odak boşsa Ana.qml zaten kısayollara verir
        acilir = self._acilir(oge)
        if acilir is not None:
            # Menü ya da onay penceresi açık: ok tuşları ve Enter onun. Kapanınca (Esc de olsa) odak onu açan
            # düğmeye döner; tuşlar videoya gitsin, boşluk menüyü yeniden açmasın.
            if hasattr(acilir, "closed") and not acilir.property("_bekci"):
                acilir.setProperty("_bekci", True)
                acilir.closed.connect(lambda: QTimer.singleShot(0, self._kapaninca))
            return
        if (oge.inherits("QQuickTextInput") or oge.inherits("QQuickTextEdit")) and not oge.property("readOnly"):
            # Yazı kutusunun içine tıklandıysa, ya da kutuyu bu tıklamanın kendisi açtıysa ("Yeni kişi ekle" gibi;
            # xdotool'la hızlı tıkta bırakma bu bakıştan önce işleniyor, kutu odağı almış oluyordu) dokunulmaz.
            if oge.contains(oge.mapFromScene(yer)) or oge != onceki:
                return
            # Kutu kendi çevresini de içi sayabilir (Ust.qml: arama kutusunun ✕'ı).
            alan = oge.property("tiklamaAlani")
            if alan is not None and alan.contains(alan.mapFromScene(yer)):
                return
        elif oge.objectName() == "kisayol":
            return
        self.pencere.tuslariVideoyaVer()

    def _kapaninca(self):
        oge = self.pencere.activeFocusItem()
        if oge is not None and (oge.inherits("QQuickTextInput") or oge.inherits("QQuickTextEdit")):
            return
        if oge is None or self._acilir(oge) is None:
            self.pencere.tuslariVideoyaVer()


def calistir():
    iz.baslat()
    if ag.PROXY:
        # Küçük resimler Qt'nin kendi bağlantısıyla iner; o da sistemin proxy'sinden geçsin (ag.py).
        u = QUrl(ag.PROXY)
        QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.HttpProxy, u.host(), u.port(8080)))
        iz.yaz(f"proxy: {ag.PROXY}")
    elif ag.SEBEP:
        iz.yaz(f"proxy desteklenmiyor, doğrudan bağlanılıyor: {ag.SEBEP}")
    # mpv'nin çizim arayüzü OpenGL ister; Windows'ta Qt'nin varsayılanı Direct3D.
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    # Yakınlık (kişi menüsü, Ctrl+artı/eksi): bütün arayüz Qt'nin ölçeğiyle büyür ya da küçülür. Kullanıcı
    # QT_SCALE_FACTOR'ı kendisi verdiyse ona dokunulmaz; programın kendi verdiği (yeniden açılınca ortamda kalan) yenilenir.
    if "QT_SCALE_FACTOR" not in os.environ or os.environ.get("LVT_YAKINLIK_BIZDEN"):
        y = kisi.yakinlik_ayari()
        kisi.ACILISTAKI_YAKINLIK[0] = y
        if y != 100:
            os.environ["QT_SCALE_FACTOR"] = str(y / 100)
            os.environ["LVT_YAKINLIK_BIZDEN"] = "1"
        else:
            os.environ.pop("QT_SCALE_FACTOR", None)
            os.environ.pop("LVT_YAKINLIK_BIZDEN", None)
    app = QGuiApplication(sys.argv)
    # Yakınlık hiç seçilmemişse (ilk açılış) ekrana göre seçilir (kisi.ekrana_gore_yakinlik) ve kaydedilir. Qt'nin ölçeği
    # yalnız açılırken okunduğu için 100 değilse program, pencere görünmeden bir kez kendini yeniden başlatır.
    if "QT_SCALE_FACTOR" not in os.environ and not kisi.yakinlik_secildi():
        y = kisi.ekrana_gore_yakinlik(app.primaryScreen())
        kisi.yakinlik_kaydet(y)
        if y != 100:
            Kisiler.hemen_yeniden_baslat()
            return 0
    kisi.yeniden_durumunu_al()
    app.setApplicationName("LiteVideoTube")
    app.setOrganizationName("")
    app.setDesktopFileName("litevideotube")
    # Programın simgesi: pencere ve görev çubuğu; Linux'ta masaüstü dosyasındaki simge önce gelir.
    app.setWindowIcon(program_simgesi.simge())
    ceviri.kur(app)   # QML ve yazı üreten Python nesnelerinden önce
    qmlRegisterType(Oynatici, "LiteVideoTube", 1, 0, "Oynatici")
    yoklama.silinenleri_temizle()
    veri = Veri()
    kayit = Kayit()
    abonelik = Abonelik()
    listeler = Listeler()
    indirici = Indirici()
    motor = QQmlApplicationEngine()
    motor.addImageProvider("koyu", KoyuSimgeler())
    motor.rootContext().setContextProperty("veri", veri)
    motor.rootContext().setContextProperty("kayit", kayit)
    motor.rootContext().setContextProperty("abonelik", abonelik)
    motor.rootContext().setContextProperty("listeler", listeler)
    motor.rootContext().setContextProperty("indirici", indirici)
    pano = Pano()
    motor.rootContext().setContextProperty("pano", pano)
    kisiler = Kisiler()
    motor.rootContext().setContextProperty("kisiler", kisiler)
    yenilikler = Yenilikler()
    motor.rootContext().setContextProperty("yenilikler", yenilikler)
    geri_bildirim = GeriBildirim()
    motor.rootContext().setContextProperty("geriBildirim", geri_bildirim)
    guncelleme = Guncelleme()
    motor.rootContext().setContextProperty("guncelleme", guncelleme)
    firefox = FirefoxYardimi(abonelik)
    motor.rootContext().setContextProperty("firefox", firefox)
    motor.load(QUrl.fromLocalFile(str(KLASOR / "qml" / "Ana.qml")))
    if not motor.rootObjects():
        return 1
    pencere = motor.rootObjects()[0]
    # Yakınlıkla pencerenin ekrandaki boyu değişmesin (Qt'nin ölçeği pencereyi de büyütüp küçültüyor): açılış boyu
    # ölçeğe bölünür, ekranı aşarsa ekrana sığdırılır.
    y = kisi.ACILISTAKI_YAKINLIK[0]
    if kisi.pencereyi_yerlestir(pencere):
        pass
    elif y != 100:
        alan = pencere.screen().availableGeometry()
        pencere.resize(min(round(pencere.width() * 100 / y), alan.width()),
                       min(round(pencere.height() * 100 / y), alan.height()))
    OdakBekcisi(pencere)
    kisi.YakinlikTekerlegi(pencere, kisiler)
    if os.environ.get("LVT_KUCUK_SN"):   # deneme: küçültülmüş pencerede görüntünün kapanma süresi
        pencere.setProperty("kucukSuresi", int(float(os.environ["LVT_KUCUK_SN"]) * 1000))
    kisiler.kapat = pencere.close
    for o in pencere.findChildren(Oynatici):
        o.konumBildirimi.connect(kayit.konumKaydet)
        try:
            o.kaliciSinir = int(kayit.ayar("kalite") or 0)
        except ValueError:
            pass
        o.kaliteSecildi.connect(lambda boy: kayit.ayarYaz("kalite", str(boy)))
        o.dokumHazir.connect(lambda vid, baslik, dil, vtt, o=o: o.bildirim.emit(
            tr("Metin dökümü kaydedildi: %1").replace("%1", os.path.basename(indirici.dokum_kaydet(vid, baslik, dil, vtt)))))

    def kapanirken():
        # Önce pencere gizlenir: video çizicisi kapandıktan sonra bir kare daha çizilirse program
        # çöküyordu (kapanma sinyaliyle kapatınca 2 denemede 1; çarpıyla kapatınca pencere zaten gizli).
        pencere.hide()
        for o in pencere.findChildren(Oynatici):
            o.kapat()
        kurulacak = guncelleme.kapanirken()   # indirilmiş güncelleme varsa program kapanınca kurulur
        abonelik.kapanirken(not kurulacak)   # yoklama program kapalıyken arkada sürer (arkada.py)
    app.aboutToQuit.connect(kapanirken)
    # Kapanma sinyali (oturum ya da bilgisayar kapanırken) çarpıyla kapatmakla aynı yoldan gider. Python
    # sinyali herhangi bir Python satırında işler, video karesi çizilirken de; pencere orada kapatılınca
    # yarım kalan çizim silinmiş nesnelere dokunup çöküyordu (5 denemede 5). İş olay döngüsüne ertelenir.
    signal.signal(signal.SIGTERM, lambda *_: QTimer.singleShot(0, pencere.close))
    signal.signal(signal.SIGINT, lambda *_: QTimer.singleShot(0, pencere.close))
    saat = QTimer()
    saat.start(300)
    saat.timeout.connect(lambda: None)  # Python sinyalleri işleyebilsin

    # Sınama kipi: LVT_ARA="<sorgu>" arar ve ilk sonucu açar; LVT_SINAMA=<sn>,<png> o kadar sonra
    # pencerenin görüntüsünü kaydedip kapanır (Windows'ta GitHub Actions, burada elle deneme).
    if os.environ.get("LVT_BUYUK"):
        pencere.showMaximized()
    # Yeni kişi açılırken istendi (kisi.py): abonelikler tarayıcıdaki hesaptan bu kişiye getirilir.
    if kisi.YENIDEN.get("abone_tarayici") or os.environ.pop("LVT_ABONE_TARAYICI", None):   # ortam: Firefox denemesi
        QTimer.singleShot(300, abonelik.tarayicidanAl)
    if os.environ.get("LVT_ARA"):
        QTimer.singleShot(500, lambda: pencere.aramaYap(os.environ["LVT_ARA"]))
    if os.environ.get("LVT_AC"):
        QTimer.singleShot(500, lambda: pencere.videoAc(os.environ["LVT_AC"], None, False))
    # Güncelleme denemesi (windows-guncelleme-github.yml): LVT_GUNCELLEME_SEC="simdi" ya da "sonra" verilirse "Yeni sürüm
    # var" penceresi çıkınca resmi LVT_GUNCELLEME_RESIM'e kaydedilir ve o düğmeye basılır. "dil:<kod>" ya da "kisi":
    # güncelleme indikten sonra dil ya da kişi değiştirilir (programın yeniden açılması güncellemeyi kurmalı; kisi.py,
    # Kisiler._yeniden_ac).
    if os.environ.get("LVT_GUNCELLEME_SEC"):
        def guncelleme_sec():
            gp = pencere.findChild(QObject, "guncellemePenceresi")
            if os.environ.get("LVT_GUNCELLEME_RESIM"):
                pencere.grabWindow().save(os.environ["LVT_GUNCELLEME_RESIM"])
            sec = os.environ["LVT_GUNCELLEME_SEC"]
            if sec.startswith("dil:"):
                kisiler.dilSec(sec[4:])
                QMetaObject.invokeMethod(pencere, "durumlaYenidenAc")
            elif sec == "kisi":
                kisiler.sec(kisiler.ekle("Deneme"))
            else:
                QMetaObject.invokeMethod(gp, sec)
        guncelleme.hazir.connect(lambda _: QTimer.singleShot(1500, guncelleme_sec))
    # İlk açılış denemesi: LVT_DIL_SEC=<kod> verilirse dil penceresi açılınca o dil seçilir (makinede tıklayan yok).
    if os.environ.get("LVT_DIL_SEC"):
        def dil_sec():
            dp = next((o for o in pencere.findChildren(QObject) if o.metaObject().className().startswith("DilPenceresi_QMLTYPE")), None)
            if dp is not None and dp.property("opened"):
                QMetaObject.invokeMethod(dp, "sec", Q_ARG("QVariant", os.environ["LVT_DIL_SEC"]))
            else:
                QTimer.singleShot(1000, dil_sec)
        QTimer.singleShot(3000, dil_sec)
    # Firefox denemesi (windows-firefox-deneme.yml): LVT_FIREFOX_SINAMA=<klasör> verilirse Firefox penceresinin her
    # hâlinin resmi klasöre kaydedilir, hâller durumlar.txt'ye yazılır; "sor"da "Kur"a (ya da "Giriş yap"a) basılır,
    # "bekliyor"dan 20 sn sonra (makinede YouTube'a giriş yapılamaz), "hata"dan 5 sn sonra program kapanır.
    if os.environ.get("LVT_FIREFOX_SINAMA"):
        klasor = os.environ["LVT_FIREFOX_SINAMA"]
        os.makedirs(klasor, exist_ok=True)
        onceki = [None, 0]

        def firefox_hali():
            durum = firefox.durum
            if durum == onceki[0]:
                return
            onceki[0] = durum
            onceki[1] += 1
            with open(os.path.join(klasor, "durumlar.txt"), "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S')} {durum or 'kapali'} {firefox.aciklama}\n")
            ad = os.path.join(klasor, f"{onceki[1]:02d}-{durum or 'kapali'}.png")
            QTimer.singleShot(1500, lambda: pencere.grabWindow().save(ad))
            if durum == "sor":
                QTimer.singleShot(3000, firefox.evet)
            if durum in ("bekliyor", "hata"):
                QTimer.singleShot(20000 if durum == "bekliyor" else 5000,
                                  lambda: (pencere.grabWindow().save(os.path.join(klasor, "son.png")), app.quit()))
        firefox.degisti.connect(firefox_hali)
    if os.environ.get("LVT_SINAMA"):
        sure, png = os.environ["LVT_SINAMA"].split(",", 1)

        def sinama():
            pencere.grabWindow().save(png)
            o = pencere.findChild(Oynatici)
            durum = {"konum": round(o.mpv.time_pos or 0.0, 1), "sure": o._d["sure"], "cozucu": o._d["cozucu"],
                     "sayfa": pencere.property("sayfa"),
                     "surum": yenilikler.surumAdi, "dil": ceviri.kurulan_dil(), "kisi": kisiler.seciliAd,
                     "guncellendi_penceresi": bool(pencere.findChild(QObject, "guncellendiPenceresi").property("opened")),
                     "pencere": [pencere.x(), pencere.y(), pencere.width(), pencere.height()],
                     "kalite": o._kaliteler[o._kalite_secili]["ad"] if o._kalite_secili >= 0 else None}
            with open(png + ".txt", "w", encoding="utf-8") as f:   # pencereli exe'de çıktı yok
                f.write(repr(durum) + "\n")
            try:
                print(durum, flush=True)
            except (OSError, UnicodeError, AttributeError):   # Windows'ta çıktının kod sayfası "ş"yi yazamıyordu
                pass
            app.quit()
        QTimer.singleShot(int(float(sure) * 1000), sinama)
    rc = app.exec()
    # QML motoru Python nesnelerinden (veri, kayit) önce kapanmalı; yoksa kapanışta boş bağ uyarıları çıkar.
    # Önce pencere (bütün öğeler ve bağları) silinir: motor kapanırken bağlam boşalınca bağlar
    # yeniden hesaplanıp "of null" uyarıları yazıyordu.
    pencere.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    del pencere
    motor.deleteLater()
    del motor
    return rc
