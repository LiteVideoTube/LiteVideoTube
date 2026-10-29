"""Kişiler: programı birden çok kişi kullanabilir, ya da bir kişinin iki YouTube hesabı olabilir.
Her kişinin abonelikleri, zili, geçmişi, listeleri ve programın kendi sıralaması ayrı (kayıtların yeri: yoklama.py,
veri_klasoru). Kişi silinince kayıtları da silinir. İki hesabı olan seçer: ikinci hesabın aboneliklerini aynı kişiye getirirse birleşir, yeni kişi
açarsa ayrı durur. Kişi değişince program kendini o kişinin kayıtlarıyla yeniden açar: bütün parçalar (geçmiş,
abonelik, listeler, arka plan yoklaması) kayıtlarını açılışta bulur, çalışırken değiştirmek bir yeri unutturabilirdi.
"""
import json
import os
import re
import subprocess
import sys
import time

from PySide6.QtCore import Property, QEvent, QObject, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

from . import arkada, ceviri, yoklama
from .guncelleme import Guncelleme
from .ceviri import tr


class Kisiler(QObject):
    degisti = Signal()

    def __init__(self):
        super().__init__()
        self.kapat = None   # pencere kurulunca uygulama.py verir

    def _liste(self):
        return [dict(x, ad=gorunen_ad(x)) for x in yoklama.kisiler()["liste"]]
    liste = Property(list, _liste, notify=degisti)
    secili = Property(str, lambda s: yoklama.secili_kisi(), notify=degisti)

    @Property(str, notify=degisti)
    def seciliAd(self):
        k = yoklama.secili_kisi()
        return next((x["ad"] for x in self._liste() if x["id"] == k), "")

    @Slot(str, result=str)
    def ekle(self, ad):
        """Yeni kişi; kimliği döner. Kayıtları ilk açılışta kendi klasöründe kurulur."""
        k = yoklama.kisiler()
        kimlik = "k" + str(int(time.time() * 1000))
        # Yeni kişi ekleyenin yakınlığıyla başlar.
        # Ad yazılmadıysa kayda Türkçe "Kişi N" girer, ekranda programın dilinde görünür (gorunen_ad).
        k["liste"].append({"id": kimlik, "ad": ad.strip() or f"Kişi {len(k['liste']) + 1}", "yakinlik": yakinlik_ayari()})
        yoklama.kisileri_yaz(k)
        self.degisti.emit()
        return kimlik

    @Slot(str, str)
    def adDegistir(self, kimlik, ad):
        k = yoklama.kisiler()
        for x in k["liste"]:
            if x["id"] == kimlik and ad.strip():
                x["ad"] = ad.strip()
        yoklama.kisileri_yaz(k)
        self.degisti.emit()

    @Slot(str)
    def sil(self, kimlik):
        """Kişi kayıtlarıyla birlikte silinir; son kişi silinmez. Seçili kişi silinirse program listedeki ilk kişiyle
        yeniden açılır. Dosyalar hemen silinemeyebilir (o kişinin kaydı bu kopyada ya da arka plan yoklamasında açık,
        Windows açık dosyayı silmez); kalanı her açılışta yeniden denenir (yoklama.silinenleri_temizle)."""
        k = yoklama.kisiler()
        if len(k["liste"]) < 2 or not any(x["id"] == kimlik for x in k["liste"]):
            return
        k["liste"] = [x for x in k["liste"] if x["id"] != kimlik]
        k["silinen"] = k.get("silinen", []) + [kimlik]
        yoklama.kisileri_yaz(k)
        if kimlik == yoklama.secili_kisi():
            self._gec(k["liste"][0]["id"], False)
        else:
            yoklama.silinenleri_temizle()
            self.degisti.emit()

    # Görünüm (Renk.qml): "cihaz", "koyu", "acik". Kişinin değil programın ayarı; kişi değişince aynı kalır.
    @Property(str, notify=degisti)
    def gorunum(self):
        return yoklama.kisiler().get("gorunum", "cihaz")

    @Slot(str)
    def gorunumSec(self, g):
        k = yoklama.kisiler()
        k["gorunum"] = g
        yoklama.kisileri_yaz(k)
        self.degisti.emit()

    # Yakınlık (bütün arayüz birlikte büyür ya da küçülür; tarayıcıdaki Ctrl+artı/eksi gibi). Programın ayarı,
    # açılışta Qt'nin ölçeğine verilir (uygulama.py); değişince program yeniden açılınca geçerli olur. Anında
    # büyütme denendi (sayfanın tek kutuda ölçeklenmesi): yazılar ve video bulanıklaşıyordu (28 Ekim).
    YAKINLIKLAR = [50, 60, 67, 75, 80, 90, 100, 110, 125, 150]

    @Property(int, notify=degisti)
    def yakinlik(self):
        return yakinlik_ayari()

    @Property(int, constant=True)
    def acikYakinlik(self):
        return ACILISTAKI_YAKINLIK[0]

    @Slot(int)
    def yakinlikDegistir(self, yon):
        """yon: +1 bir adım büyük, -1 bir adım küçük, 0 %100."""
        y = self.yakinlik
        a = self.YAKINLIKLAR
        if yon == 0:
            yeni = 100
        elif yon > 0:
            yeni = next((x for x in a if x > y), a[-1])
        else:
            yeni = next((x for x in reversed(a) if x < y), a[0])
        yakinlik_kaydet(yeni)
        self.degisti.emit()

    @Slot(str)
    def yenidenAc(self, durum):
        """Yakınlık geçerli olsun: program kapanıp aynı kişiyle yeniden açılır (sekmeler geri gelir). durum (Ana.qml,
        JSON): oynuyor mu, pencerenin yeri ve boyu (eski ölçekte), büyütülmüş mü; yeni kopya ondan sürdürür."""
        self._yeniden_ac(json.loads(durum))

    # Programın dili (ceviri.py; 29 Ekim): ilk açılışta sorulur, kişi menüsünden değişir. Kişinin değil programın
    # ayarı. Değişince program yeniden açılır (Ana.qml, durumlaYenidenAc): bazı yazılar Python'da açılışta kuruluyor.
    dil = Property(str, lambda s: ceviri.kurulan_dil(), constant=True)

    @Property(bool, notify=degisti)
    def dilSecildi(self):
        return ceviri.dil_secildi()

    @Property(list, constant=True)
    def diller(self):
        return [{"kod": k, "ad": ceviri.DILLER[k][0], "bolgeler": list(ceviri.DILLER[k][1])} for k in ceviri.mevcut_diller()]

    @Slot(str)
    def dilSec(self, kod):
        ceviri.dil_kaydet(kod)
        self.degisti.emit()

    @Slot(result=bool)
    def ctrlBasili(self):
        return bool(QGuiApplication.queryKeyboardModifiers() & Qt.ControlModifier)

    # Yakınlık için yeniden açıldıysa video duraklatılmadan sürer (normal açılışta ses birden çalmasın diye duraklatılır).
    yenidenOynat = Property(bool, lambda s: bool(YENIDEN.get("oynat")), constant=True)
    yenidenKaydirma = Property(str, lambda s: json.dumps(YENIDEN["kaydirma"]) if YENIDEN.get("kaydirma") else "", constant=True)

    tekerlek = Signal(int)   # Ctrl + fare tekerleği: +1 büyüt, -1 küçült (YakinlikTekerlegi)


    @Slot(str)
    def sec(self, kimlik):
        self._gec(kimlik, False)

    @Slot(str)
    def yeniKisiyeTarayicidanAl(self, ad):
        """İkinci hesabı ayrı tutmak: yeni kişi açılır, program o kişiyle açılınca abonelikleri tarayıcıdan getirir."""
        self._gec(self.ekle(ad), True)

    def _gec(self, kimlik, tarayicidan_al):
        if kimlik == yoklama.secili_kisi() and not tarayicidan_al:
            return
        k = yoklama.kisiler()
        k["secili"] = kimlik
        yoklama.kisileri_yaz(k)
        self._yeniden_ac({"abone_tarayici": tarayicidan_al}, kisi_degisti=True)

    @staticmethod
    def hemen_yeniden_baslat():
        """Pencere açılmadan önce: programın yeni bir kopyası aynı ortamla başlar, bu kopya çıkar."""
        kw = {"cwd": arkada._proje_klasoru(), "env": dict(os.environ)}
        if sys.platform == "win32":
            kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED, NEW_PROCESS_GROUP
        else:
            kw["start_new_session"] = True
        subprocess.Popen(arkada.komut()[:-1] + sys.argv[1:], **kw)

    def _yeniden_ac(self, durum, kisi_degisti=False):
        """Programın kendini yeniden açmasının tek kapısı (yakınlık, dil, kişi; 29 Ekim). İndirilmiş bir güncelleme
        bekliyorsa programı Velopack açar: güncellemeyi kurar, yeni sürümü başlatır. Önceden program eski sürümün yeni
        bir kopyasını açarken Velopack aynı klasöre kurmaya başlıyordu. Durum (sekmeler, video, pencerenin yeri) bu yüzden
        ortam değişkeniyle değil dosyayla geçer (yeniden_durumunu_al); Velopack'in açtığı kopyaya ortam verilemez.
        Programı yeniden başlatan başka bir yer olmasın: araclar/yeniden_kapisi_sinama.py bakar."""
        yol = yoklama.kok_klasor() / YENIDEN_DOSYA
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(json.dumps(dict(durum, zaman=time.time())), encoding="utf-8")
        g = Guncelleme.etkin
        if g is None or not g.simdiYukle():
            ortam = dict(os.environ)
            for ad in ("LVT_AC", "LVT_ARA", "LVT_SINAMA") + (("LVT_KISI",) if kisi_degisti else ()):
                ortam.pop(ad, None)
            kw = {"cwd": arkada._proje_klasoru(), "env": ortam}
            if sys.platform == "win32":
                kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED, NEW_PROCESS_GROUP
            else:
                kw["start_new_session"] = True
            # Yeni kopya, bu kopya kapanırken başlar (aynı anda iki pencere ve iki video olmasın).
            QGuiApplication.instance().aboutToQuit.connect(lambda: subprocess.Popen(arkada.komut()[:-1], **kw))
        self.kapat()


