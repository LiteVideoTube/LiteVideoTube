"""Aboneliklerin okunduğu tarayıcılar ve Firefox'la elden tutma.

Abonelik listesi tarayıcının YouTube girişinden okunur (abonelik.py, _tarayicidan_al). Hiçbir tarayıcıda giriş
bulunamazsa program tek bir soru sorar (qml/FirefoxPenceresi.qml): Firefox yoksa "Firefox kurulsun mu? Kur / Hayır",
varsa "Firefox'ta giriş yap / Hayır". "Kur"da Firefox Mozilla'nın kendi sitesinden iner ve kurulur; sonra YouTube'un
giriş sayfası Firefox'ta açılır, program giriş yapılana kadar birkaç saniyede bir bakar ve giriş olunca abonelikleri
kendisi getirir. Kişinin programa dönüp bir şeye basması gerekmez.

Neden Firefox: Windows'ta Chrome ve Edge 2024'ten beri çerezlerini kilitliyor (app-bound encryption), yt-dlp
okuyamıyor. Firefox'unkini her sistemde okuyabiliyor.

Firefox açıkken yeni çerezler cookies.sqlite'ın yanındaki -wal dosyasında duruyor (SQLite WAL). yt-dlp yalnız ana
dosyayı kopyaladığı için az önce yapılan girişi görmüyordu (28 Ekim, başsız Firefox'la denendi: ana dosyada 0 çerez,
-wal'la birlikte 8). Bu yüzden çerezler iki dosyasıyla geçici bir klasöre kopyalanıp orada birleştirilir
(girisli_kopya) ve yt-dlp'ye o klasör verilir. Birden çok profil varsa girişi olan seçilir.

Sınama: LVT_FIREFOX_PROFIL bir profil klasörü verir (çerezler oradan okunur, Firefox o profille açılır);
LVT_FIREFOX_YOK Firefox kurulu değilmiş gibi yapar; LVT_YONETICI Linux'ta pkexec yerine kullanılır;
LVT_FIREFOX_GUNLUK kurulumun adımlarını (imza denetimi, kurucunun çıkışı) bir dosyaya yazar.
"""
import glob
import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time

import urllib3
from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from . import ag
from .ceviri import kurulan_dil, tr

WINDOWS = sys.platform == "win32"


def giris_adresi():
    """YouTube'un kendi "Oturum aç" bağlantısı: Google girişinden sonra YouTube'a döner, YouTube çerezleri o an yazılır.
    Sayfalar programın dilinde (hl)."""
    d = kurulan_dil()
    return (f"https://accounts.google.com/ServiceLogin?service=youtube&uilel=3&passive=true&hl={d}&continue="
            f"https%3A%2F%2Fwww.youtube.com%2Fsignin%3Faction_handle_signin%3Dtrue%26app%3Ddesktop%26hl%3D{d}"
            "%26next%3Dhttps%253A%252F%252Fwww.youtube.com%252F")


def hesap_secme_adresi():
    """Girişli hesapta abonelik yoksa: Google'ın hesap seçme sayfası (başka hesapla girmek ya da hesap eklemek için)."""
    return giris_adresi().replace("/ServiceLogin?", "/AccountChooser?").replace("&passive=true", "")


# Tam kurulum dosyası (Firefox 159, 28 Ekim: 95 MB). Mozilla'nın küçük kurucusu sessiz kurulamıyor. Firefox programın
# dilinde kurulur; Mozilla'nın tanımadığı dil kodu indirmeyi bozar, o yüzden yalnız bilinenler, gerisi İngilizce.
KURULUM_ADRESI = "https://download.mozilla.org/?product=firefox-latest-ssl&os={}&lang={}"
FIREFOX_DILLERI = {"tr": "tr", "en": "en-US", "es": "es-ES", "pt": "pt-BR", "ru": "ru", "uk": "uk", "pl": "pl",
                   "fr": "fr", "de": "de", "it": "it", "nl": "nl", "id": "id", "vi": "vi", "hi": "hi-IN", "bn": "bn",
                   "ar": "ar", "fa": "fa", "ja": "ja", "ko": "ko", "zh": "zh-CN"}
