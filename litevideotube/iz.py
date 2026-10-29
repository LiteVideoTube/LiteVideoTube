"""Çökme izi (26 Ekim). Program bir kez ekran kartının sürücüsünde (iHD_drv_video.so, Intel) çöktü: bitmiş bir
canlı yayında birkaç kez ileri atlamıştı, geride ne olduğuna dair hiçbir kayıt yoktu (çıktı /dev/null'a gidiyor).
Oynatıcının son adımları (video açma, atlama, takılma, kalite değişimi, çözücü) ve çökme anında Python'un ne yaptığı
(faulthandler) kök klasördeki iz.log'a yazılır. Dosya her açılışta son 300 satıra kısaltılır."""
import faulthandler
import time

from . import yoklama

_dosya = None


def baslat():
    global _dosya
    yol = yoklama.kok_klasor() / "iz.log"
    try:
        satirlar = yol.read_text(errors="replace").splitlines()[-300:] if yol.exists() else []
        yol.write_text("".join(s + "\n" for s in satirlar))
        _dosya = open(yol, "a", buffering=1)   # satır satır: çökmeden önceki satır diskte olsun
        faulthandler.enable(file=_dosya, all_threads=True)
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