# Açılışta Qt'ye verilen yakınlık (uygulama.py yazar); menü, seçilenle farklıysa "yeniden açılınca" der.
ACILISTAKI_YAKINLIK = [100]

# Kendiliğinden verilen ad ("Kişi 1", ilk kişi ve adı yazılmadan eklenen kişi; yoklama.py, Kisiler.ekle) kayıtta Türkçe
# durur, ekranda programın dilinde görünür ("Profile 1", "نمایه 1"). Kişinin kendi verdiği ad olduğu gibi kalır.
_KENDILIGINDEN = re.compile(r"Kişi (\d+)")


def gorunen_ad(kisi):
    m = _KENDILIGINDEN.fullmatch(kisi.get("ad", ""))
    return tr("Kişi %1").replace("%1", m.group(1)) if m else kisi.get("ad", "")

# Program yeniden açıldıysa önceki kopyanın bıraktığı durum (Kisiler._yeniden_ac): yakınlıkta ve dilde sekmeler, video,
# pencerenin yeri; kişi değişince yalnız "abonelikleri tarayıcıdan getir". Dosya okununca silinir, sonraki açılışa geçmez.
# Yeniden açılış olmadıysa (Velopack kuramadı, program açılmadı) eski dosyaya bakılmaz.
YENIDEN_DOSYA = "yeniden.json"
YENIDEN_GECERLI_SN = 600
YENIDEN = {}