SITE = "https://www.mozilla.org/{}/firefox/new/"
BAKIS_ARALIGI = 3000              # giriş beklenirken (ms)
BEKLEME_EN_COK = 20 * 60          # bu kadar sürede giriş görülmezse beklemek bırakılır (sn)
# yt-dlp'nin "giriş yapılmış" saydığı çerezler (extractor/youtube/_base.py, _has_auth_cookies).
GIRIS_CEREZI = "LOGIN_INFO"
SID_CEREZLERI = ("SAPISID", "__Secure-1PAPISID", "__Secure-3PAPISID")
_YOK = 0x08000000 if WINDOWS else 0   # CREATE_NO_WINDOW: pencereli exe'de PowerShell penceresi açılmasın


# ---- hangi tarayıcılar var
def _config():
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")


def _chromium_klasoru(ad):
    """yt-dlp'nin baktığı yer (cookies.py, _get_chromium_based_browser_settings); orada yoksa yt-dlp de bulamaz."""
    if WINDOWS:
        yerel, gezgin = os.path.expandvars("%LOCALAPPDATA%"), os.path.expandvars("%APPDATA%")
        return {"brave": os.path.join(yerel, r"BraveSoftware\Brave-Browser\User Data"),
                "chrome": os.path.join(yerel, r"Google\Chrome\User Data"),
                "chromium": os.path.join(yerel, r"Chromium\User Data"),
                "edge": os.path.join(yerel, r"Microsoft\Edge\User Data"),
                "opera": os.path.join(gezgin, r"Opera Software\Opera Stable"),
                "vivaldi": os.path.join(yerel, r"Vivaldi\User Data")}.get(ad)
    alt = {"brave": "BraveSoftware/Brave-Browser", "chrome": "google-chrome", "chromium": "chromium",
           "edge": "microsoft-edge", "opera": "opera", "vivaldi": "vivaldi"}.get(ad)
    return alt and os.path.join(_config(), alt)


def chromium_cerezi_var(ad):
    """Bu tarayıcının çerez dosyası var mı. Yoksa yt-dlp hiç çalıştırılmaz: eski makinede her yt-dlp açılışı
    birkaç saniye, Windows'ta yedi tarayıcı sırayla denenince pencere yarım dakika bekliyordu."""
    kok = _chromium_klasoru(ad)
    if not kok or not os.path.isdir(kok):
        return False
    k = glob.escape(kok)
    return any(glob.glob(os.path.join(k, *d)) for d in (("Cookies",), ("Network", "Cookies"), ("*", "Cookies"),
                                                       ("*", "Network", "Cookies")))


def profil_kokleri():
    """yt-dlp'nin Firefox çerezlerini aradığı yerler (cookies.py, _firefox_browser_dirs)."""
    if os.environ.get("LVT_FIREFOX_PROFIL"):
        return [os.environ["LVT_FIREFOX_PROFIL"]]
    if WINDOWS:
        return [os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles"),
                os.path.expandvars(r"%LOCALAPPDATA%\Packages\Mozilla.Firefox_n80bbvh6b1yt2\LocalCache\Roaming"
                                   r"\Mozilla\Firefox\Profiles")]
    return [os.path.join(_config(), "mozilla/firefox"),                    # Firefox 147'den beri yeni kurulumlar
            os.path.expanduser("~/.mozilla/firefox"),
            os.path.expanduser("~/.var/app/org.mozilla.firefox/config/mozilla/firefox"),   # Flatpak
            os.path.expanduser("~/.var/app/org.mozilla.firefox/.mozilla/firefox"),
            os.path.expanduser("~/snap/firefox/common/.mozilla/firefox")]           # Snap


def _cerez_dosyalari():
    """Bütün Firefox profillerinin çerez dosyaları, en son kullanılan önde (-wal'ın saati de sayılır: Firefox
    açıkken ana dosya değişmiyor)."""
    dosyalar = set()
    for kok in profil_kokleri():
        k = glob.escape(kok)
        for desen in ((), ("*",), ("Profiles", "*")):
            dosyalar.update(glob.glob(os.path.join(k, *desen, "cookies.sqlite")))

    def saat(d):
        return max((os.path.getmtime(d + ek) for ek in ("", "-wal") if os.path.exists(d + ek)), default=0)
    return sorted(dosyalar, key=saat, reverse=True)


