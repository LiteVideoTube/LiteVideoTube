"""Çökme izi (26 Ekim). Program bir kez ekran kartının sürücüsünde (iHD_drv_video.so, Intel) çöktü: bitmiş bir
canlı yayında birkaç kez ileri atlamıştı, geride ne olduğuna dair hiçbir kayıt yoktu (çıktı /dev/null'a gidiyor).
Oynatıcının son adımları (video açma, atlama, takılma, kalite değişimi, çözücü) ve çökme anında Python'un ne yaptığı
(faulthandler) kök klasördeki iz.log'a yazılır. Dosya her açılışta son 300 satıra kısaltılır.

Windows'ta yalnız çöken iş parçacığının izi yazılır (30 Ekim, Eren'in PYTHON-5 bildirimi: "yakınlaştırınca program
kapanıp açılmıyor"). Windows'ta faulthandler yalnız ölümcül çökmede değil, yüksek biti açık her istisnada çalışır; mpv'nin
içindeki LuaJIT olağan hata işlemede 0xE24C4A02 istisnasını atıp kendisi yakalıyor. all_threads=True iken faulthandler
her seferinde öteki iş parçacıklarının Python izini de okuyordu; ana iş parçacığı o sırada Python kodu çalıştırıyorsa
(açılışta PySide içe alınırken) değişen bir çerçeveyi okuyup programı kendisi çökertiyordu (python312.dll'de erişim
ihlali, Windows Olay 1000; aynı adreste üç çökme). Yakınlık programı art arda yeniden açtığı için orada görünüyordu.
iz.log'daki "Windows fatal exception: code 0xe24c4a02" satırları bu yüzden çökme değil."""
import faulthandler
import sys
import time

from . import yoklama

_dosya = None


def baslat():
    global _dosya
    yol = yoklama.kok_klasor() / "iz.log"
    try:
        # Kodlama açıkça: Windows'ta verilmezse cp1254 yazılıyor, "açıldı" Sentry'ye giden kayıtta bozuk çıkıyordu.
        satirlar = yol.read_text(encoding="utf-8", errors="replace").splitlines()[-300:] if yol.exists() else []
        yol.write_text("".join(s + "\n" for s in satirlar), encoding="utf-8")
        _dosya = open(yol, "a", buffering=1, encoding="utf-8")   # satır satır: çökmeden önceki satır diskte olsun
        faulthandler.enable(file=_dosya, all_threads=sys.platform != "win32")
    except OSError:
        _dosya = None
    yaz("program açıldı")


def yaz(metin):
    if _dosya is None:
        return
    try:
        _dosya.write(time.strftime("%Y-%m-%d %H:%M:%S ") + metin + "\n")
    except (OSError, ValueError):
        pass