def yeniden_durumunu_al():
    """Açılışta bir kez (uygulama.py), pencere kurulmadan önce."""
    yol = yoklama.kok_klasor() / YENIDEN_DOSYA
    try:
        d = json.loads(yol.read_text(encoding="utf-8"))
        yol.unlink()
    except (OSError, ValueError):
        return
    if isinstance(d, dict) and 0 <= time.time() - d.get("zaman", 0) < YENIDEN_GECERLI_SN:
        YENIDEN.update(d)


def pencereyi_yerlestir(pencere):
    """Yakınlık değişince pencere ekranda aynı yerde ve aynı boyda kalsın, büyütülmüşse büyütülmüş açılsın. Qt'nin ölçeği
    pencerenin boyunu da çarptığı için eski ölçekteki boy önce ekran pikseline, sonra yeni ölçeğe çevrilir."""
    d = YENIDEN
    if not d.get("w"):
        return False
    eski, yeni = (d.get("olcek") or 100) / 100, ACILISTAKI_YAKINLIK[0] / 100
    c = lambda v: round(v * eski / yeni)
    pencere.setGeometry(c(d["x"]), c(d["y"]), c(d["w"]), c(d["h"]))
    if d.get("buyuk"):
        pencere.showMaximized()
    return True


class YakinlikTekerlegi(QObject):
    """Ctrl + fare tekerleği yakınlığı değiştirir (tarayıcıdaki gibi); o sırada sayfa kaymaz. Dokunmatik yüzey küçük
    adımlar gönderir: bir çentik (120) birikince bir adım."""

    def __init__(self, pencere, kisiler):
        super().__init__(pencere)
        self.kisiler = kisiler
        self._birikim = 0
        pencere.installEventFilter(self)

    def eventFilter(self, nesne, olay):
        if olay.type() != QEvent.Wheel or not (olay.modifiers() & Qt.ControlModifier):
            return False
        d = olay.angleDelta().y()
        if self._birikim and (d > 0) != (self._birikim > 0):
            self._birikim = 0   # yön değişti
        self._birikim += d
        while abs(self._birikim) >= 120:
            yon = 1 if self._birikim > 0 else -1
            self._birikim -= 120 * yon
            self.kisiler.tekerlek.emit(yon)
        return True