def _giris_izi(db):
    """Girişli profilde giriş çerezlerinin değerlerinden kısa bir iz (çıkıp başka hesapla girilince değişir);
    giriş yoksa None. Değerlerin kendisi hiçbir yere yazılmaz."""
    simdi = time.time()
    cerezler = dict(db.execute(
        "SELECT name, value FROM moz_cookies WHERE host = '.youtube.com' AND originAttributes NOT LIKE '%userContextId=%' "
        "AND (CASE WHEN expiry > 100000000000 THEN expiry / 1000 ELSE expiry END) > ?", (simdi,)))
    if GIRIS_CEREZI not in cerezler or not any(a in cerezler for a in SID_CEREZLERI):
        return None
    return hashlib.sha256("|".join(cerezler.get(a, "") for a in (GIRIS_CEREZI, *SID_CEREZLERI)).encode()).hexdigest()[:16]


def girisli_kopya(klasor, iz=None):
    """YouTube'a girilmiş Firefox profilinin çerezlerini klasöre kopyalar ve -wal'ı birleştirir; yt-dlp'ye
    "firefox:<klasor>" diye verilir. Girişli profil yoksa None. iz verilirse (liste) girişin izi eklenir."""
    hedef = os.path.join(klasor, "cookies.sqlite")
    for dosya in _cerez_dosyalari():
        try:
            for ek in ("", "-wal"):
                if os.path.exists(hedef + ek):
                    os.remove(hedef + ek)
                if os.path.exists(dosya + ek):
                    shutil.copyfile(dosya + ek, hedef + ek)
            db = sqlite3.connect(hedef)
            try:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                girisli = _giris_izi(db)
            finally:
                db.close()
        except (OSError, sqlite3.Error):
            continue
        if girisli:
            if iz is not None:
                iz.append(girisli)
            return klasor
    return None


def giris_izi():
    """Firefox'taki YouTube girişinin izi; giriş yoksa None."""
    iz = []
    with tempfile.TemporaryDirectory(prefix="lvt-firefox-") as k:
        girisli_kopya(k, iz)
    return iz[0] if iz else None


def giris_var():
    return giris_izi() is not None


