"""Otomatik güncelleme (Velopack): program açılınca arka planda yeni sürüme bakılır, varsa sessizce
indirilir, sonra "Yeni sürüm var" penceresi çıkar (qml/GuncellemePenceresi.qml):

- "Şimdi yükle": program her zamanki gibi kapanır (sekmeler, konum kaydedilir), Velopack güncellemeyi kurar ve
  programı yeni sürümle yeniden açar.
- "Sonra yükle" (ya da pencereye cevap vermeden kapatmak): güncelleme program kapanınca kurulur; bir sonraki açılış
  yeni sürümle olur. Program kapalıyken yeni videolara bakan arka plan parçası (--arkada) kurulumdan sonra yeni
  sürümle başlar.

Güncellemeler deponun GitHub Releases sayfasından gelir (KAYNAK). LVT_GUNCELLEME başka bir yer (klasör ya da adres)
verir; denemede bu makinedeki bir klasör (.github/workflows/windows-guncelleme-deneme.yml). Depo gizliyken yapılan
denemede (windows-guncelleme-github.yml) LVT_GUNCELLEME_JETON GitHub'a giriş anahtarını, LVT_GUNCELLEME_ON_SURUM=1
"ön sürüm" işaretli sürümleri de görmeyi verir; gerçek kullanıcıda ikisi de yok. Velopack yoksa (geliştirme
klasörü, Linux, Velopack'siz Windows paketi), program Velopack'le kurulmadıysa, internet yoksa ya da bakış başarısızsa
hiçbir şey olmaz: program sessizce açılmaya devam eder.

Velopack'in "kapanınca kur" çağrısı (wait_exit_then_apply_updates) programın kapanmasını yalnız 60 saniye bekliyor;
bu yüzden "Sonra yükle"de değil, program kapanırken (kapanirken) çağrılır.
"""
import os
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal, Slot

KAYNAK = "https://github.com/adeptus-vn/LiteVideoTube"


def gunluk(satir):
    """Deneme günlüğü (LVT_GUNCELLEME_GUNLUK verilirse); gerçek kullanıcıda hiçbir şey yazılmaz."""
    yol = os.environ.get("LVT_GUNCELLEME_GUNLUK")
    if yol:
        try:
            with open(yol, "a", encoding="utf-8") as f:
                f.write(time.strftime("%H:%M:%S ") + satir + "\n")
        except OSError:
            pass


class Guncelleme(QObject):
    # Yeni sürüm indirildi ve kurulmaya hazır; QML "Yeni sürüm var" penceresini açar.
    hazir = Signal(str)
    etkin = None   # programın tek Guncelleme'si; yeniden açılırken kisi.py bakar (Kisiler._yeniden_ac)

    def __init__(self, parent=None):
        super().__init__(parent)
        Guncelleme.etkin = self
        self._um = None
        self._bilgi = None        # indirilmiş, henüz kurulmamış güncelleme
        self._kuruldu = False     # kurma çağrısı yapıldı (Şimdi yükle ya da kapanırken)
        try:
            import velopack
        except ImportError:
            return
        if not getattr(sys, "frozen", False):
            return
        threading.Thread(target=self._bak, args=(velopack,), daemon=True).start()

    def _bak(self, velopack):
        kaynak = os.environ.get("LVT_GUNCELLEME") or velopack.GithubSource(
            KAYNAK, os.environ.get("LVT_GUNCELLEME_JETON") or None, os.environ.get("LVT_GUNCELLEME_ON_SURUM") == "1")
        # Velopack'in ağ kitaplığı (ureq) sistemin proxy ayarını değil yalnız HTTPS_PROXY gibi ortam değişkenlerini okur;
        # Windows'ta İnternet Seçenekleri'ndeki proxy (ag.py) ona bakış ve indirme süresince ortam değişkeniyle verilir.
        # Sonra kaldırılır: yeniden açılan program (güncellemeden sonra) eski proxy'yi miras almasın, sistemin o anki
        # ayarını okusun (29 Ekim, windows-guncelleme-github.yml; Windows'ta doğrudan çıkış kapalıyken denendi).
        from litevideotube import ag
        konan = [ad for ad in ("HTTPS_PROXY", "HTTP_PROXY") if ag.PROXY and ad not in os.environ]
        for ad in konan:
            os.environ[ad] = ag.PROXY
        try:
            self._bak_ve_indir(velopack, kaynak)
        finally:
            for ad in konan:
                os.environ.pop(ad, None)

    def _bak_ve_indir(self, velopack, kaynak):
        try:
            um = velopack.UpdateManager(kaynak)
            gunluk(f"sürüm {um.get_current_version()}, kimlik {um.get_app_id()}")
            t = time.perf_counter()
            bilgi = um.check_for_updates()
            gunluk(f"bakış {(time.perf_counter() - t) * 1000:.0f} ms: "
                   + (f"yeni sürüm {bilgi.TargetFullRelease.Version}" if bilgi else "yeni sürüm yok"))
            if not bilgi:
                return
            t = time.perf_counter()
            onceki = [-10]

            def ilerleme(yuzde):   # yalnız deneme günlüğü için, onda birlik adımlarla
                if yuzde >= onceki[0] + 10:
                    onceki[0] = yuzde
                    gunluk(f"indiriliyor %{yuzde} ({time.perf_counter() - t:.0f} sn)")
            um.download_updates(bilgi, ilerleme if os.environ.get("LVT_GUNCELLEME_GUNLUK") else None)
            gunluk(f"indirme {(time.perf_counter() - t) * 1000:.0f} ms, "
                   f"{'delta' if bilgi.BaseRelease else 'tam paket'}, {len(bilgi.DeltasToTarget)} delta")
        except Exception as e:  # internet yok, depo cevap vermedi, Velopack'le kurulmamış: program yine açılır
            gunluk(f"hata: {type(e).__name__}: {str(e).splitlines()[0] if str(e) else e!r}")
            return
        self._um, self._bilgi = um, bilgi
        self.hazir.emit(bilgi.TargetFullRelease.Version)

    def _kur(self, yeniden_ac, arguman):
        if self._bilgi is None or self._kuruldu:
            return False
        try:
            self._um.wait_exit_then_apply_updates(self._bilgi, silent=True, restart=yeniden_ac, restart_args=arguman)
        except Exception as e:
            gunluk(f"kurma hatası: {type(e).__name__}: {e}")
            return False
        self._kuruldu = True
        gunluk("kurma çağrısı yapıldı: " + ("yeniden açılacak" if not arguman else "kapanınca, arka plan " + " ".join(arguman)))
        return True

    @Slot(result=bool)
    def simdiYukle(self):
        """Velopack'e "program kapanınca kur ve yeniden aç" denir; programı QML kapatır (her zamanki kapanış)."""
        return self._kur(True, [])

    def kapanirken(self):
        """Program kapanırken: indirilmiş ama kurulmamış güncelleme varsa kapanınca kurulur ("Sonra yükle" ya da
        pencereye cevap verilmedi). Kurulumdan sonra yeni sürüm yalnız arka plan parçası olarak (--arkada) açılır;
        arka plan kapalıysa ya da abonelik yoksa o da hemen çıkar (arkada.py). True: kurulum bekliyor, arka plan
        parçasını eski sürümden başlatmaya gerek yok (Velopack kurarken onu kapatırdı)."""
        if self._kuruldu:
            return True
        return self._kur(True, ["--arkada"])
