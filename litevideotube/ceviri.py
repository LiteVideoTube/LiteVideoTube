"""Programın dili (29 Ekim: dil seçme yeri var, ilk açılışta sorulur). Qt'nin çeviri düzeni kullanılır.

Kaynak dil Türkçe: yazılar kodda Türkçe durur; öbür diller ceviri/litevideotube_<dil>.ts'te, program derlenmiş
.qm'yi okur (araclar/ceviri.sh çıkarır ve derler). Python'da tr("..."), QML'de qsTr("..."). Sayı içeren yazı
tek parça cümle olur, sayı %n ile verilir (tr("%n gün önce", None, n)): her dilin tekil ve çoğul biçimi ayrı.
Program açılmadan (import anında) değerlendirilen sabitler QT_TR_NOOP ile işaretlenir, kullanılırken tr()'den
geçer; o anda çevirmen henüz kurulmamış olur.

Dil sırası: kişilerin ortak ayarı "dil" (kisiler.json), yoksa bilgisayarın dili. O dilin çevirisi yoksa İngilizce,
o da yoksa Türkçe. Denemede LVT_DIL=<dil> ayarı geçersiz kılar.
"""
import os
import sys
from pathlib import Path

KLASOR = Path(__file__).resolve().parent / "ceviri"
KAYNAK_DIL = "tr"
YEDEK_DIL = "en"


def tr(metin, ayirt=None, n=-1):
    """Bağlamsız çeviri (araclar/ceviri.sh'deki pyside6-lupdate Python'da tr("...") çağrılarını boş bağlamla toplar).
    Adı ve imzası Qt'ninki gibi kalmalı: lupdate çağrıyı adından, sayıyı üçüncü değerden tanıyor.
    Qt'yi yüklemeyen arka plan yoklaması (arkada.py, youtube.py'yi kullanıyor) Qt'yi bunun için yüklemez: yazı Türkçe kalır."""
    if "PySide6.QtCore" not in sys.modules:
        return metin.replace("%n", str(n)) if n >= 0 else metin
    from PySide6.QtCore import QCoreApplication
    return QCoreApplication.translate("", metin, ayirt, n)


def QT_TR_NOOP(metin):   # noqa: N802 (lupdate bu adı tanıyor)
    return metin


def istenen_dil():
    """Kişinin seçtiği dil ("" ise seçilmemiş: bilgisayarın dili)."""
    if os.environ.get("LVT_DIL"):
        return os.environ["LVT_DIL"]
    from PySide6.QtCore import QLocale
    from . import yoklama
    return yoklama.kisiler().get("dil", "") or QLocale.system().name().split("_")[0]


_kurulan = [KAYNAK_DIL]
# Sağdan sola yazılan diller: düzen aynalanır (QML'de LayoutMirroring, Ana.qml). 29 Ekim: Arapça ilk.
SAGDAN_SOLA = ("ar", "fa")

# Dil seçme ekranı (DilPenceresi.qml; 29 Ekim: düz liste değil, önce bölge): dilin kendi dilindeki adı ve
# göründüğü bölgeler. Bir dil, konuşulduğu her bölgede görünür (İspanyolca Avrupa'da da Latin Amerika'da da).
# Yalnız çevirisi olan diller gösterilir (mevcut_diller).
DILLER = {
    "tr": ("Türkçe", ("avrupa", "asya")),
    "en": ("English", ("avrupa", "asya", "afrika", "kuzey_amerika")),
    "es": ("Español", ("avrupa", "kuzey_amerika", "latin_amerika")),
    "pt": ("Português (Brasil)", ("avrupa", "afrika", "latin_amerika")),
    "fr": ("Français", ("avrupa", "afrika", "kuzey_amerika")),
    "ru": ("Русский", ("avrupa", "asya")),
    "uk": ("Українська", ("avrupa",)),
    "pl": ("Polski", ("avrupa",)),
    "hi": ("हिन्दी", ("asya",)),
    "bn": ("বাংলা", ("asya",)),
    "id": ("Bahasa Indonesia", ("asya",)),
    "vi": ("Tiếng Việt", ("asya",)),
    "ar": ("العربية", ("asya", "afrika")),
    "fa": ("فارسی", ("asya",)),
}


def mevcut_diller():
    """Çevirisi olan diller (Türkçe hep), DILLER sırasıyla."""
    from PySide6.QtCore import QTranslator
    sonuc = []
    for kod in DILLER:
        if kod != KAYNAK_DIL:
            c = QTranslator()
            if not (c.load(str(KLASOR / f"litevideotube_{kod}.qm")) and not c.isEmpty()):
                continue
        sonuc.append(kod)
    return sonuc


def dil_secildi():
    """Dil seçme penceresi ilk açılışta çıksın mı. Denemelerde (LVT_DIL, LVT_SINAMA) çıkmaz."""
    if os.environ.get("LVT_DIL") or os.environ.get("LVT_SINAMA"):
        return True
    from . import yoklama
    return bool(yoklama.kisiler().get("dil"))


def dil_kaydet(kod):
    from . import yoklama
    k = yoklama.kisiler()
    k["dil"] = kod
    yoklama.kisileri_yaz(k)


def kur(app):
    """Çevirmeni kurar, kurulan dili döndürür. QML yüklenmeden önce çağrılır. Qt'nin varsayılan yerel ayarı da o dile
    alınır (ülke bilgisayarınki): QML'deki Qt.locale() ve QLocale() tarih, sayı, ondalık ayırıcıyı o dile göre yazar."""
    from PySide6.QtCore import QLocale, Qt, QTranslator
    from PySide6.QtGui import QGuiApplication
    dil = istenen_dil()
    if dil != KAYNAK_DIL:
        cevirmen = QTranslator(app)
        for aday in (dil, YEDEK_DIL):
            # Çevirisi henüz boş dilin .qm'si de yükleniyor; boşsa yedeğe geçilir.
            if cevirmen.load(str(KLASOR / f"litevideotube_{aday}.qm")) and not cevirmen.isEmpty():
                app.installTranslator(cevirmen)
                _kurulan[0] = aday
                break
    QLocale.setDefault(QLocale(_kurulan[0] + "_" + ulke()))
    if _kurulan[0] in SAGDAN_SOLA:
        QGuiApplication.setLayoutDirection(Qt.RightToLeft)
    return _kurulan[0]


def kurulan_dil():
    """Programın ekrandaki dili ("tr", "en"...). Qt'siz süreçte (arka plan yoklaması) hep Türkçe."""
    return _kurulan[0]


def ulke():
    """YouTube'un hangi ülkeye göre içerik vereceği (gündem, öneriler; gl): kişilerin ortak "bolge" ayarı (dil seçme
    ekranı yazacak), yoksa bilgisayarın ülkesi, o da belli değilse TR. Qt'siz süreçte TR."""
    if os.environ.get("LVT_ULKE"):
        return os.environ["LVT_ULKE"]
    if "PySide6.QtCore" not in sys.modules:
        return "TR"
    if not _ulke:
        from PySide6.QtCore import QLocale
        from . import yoklama
        u = yoklama.kisiler().get("bolge", "") or QLocale.system().name().partition("_")[2]
        _ulke.append(u.upper() if len(u) == 2 and u.isalpha() else "TR")
    return _ulke[0]


_ulke = []