# ---- Firefox'u bulmak, açmak, kurmak
def komut():
    """Firefox'u açan komutun başı; kurulu değilse None."""
    if os.environ.get("LVT_FIREFOX_YOK"):
        return None
    if WINDOWS:
        import winreg
        for kok in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for alt in (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe",
                        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe"):
                try:
                    yol = winreg.QueryValue(kok, alt).strip('"')
                except OSError:
                    continue
                if os.path.isfile(yol):
                    return [yol]
        for yol in (r"%ProgramFiles%\Mozilla Firefox\firefox.exe", r"%ProgramFiles(x86)%\Mozilla Firefox\firefox.exe",
                    r"%LOCALAPPDATA%\Mozilla Firefox\firefox.exe"):
            yol = os.path.expandvars(yol)
            if os.path.isfile(yol):
                return [yol]
        w = shutil.which("firefox")   # Microsoft Store'dan kurulan (WindowsApps'teki kısayol)
        return [w] if w else None
    w = shutil.which("firefox") or shutil.which("firefox-esr")
    if w:
        return [w]
    if shutil.which("flatpak") and subprocess.run(["flatpak", "info", "org.mozilla.firefox"],
                                                  capture_output=True).returncode == 0:
        return ["flatpak", "run", "org.mozilla.firefox"]
    return None


def _ayri_baslat(k):
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if WINDOWS:
        kw["creationflags"] = 0x00000008 | 0x00000200   # DETACHED, NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    subprocess.Popen(k, **kw)


def ac(adres=None):
    """Firefox'u adresle açar (açıksa yeni sekme), adres verilmezse giriş sayfası. Açılamazsa False."""
    adres = adres or giris_adresi()
    k = komut()
    if not k:
        return False
    profil = os.environ.get("LVT_FIREFOX_PROFIL")
    try:
        _ayri_baslat(k + (["-profile", profil] if profil else []) + [adres])
    except OSError:
        return False
    return True


def siteyi_ac():
    """Kurulum olmadıysa son çare: Firefox'un indirme sayfası varsayılan tarayıcıda."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    QDesktopServices.openUrl(QUrl(SITE.format(FIREFOX_DILLERI.get(kurulan_dil(), "en-US"))))


class Vazgecildi(Exception):
    pass


def _windows_turu():
    m = (os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ.get("PROCESSOR_ARCHITECTURE") or "").upper()
    return "win64-aarch64" if m == "ARM64" else "win64" if m in ("AMD64", "IA64") else "win"


def _indir(dosya, ilerleme, iptal):
    havuz = ag.havuz(retries=urllib3.Retry(total=3, backoff_factor=0.5),
                                timeout=urllib3.Timeout(connect=15, read=60))
    adres = KURULUM_ADRESI.format(_windows_turu(), FIREFOX_DILLERI.get(kurulan_dil(), "en-US"))
    r = havuz.request("GET", adres, preload_content=False)
    try:
        if r.status != 200:
            raise OSError(f"HTTP {r.status}")
        toplam = int(r.headers.get("Content-Length") or 0)
        inen = 0
        with open(dosya, "wb") as f:
            for parca in r.stream(256 * 1024):
                if iptal.is_set():
                    raise Vazgecildi()
                f.write(parca)
                inen += len(parca)
                ilerleme(inen, toplam)
    finally:
        r.release_conn()


def gunluk(satir):
    """Deneme günlüğü (LVT_FIREFOX_GUNLUK verilirse); gerçek kullanıcıda hiçbir şey yazılmaz."""
    yol = os.environ.get("LVT_FIREFOX_GUNLUK")
    if yol:
        try:
            with open(yol, "a", encoding="utf-8") as f:
                f.write(time.strftime("%H:%M:%S ") + satir + "\n")
        except OSError:
            pass


def _powershell(betik, ortam):
    """Windows PowerShell 5.1 (her Windows 10'da var). PSModulePath kalıtılmaz: PowerShell 7'den başlatılan
    programda 7'nin modül yolları 5.1'in kendi komutlarını bozabiliyor."""
    yol = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), r"System32\WindowsPowerShell\v1.0\powershell.exe")
    env = {k: v for k, v in os.environ.items() if k.upper() != "PSMODULEPATH"}
    env.update(ortam)
    return subprocess.run([yol if os.path.isfile(yol) else "powershell", "-NoProfile", "-NonInteractive",
                           "-ExecutionPolicy", "Bypass", "-Command", betik],
                          env=env, capture_output=True, text=True, timeout=1200, creationflags=_YOK)


def _imzali_mi(dosya):
    """Kurulum dosyası Mozilla'nın imzasını taşıyor mu (Windows'un kendi denetimiyle). Denetlenemezse kurulmaz."""
    try:
        r = _powershell("$s = Get-AuthenticodeSignature -LiteralPath $env:LVT_DOSYA; $s.Status; "
                        "$s.SignerCertificate.Subject", {"LVT_DOSYA": dosya})
    except (OSError, subprocess.TimeoutExpired) as e:
        gunluk(f"imza denetlenemedi: {e!r}")
        return False
    satirlar = r.stdout.strip().splitlines()
    gunluk(f"imza: {satirlar} {r.stderr.strip()[:300]}")
    return len(satirlar) >= 2 and satirlar[0].strip() == "Valid" and "O=Mozilla Corporation" in satirlar[1]


def _kur_windows(ilerleme, iptal, asama):
    dosya = os.path.join(tempfile.gettempdir(), "LiteVideoTube-Firefox-Kurulum.exe")
    try:
        try:
            _indir(dosya, ilerleme, iptal)
        except (urllib3.exceptions.HTTPError, OSError):
            return tr("Firefox indirilemedi. İnternet bağlantına bak, sonra yeniden dene.")
        asama("kuruluyor")
        if not _imzali_mi(dosya):
            return tr("İnen dosya Mozilla'nın imzasını taşımıyor, kurulmadı. Firefox'u kendi sitesinden kurabilirsin.")
        # Kurulum dosyası izinsiz başlar ("asInvoker"), yönetici izni gerekirse Windows'un izin sorusunu kendisi
        # açar ve kurulum bitene kadar bekler. /S: soru sormadan, Türkçe, varsayılan yere.
        try:
            r = subprocess.run([dosya, "/S"], timeout=1200)
            gunluk(f"kurulum bitti, çıkış {r.returncode}")
        except OSError as e:
            # Yine de "yönetici gerekli" derse (740): izin sorusunu PowerShell açar ve bitmesini bekler.
            gunluk(f"kurulum başlamadı: {e!r}; izin sorusuyla yeniden")
            try:
                _powershell("Start-Process -LiteralPath $env:LVT_DOSYA -ArgumentList '/S' -Verb RunAs -Wait",
                            {"LVT_DOSYA": dosya})
            except (OSError, subprocess.TimeoutExpired):
                pass
        except subprocess.TimeoutExpired:
            gunluk("kurulum 20 dakikada bitmedi")
    finally:
        try:
            os.remove(dosya)
        except OSError:
            pass
    if komut():
        return ""
    return tr("Firefox kurulamadı. Windows izin sorduysa ve Hayır dendiyse yeniden dene, ya da kendi sitesinden kur.")


def _linux_komutu():
    """Sistemin paket yöneticisiyle Firefox'u kuran komut (yönetici izniyle çalıştırılır)."""
    bilgi = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for satir in f:
                a, _, d = satir.strip().partition("=")
                bilgi[a] = d.strip('"').lower()
    except OSError:
        pass
    aile = bilgi.get("ID", "") + " " + bilgi.get("ID_LIKE", "")
    if shutil.which("apt-get"):
        # Debian'da paketin adı firefox-esr; Ubuntu ve türevlerinde firefox (Ubuntu'da Snap'i kuran geçiş paketi).
        paket = "firefox" if "ubuntu" in aile else "firefox-esr"
        return ["sh", "-c", f"apt-get update -q; DEBIAN_FRONTEND=noninteractive apt-get install -y {paket}"]
    if shutil.which("dnf"):
        return ["dnf", "install", "-y", "firefox"]
    if shutil.which("pacman"):
        return ["pacman", "-S", "--noconfirm", "--needed", "firefox"]
    if shutil.which("zypper"):
        return ["zypper", "--non-interactive", "install", "MozillaFirefox"]
    return None


def _kur_linux(asama):
    yonetici = os.environ.get("LVT_YONETICI") or shutil.which("pkexec")
    k = _linux_komutu()
    if not yonetici or not k:
        return tr("Bu sistemde Firefox kendiliğinden kurulamıyor. Kendi sitesinden kurabilirsin.")
    asama("kuruluyor")
    try:
        r = subprocess.run([yonetici, *k], capture_output=True, timeout=1800)
    except (OSError, subprocess.TimeoutExpired):
        return tr("Firefox kurulamadı. Kendi sitesinden kurabilirsin.")
    if komut():
        return ""
    if r.returncode in (126, 127):   # pkexec: parola sorusu kapatıldı ya da izin verilmedi
        return tr("Parola girilmediği için Firefox kurulmadı.")
    return tr("Firefox kurulamadı. Kendi sitesinden kurabilirsin.")


def kur(ilerleme, iptal, asama):
    """Firefox'u kurar. Boş yazı: kuruldu; değilse kişiye gösterilecek sebep. Vazgeçilirse Vazgecildi."""
    return _kur_windows(ilerleme, iptal, asama) if WINDOWS else _kur_linux(asama)


def internet_var():
    try:
        ag.havuz(retries=False, timeout=urllib3.Timeout(connect=6, read=6)).request(
            "HEAD", "https://www.youtube.com/generate_204")
    except (urllib3.exceptions.HTTPError, OSError):
        return False
    return True


class FirefoxYardimi(QObject):
    """Firefox penceresinin hâli (qml/FirefoxPenceresi.qml). durum: "" (kapalı), "sor", "indiriliyor", "kuruluyor",
    "bekliyor" (Firefox'ta giriş bekleniyor), "aliniyor" (giriş görüldü, abonelikler okunuyor), "bos" (Firefox'ta girilen
    hesapta abonelik yok: başka hesapla girmek önerilir), "hata"."""
    degisti = Signal()
    geldi = Signal()                 # abonelikler giriş sonrası geldi: pencere öne gelsin
    birakildi = Signal()             # kişi "Hayır" dedi ya da vazgeçti
    _ilerleme_geldi = Signal(int, int)
    _asama_geldi = Signal(str)
    _kurulum_bitti = Signal(str)
    _bakis_bitti = Signal(str)       # girişin izi; giriş yoksa boş

    def __init__(self, abonelik):
        super().__init__()
        self._abonelik = abonelik
        self._durum = ""
        self._kurulu = False
        # Firefox'u program kurdu: ilk açılışta giriş sayfasının üstünde "Firefox tarayıcısına hoş geldiniz" çıkıyor
        # (GitHub'ın Windows makinesinde, 28 Ekim); bekleme yazısı "Devam et"i söyler.
        self._yeni_kuruldu = False
        self._aciklama = ""
        self._inen = 0
        self._toplam = 0
        self._tekrar = ""          # hata hâlindeki "Yeniden dene"nin yaptığı: "kur", "giris" ya da ""
        self._iptal = threading.Event()
        self._bekleme_basi = 0.0
        self._bakiliyor = False
        # Beklenen, girişin değişmesi: aboneliği olmayan ya da geçersiz girişin izi (yoksa None, her giriş sayılır).
        self._eski_iz = None
        self._kip = "giris"        # "giris", "yeniden" (giriş geçersiz), "baska" (hesapta abonelik yok)
        self._adres = giris_adresi()
        self._saat = QTimer(self)
        self._saat.setInterval(BAKIS_ARALIGI)
        self._saat.timeout.connect(self._bak)
        self._ilerleme_geldi.connect(self._ilerleme_yaz)
        self._asama_geldi.connect(self._gec)
        self._kurulum_bitti.connect(self._kurulum_sonu)
        self._bakis_bitti.connect(self._bakis_sonu)
        abonelik.girisBulunamadi.connect(self._sor)
        abonelik.hesaptaAbonelikYok.connect(self._bos)
        abonelik.iceAlindi.connect(self._ice_alindi)

    durum = Property(str, lambda s: s._durum, notify=degisti)
    kurulu = Property(bool, lambda s: s._kurulu, notify=degisti)
    aciklama = Property(str, lambda s: s._aciklama, notify=degisti)
    inen = Property(int, lambda s: s._inen, notify=degisti)
    toplam = Property(int, lambda s: s._toplam, notify=degisti)
    tekrar = Property(str, lambda s: s._tekrar, notify=degisti)
    windows = Property(bool, lambda s: WINDOWS, constant=True)
    yeniKuruldu = Property(bool, lambda s: s._yeni_kuruldu, notify=degisti)
    kip = Property(str, lambda s: s._kip, notify=degisti)

    @Property(str, notify=degisti)
    def neden(self):
        """Windows'ta Chrome ya da Edge varsa neden onların işe yaramadığı (kişi "bende Chrome'da giriş var" der)."""
        if WINDOWS and (chromium_cerezi_var("chrome") or chromium_cerezi_var("edge")):
            return tr("Chrome ve Edge, YouTube girişini başka programlara vermiyor; Firefox veriyor.")
        return ""

    def _gec(self, durum, aciklama=None):
        self._durum = durum
        if aciklama is not None:
            self._aciklama = aciklama
        self.degisti.emit()

    def _sor(self, gecersiz=False):
        if self._durum in ("bekliyor", "aliniyor") and gecersiz:
            self._saat.stop()
            self._tekrar = "giris"
            self._eski_iz = giris_izi()
            self._kip = "yeniden"
            self._gec("hata", tr("YouTube bu Firefox girişini kabul etmiyor. Firefox'ta YouTube'dan çıkıp yeniden gir."))
            return
        if self._durum in ("bekliyor", "aliniyor"):
            # Giriş görüldü ama hiçbir tarayıcıdan liste gelmedi (giriş bu arada kapandı ya da çerez eksik).
            self._saat.stop()
            self._tekrar = "giris"
            self._gec("hata", tr("Firefox'taki YouTube girişi okunamadı. Firefox'ta YouTube'a girip yeniden dene."))
            return
        self._kurulu = komut() is not None
        self._yeni_kuruldu = False
        self._kip = "yeniden" if gecersiz else "giris"
        self._eski_iz = giris_izi() if gecersiz else None
        self._gec("sor", "")

    def _bos(self):
        """Firefox'taki hesapta abonelik yok (abonelik.py). Kişi başka hesabıyla girebilsin; elle düğmeye basınca da,
        giriş sonrası okununca da aynı pencere."""
        self._saat.stop()
        self._eski_iz = giris_izi()
        self._kip = "baska"
        self._gec("bos", "")

    @Slot()
    def baskaHesapla(self):
        self._girisi_ac(hesap_secme_adresi())

    @Slot()
    def evet(self):
        if self._kurulu:
            # Geçersiz girişte Google'ın hesap seçme sayfası: hesap orada seçilir ya da yeniden girilir.
            self._girisi_ac(hesap_secme_adresi() if self._kip == "yeniden" else giris_adresi())
        else:
            self._kur()

    @Slot()
    def hayir(self):
        """Hayır, Vazgeç, Kapat ve Esc: pencere kapanır, abonelik sayfasında yeniden denemenin yeri yazar."""
        if self._durum:
            self.vazgec()
            self.birakildi.emit()

    @Slot()
    def vazgec(self):
        self._iptal.set()
        self._saat.stop()
        self._gec("")

    @Slot()
    def yenidenDene(self):
        if self._tekrar == "kur" and not komut():
            self._kur()
        elif self._kip == "giris" and giris_var():   # giriş var, liste okunamamıştı: Firefox açılmadan yeniden okunur
            self._gec("aliniyor", "")
            self._abonelik.tarayicidanAl()
        else:
            self._girisi_ac(giris_adresi() if self._kip == "giris" else hesap_secme_adresi())

    @Slot()
    def firefoxuAc(self):
        ac(self._adres)

    @Slot()
    def siteyiAc(self):
        siteyi_ac()
        self.vazgec()

    def _kur(self):
        self._iptal = threading.Event()
        self._inen = self._toplam = 0
        self._tekrar = "kur"
        self._gec("indiriliyor" if WINDOWS else "kuruluyor", "")
        iptal = self._iptal

        def is_():
            try:
                sonuc = kur(lambda i, t: self._ilerleme_geldi.emit(i, t), iptal, self._asama_geldi.emit)
            except Vazgecildi:
                return
            if not iptal.is_set():
                self._kurulum_bitti.emit(sonuc)
        threading.Thread(target=is_, daemon=True).start()

    def _ilerleme_yaz(self, inen, toplam):
        # Her parçada değil, yüzde birlik adımlarda (QML her değişimde yeniden çizer).
        if toplam and inen < toplam and (inen - self._inen) * 100 < toplam:
            return
        self._inen, self._toplam = inen, toplam
        self.degisti.emit()

    def _kurulum_sonu(self, sonuc):
        if sonuc:
            self._gec("hata", sonuc)
        else:
            self._kurulu = self._yeni_kuruldu = True
            self._girisi_ac()

    def _girisi_ac(self, adres=None):
        adres = adres or giris_adresi()
        self._adres = adres
        if not ac(adres):
            self._tekrar = "kur"
            self._gec("hata", tr("Firefox açılamadı."))
            return
        self._tekrar = "giris"
        self._bekleme_basi = time.time()
        self._gec("bekliyor", "")
        self._saat.start()

    def _bak(self):
        if time.time() - self._bekleme_basi > BEKLEME_EN_COK:
            self._saat.stop()
            self._gec("hata", tr("Firefox'ta YouTube girişi görülmedi. Giriş yaptıysan yeniden dene."))
            return
        if self._bakiliyor:
            return
        self._bakiliyor = True
        threading.Thread(target=lambda: self._bakis_bitti.emit(giris_izi() or ""), daemon=True).start()

    def _bakis_sonu(self, iz):
        self._bakiliyor = False
        if not iz or iz == self._eski_iz or self._durum != "bekliyor":
            return
        self._saat.stop()
        self._gec("aliniyor", "")
        self._abonelik.tarayicidanAl()

    def _ice_alindi(self, eklenen, metin):
        if self._durum != "aliniyor":
            return
        if eklenen < 0:
            self._tekrar = "giris"
            self._gec("hata", metin)
        else:
            self._gec("")
            self.geldi.emit()
