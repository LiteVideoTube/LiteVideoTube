"""Arayüz ile YouTube verisi arasındaki köprü: istekler arka planda, sonuç sinyalle gelir.
Arayüz hiçbir zaman ağı beklerken donmaz."""
import threading

from PySide6.QtCore import QObject, Signal, Slot

from . import youtube
from .ceviri import tr


class Veri(QObject):
    aramaGeldi = Signal(str, list, bool)          # sorgu, videolar, devamı var mı
    videoGeldi = Signal(str, "QVariantMap")       # video id, sayfa bilgisi
    onerilerGeldi = Signal(str, list, bool)       # video id, ek öneriler, devamı var mı
    kanalGeldi = Signal(str, "QVariantMap")       # kanal id, kanal sayfası (ilk videolarla)
    kanalVideolariGeldi = Signal(str, list, bool)  # kanal id, ek videolar, devamı var mı
    kanalShortslariGeldi = Signal(str, list, bool, bool)  # kanal id, Shorts, devamı var mı, ilk parti mi
    hata = Signal(str, str)                       # ne yapılıyordu, hata
    # Yorumlar: video id, hangi istek ("" ilk parti ya da sıralama, yoksa yanıtları istenen yorumun id'si),
    # parti ({sayi, siralar, yorumlar, devam}); hata olursa parti {hata: metin}.
    yorumlarGeldi = Signal(str, str, "QVariantMap")

    def __init__(self):
        super().__init__()
        self._arama_devam = {}
        self._oneri_devam = {}
        self._kanal_devam = {}
        self._shorts_devam = {}
        self._kilit = threading.Lock()

    def _arkada(self, is_adi, islev, *args):
        def kos():
            try:
                islev(*args)
            except Exception as e:  # ağ, YouTube biçimi... arayüz düz bir uyarı gösterir
                self.hata.emit(is_adi, str(e) or e.__class__.__name__)
        threading.Thread(target=kos, daemon=True).start()

    @Slot(str)
    def ara(self, sorgu):
        def is_():
            s = youtube.ara(sorgu)
            with self._kilit:
                self._arama_devam[sorgu] = s["devam"]
            self.aramaGeldi.emit(sorgu, s["videolar"], bool(s["devam"]))
        self._arkada(tr("arama"), is_)

    @Slot(str)
    def aramaDevami(self, sorgu):
        def is_():
            with self._kilit:
                devam = self._arama_devam.get(sorgu)
            if not devam:
                return
            s = youtube.ara(None, devam)
            with self._kilit:
                self._arama_devam[sorgu] = s["devam"]
            self.aramaGeldi.emit(sorgu, s["videolar"], bool(s["devam"]))
        self._arkada(tr("arama"), is_)

    @Slot(str)
    def video(self, video_id):
        def is_():
            v = youtube.video_sayfasi(video_id)
            with self._kilit:
                self._oneri_devam[video_id] = v.pop("oneri_devam")
            self.videoGeldi.emit(video_id, v)
        self._arkada(tr("video"), is_)

    @Slot(str)
    def oneriDevami(self, video_id):
        def is_():
            with self._kilit:
                devam = self._oneri_devam.get(video_id)
            if not devam:
                return
            oneriler, sonraki = youtube.oneri_devami(devam)
            with self._kilit:
                self._oneri_devam[video_id] = sonraki
            self.onerilerGeldi.emit(video_id, oneriler, bool(sonraki))
        self._arkada(tr("öneriler"), is_)

    @Slot(str, str, str)
    def yorumlar(self, video_id, devam, yorum_id):
        """Bir parti yorum ya da (yorum_id verilince) o yorumun yanıtları. Anahtar arayüzde tutulur: ilk
        parti video sayfasının yorum_devam'ı, sonrakiler bir önceki partinin devam'ı."""
        def kos():
            try:
                parti = youtube.yorumlar(devam, video_id)
            except Exception as e:  # yorum bölümü kendi yerinde "alınamadı, yeniden dene" gösterir
                parti = {"hata": str(e) or e.__class__.__name__}
            self.yorumlarGeldi.emit(video_id, yorum_id, parti)
        threading.Thread(target=kos, daemon=True).start()

    @Slot(str)
    def kanal(self, kanal_id):
        def is_():
            k = youtube.kanal_sayfasi(kanal_id)
            with self._kilit:
                self._kanal_devam[kanal_id] = (k["ad"], k.pop("devam"))
            k["devamVar"] = bool(self._kanal_devam[kanal_id][1])
            self.kanalGeldi.emit(kanal_id, k)
        self._arkada(tr("kanal sayfası"), is_)

    @Slot(str)
    def kanalDevami(self, kanal_id):
        def is_():
            with self._kilit:
                ad, devam = self._kanal_devam.get(kanal_id, ("", None))
            if not devam:
                return
            videolar, sonraki = youtube.kanal_devami(kanal_id, ad, devam)
            with self._kilit:
                self._kanal_devam[kanal_id] = (ad, sonraki)
            self.kanalVideolariGeldi.emit(kanal_id, videolar, bool(sonraki))
        self._arkada(tr("kanal videoları"), is_)

    # Kanal sayfasının Shorts bölümü (bir kanalın bütün Shorts'larını görmek isteyen buraya girer).
    @Slot(str)
    def kanalShorts(self, kanal_id):
        def is_():
            vler, devam = youtube.kanal_shorts(kanal_id)
            with self._kilit:
                self._shorts_devam[kanal_id] = devam
            self.kanalShortslariGeldi.emit(kanal_id, vler, bool(devam), True)
        self._arkada(tr("kanalın Shorts'ları"), is_)

    @Slot(str)
    def kanalShortsDevami(self, kanal_id):
        def is_():
            with self._kilit:
                devam = self._shorts_devam.get(kanal_id)
            if not devam:   # devamı yok: bekleyen (Shorts görünümü) bitti desin
                self.kanalShortslariGeldi.emit(kanal_id, [], False, False)
                return
            vler, sonraki = youtube.kanal_devami(kanal_id, "", devam)
            with self._kilit:
                self._shorts_devam[kanal_id] = sonraki
            self.kanalShortslariGeldi.emit(kanal_id, vler, bool(sonraki), False)
        self._arkada(tr("kanalın Shorts'ları"), is_)
