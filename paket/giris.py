"""Paketlenmiş program için başlangıç (PyInstaller bu dosyadan exe yapar). `--arkada`: program kapalıyken
abonelik yoklaması, pencere ve Qt yüklenmez.

Velopack (otomatik güncelleme): paket Velopack ile kurulduysa `velopack.App().run()` en başta
çalışmalı; kurulum, güncelleme ve kaldırma sırasında Velopack exe'yi özel argümanlarla açar, bu çağrı onları
karşılayıp çıkar. Sıradan açılışta bir şey yapmaz. Yeni sürüme bakmak, indirmek ve "Yeni sürüm var" penceresi
programın içinde (litevideotube/guncelleme.py).

Kaldırma kancası: program kaldırılırken Windows'un "bilgisayar açılınca başla" kaydı ("LiteVideoTube yoklama",
arkada.py) silinir; yoksa kaldırılmış programı açmaya çalışan bir kayıt kalırdı. Kullanıcının kayıt klasörüne
dokunulmaz.
"""
import os
import sys
import time


def _gunluk(satir):
    yol = os.environ.get("LVT_GUNCELLEME_GUNLUK")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + satir + "\n")


def _kaldirirken(surum):
    try:
        from litevideotube import arkada
        arkada.baslangica_yaz(False)
        _gunluk(f"kaldırma kancası ({surum}): başlangıç kaydı silindi")
    except Exception as e:  # kaldırma yine sürer
        _gunluk(f"kaldırma kancası hatası: {e}")


def _velopack():
    try:
        import velopack
    except ImportError:   # Velopack'siz paket (windows-paket.yml) ya da geliştirme klasörü
        return
    t = time.perf_counter()
    app = velopack.App().on_before_uninstall_fast_callback(_kaldirirken)
    if "--arkada" in sys.argv:
        # Arka plan parçası bilgisayar açılınca da başlar; bekleyen bir güncellemeyi o sırada kurup programı
        # açmasın. Kurulum programın kendisinde ya da kapanışında olur (guncelleme.py).
        app = app.set_auto_apply_on_startup(False)
    app.run()
    _gunluk(f"App().run() {(time.perf_counter() - t) * 1000:.0f} ms, argv {sys.argv[1:]}")


if __name__ == "__main__":
    _velopack()
    if "--arkada" in sys.argv:
        from litevideotube.arkada import calistir
    else:
        from litevideotube.uygulama import calistir
    sys.exit(calistir())