# Yakınlık kişi başına (28 Ekim; aynı bilgisayarı kullananların gözü aynı değil): seçili
# kişinin kisiler.json'daki kaydında. Kökteki "yakinlik" kişi başına geçmeden önceki ortak değer; kendi değeri olmayan
# kişi onu kullanır.
def _kisi_kaydi(k):
    s = yoklama.secili_kisi()
    return next((x for x in k["liste"] if x["id"] == s), None)


def yakinlik_secildi():
    k = yoklama.kisiler()
    return "yakinlik" in (_kisi_kaydi(k) or {}) or "yakinlik" in k


def ekrana_gore_yakinlik(ekran):
    """Kullanıcı yakınlık seçmemişken (ilk açılış) ekrana göre: yazılar her ekranda aşağı yukarı aynı boyda görünsün.
    Ölçü 14 inç 1920x1080 bir ekran (158 nokta/inç, sistemde büyütme yok): orada %80. Orada %60 da okunur;
    varsayılan biraz iri tutuldu, gözü zayıf olan da ilk açılışta okuyabilsin (28 Ekim). Seyrek pikselli ekranda
    küçültmek yazıyı fiziksel olarak aynı boya getirse de harfler az pikselle çizilip okunmaz olurdu: 14 piksellik yazı
    ekranda 11 pikselin altına inmez. Varsayılan büyütmez (Windows'un kendi büyütmesi, devicePixelRatio, zaten var) ve
    %67'nin altına inmez (sistemin büyütmesini fazla bozmasın, yüzde de tuhaf görünmesin). Sonuç çoğu ekranda %80,
    Windows'ta büyütme %125-150 ise %67."""
    dpi = ekran.physicalDotsPerInch()
    oran = ekran.devicePixelRatio() or 1
    if not 50 <= dpi <= 400:
        return 100   # ekranın boyu okunamadı (sanal makine, projeksiyon)
    y = min(100, max(67, 80 * dpi / oran / 158, 100 * 11 / (14 * oran)))
    return min(Kisiler.YAKINLIKLAR, key=lambda a: abs(a - y))


def yakinlik_kaydet(y):
    k = yoklama.kisiler()
    (_kisi_kaydi(k) or k)["yakinlik"] = y
    yoklama.kisileri_yaz(k)


def yakinlik_ayari():
    k = yoklama.kisiler()
    try:
        y = int((_kisi_kaydi(k) or {}).get("yakinlik", k.get("yakinlik", 100)))
    except (TypeError, ValueError):
        return 100
    return min(max(y, Kisiler.YAKINLIKLAR[0]), Kisiler.YAKINLIKLAR[-1])
