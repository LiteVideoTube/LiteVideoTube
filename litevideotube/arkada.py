"""Program kapalıyken abonelik yoklaması (kişi programı açınca güncel videolarla karşılaşsın; bu
sayede içerideyken yarım saat yeter, zilli kanallar 15 dakikada bir). `litevideotube --arkada` ile başlar: pencere
ve Qt yüklenmez. Bilgisayar açılınca kendiliğinden başlar (Linux'ta ~/.config/autostart, Windows'ta kullanıcının
"Run" kaydı); program kapanınca program da başlatır. Program açıkken bekler (yoklamayı program yapar), tek kopya
çalışır, abonelik kalmazsa ya da kullanıcı kapatırsa (abonelik sayfasındaki seçenek) kendini kapatır.
"""
import os
import subprocess
import sys
import time

import urllib3

from . import youtube, yoklama
from .ceviri import tr

GUNLUK_SINIRI = 100 * 1024
# Ağ hatası (internet yok, bağlantı koptu): kanal "bakıldı" sayılmaz, bir süre beklenir. HTTP durum hataları
# (kanal silinmiş gibi) buraya girmez, yoksa o kanal her turda yeniden denenirdi.
AG_HATALARI = (urllib3.exceptions.HTTPError, OSError)


def gunluk(metin):
    try:
        yol = yoklama.veri_klasoru() / "arkada.log"
        if yol.exists() and yol.stat().st_size > GUNLUK_SINIRI:
            yol.write_text(yol.read_text(encoding="utf-8")[-GUNLUK_SINIRI // 2:], encoding="utf-8")
        with open(yol, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + metin + "\n")
    except OSError:
        pass


def _yasiyor(pid):
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _taze(deger, sure):
    """ayar değeri "<pid> <zaman>": süreç yaşıyor ve zaman yeni mi."""
    try:
        pid, ts = deger.split()
        return time.time() - float(ts) < sure and _yasiyor(int(pid))
    except (AttributeError, ValueError):
        return False


def acik_mi(db):
    """Kullanıcının seçimi (abonelik sayfası): program kapalıyken de bakılsın mı. Varsayılan evet."""
    return yoklama.ayar(db, "arkada_yoklama", "1") != "0"


def calistir():
    yol = yoklama.db_yolu()
    if not os.path.exists(yol):
        return 0
    db = yoklama.baglan(yol)
    yoklama.tablolari_kur(db)
    if _taze(yoklama.ayar(db, "arkada"), 180):
        return 0   # başka bir kopya çalışıyor
    benim = str(os.getpid())
    kisi = yoklama.secili_kisi()
    gunluk(f"başladı (süreç {benim})")
    bekle_bitis, bekle_sure, ag_sure, son_isaret, bozuk = 0.0, 600.0, 60.0, 0.0, 0
    try:
        while True:
            simdi = time.time()
            if simdi - son_isaret > 60:
                if not acik_mi(db) or not db.execute("SELECT COUNT(*) FROM kanal").fetchone()[0]:
                    gunluk("kapatıldı ya da abonelik yok; bitti")
                    break
                if all(x["id"] != kisi for x in yoklama.kisiler()["liste"]):
                    break   # bu kişi silindi (kisi.py)
                onceki = yoklama.ayar(db, "arkada", "")
                if onceki and onceki.split()[0] != benim and _taze(onceki, 180):
                    break   # aynı anda iki kopya başladıysa geç kalan çekilir
                yoklama.ayar_yaz(db, "arkada", f"{benim} {simdi}")
                son_isaret = simdi
            # Program açıkken yoklamayı program yapar; arka plan bekler.
            if _taze(yoklama.ayar(db, "program"), 150) or simdi < bekle_bitis:
                time.sleep(30)
                continue
            r = yoklama.siradaki(db, acik=False)
            if not r:
                time.sleep(30)
                continue
            kanal_id, _, onceki_bakis = r
            try:
                _, rss_saglam = yoklama.kanala_bak(kanal_id, yol)
                bozuk = 0 if rss_saglam else bozuk + 1
                bekle_sure, ag_sure = 600.0, 60.0
            except youtube.CokIstek:
                gunluk(f"YouTube çok istek dedi; {bekle_sure / 60:.0f} dk bekleniyor")
                bekle_bitis = time.time() + bekle_sure
                bekle_sure = min(bekle_sure * 2, 6 * 3600)
            except AG_HATALARI:
                yoklama.geri_al(db, kanal_id, onceki_bakis)
                bekle_bitis = time.time() + ag_sure
                ag_sure = min(ag_sure * 2, 15 * 60)
            except Exception as e:   # tek kanalın hatası yoklamayı durdurmaz
                gunluk(f"{kanal_id}: {e.__class__.__name__}: {e}")
            time.sleep(yoklama.bekleme(bozuk))   # YouTube'u yormamak için kanallar arasında
    finally:
        if (yoklama.ayar(db, "arkada", "") or "").split()[:1] == [benim]:
            yoklama.ayar_yaz(db, "arkada", "")
        db.close()
    return 0


# ---- başlatma ve bilgisayar açılınca başlama (program kullanır)

def komut():
    """Arka plan parçasını başlatan komut: paketlenmiş programda exe'nin kendisi, geliştirmede bu Python.
    AppImage'da exe, AppImage açıkken bağlanan geçici bir klasörde (/tmp/.mount_...): program kapanınca o klasör
    kalkar. Bu yüzden program kapanınca da süren kopyalar (arka plan parçası, yeniden açılış, bilgisayar açılınca
    başlama) AppImage dosyasının kendisinden başlatılır (APPIMAGE değişkeni, AppImage'ın açılış parçası verir)."""
    if getattr(sys, "frozen", False):
        return [os.environ.get("APPIMAGE") or sys.executable, "--arkada"]
    py = sys.executable
    if sys.platform == "win32" and py.lower().endswith("python.exe"):
        py = py[:-len("python.exe")] + "pythonw.exe"   # siyah pencere açılmasın
    return [py, "-m", "litevideotube", "--arkada"]


def _proje_klasoru():
    # AppImage'da geçici klasör değil (yukarıda komut()): orada çalışan süreç klasörün kalkmasını engellerdi.
    if os.environ.get("APPIMAGE") and getattr(sys, "frozen", False):
        return os.path.dirname(os.environ["APPIMAGE"])
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def baslat():
    """Program kapanırken: arka plan parçası çalışmıyorsa ayrı bir süreç olarak başlatır (program kapanınca
    da sürer)."""
    try:
        db = yoklama.baglan()
        calisiyor = _taze(yoklama.ayar(db, "arkada"), 180)
        db.close()
    except Exception:
        return
    if calisiyor:
        return
    kw = {"cwd": _proje_klasoru(), "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
          "stderr": subprocess.DEVNULL}
    if sys.platform == "win32":
        kw["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED, NEW_PROCESS_GROUP, NO_WINDOW
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(komut(), **kw)
    except OSError:
        pass


def _autostart_yolu():
    # Denemelerde (LVT_VERI) kullanıcının asıl başlangıç klasörüne yazılmaz.
    if os.environ.get("LVT_VERI"):
        return os.path.join(os.environ["LVT_VERI"], "autostart", "litevideotube-yoklama.desktop")
    kok = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(kok, "autostart", "litevideotube-yoklama.desktop")


RUN_ANAHTARI = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_ADI = "LiteVideoTube yoklama"


def _masaustu_arg(a):
    """.desktop dosyasının Exec satırı için tırnaklama (Desktop Entry belirtimi: çift tırnak, \\ " ` $ kaçar)."""
    if a and not any(c in a for c in ' \t\n"\'\\><~|&;$*?#()`'):
        return a
    return '"' + "".join("\\" + c if c in '"`$\\' else c for c in a) + '"'


def baslangica_yaz(acik):
    """Bilgisayar açılınca başlasın mı: acik ise kaydı yazar (ya da günceller), değilse siler."""
    try:
        if sys.platform == "win32":
            if os.environ.get("LVT_VERI"):
                return
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_ANAHTARI, 0, winreg.KEY_SET_VALUE) as k:
                if acik:
                    winreg.SetValueEx(k, RUN_ADI, 0, winreg.REG_SZ, subprocess.list2cmdline(komut()))
                else:
                    try:
                        winreg.DeleteValue(k, RUN_ADI)
                    except FileNotFoundError:
                        pass
            return
        yol = _autostart_yolu()
        if not acik:
            if os.path.exists(yol):
                os.remove(yol)
            return
        ortam = "env " + _masaustu_arg("LVT_VERI=" + os.environ["LVT_VERI"]) + " " if os.environ.get("LVT_VERI") else ""
        # Dosyayı yalnız program yazar (abonelik.py): ad ve açıklama ekran dilinde.
        metin = ("[Desktop Entry]\nType=Application\nName=" + tr("LiteVideoTube: yeni videolara bakar") + "\n"
                 "Comment=" + tr("Program kapalıyken aboneliklerin yeni videolarına bakar (Abonelikler sayfasında Yönet "
                                 "menüsünden kapatılır)") + "\n"
                 f"Exec={ortam}{' '.join(_masaustu_arg(a) for a in komut())}\nPath={_proje_klasoru()}\n"
                 "NoDisplay=true\nTerminal=false\nX-GNOME-Autostart-enabled=true\n")
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        if not os.path.exists(yol) or open(yol, encoding="utf-8").read() != metin:
            with open(yol, "w", encoding="utf-8") as f:
                f.write(metin)
    except OSError:
        pass
