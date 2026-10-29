"""Arka plan yoklamasını (litevideotube --arkada) sınamak için yardımcı; Windows iş akışı ve elle deneme kullanır.
Kayıt klasörü LVT_VERI'den (kullanıcının asıl kaydına dokunulmaz).

  python araclar/arkada_sinama.py hazirla     # tek kanallık (Blender) deneme kaydı
  python araclar/arkada_sinama.py sifirla     # kanalın bakış zamanını ve "program açık" işaretini sıfırlar
  python araclar/arkada_sinama.py denetle     # kanala bakıldı mı, video geldi mi; bakılmadıysa çıkış kodu 1
  python araclar/arkada_sinama.py baslangic   # Windows'ta başlangıç kaydını (HKCU Run) yazıp siler; yalnız sınama makinesinde
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from litevideotube import arkada, yoklama  # noqa: E402

KANAL = ("UCSMOQeBJ2RAnuFungnQOxLg", "Blender")


def main(is_):
    if is_ == "baslangic":
        # Kullanıcının asıl başlangıç kaydına yazar: yalnız tek kullanımlık sınama makinesinde (Windows Actions).
        if sys.platform != "win32":
            print("yalnız Windows sınama makinesinde çalışır")
            return 0
        os.environ.pop("LVT_VERI", None)
        arkada.baslangica_yaz(True)
        print("yazıldı:", _oku())
        arkada.baslangica_yaz(False)
        print("silindi, kalan:", _oku())
        return 0
    os.makedirs(yoklama.veri_klasoru(), exist_ok=True)
    db = yoklama.baglan()
    yoklama.tablolari_kur(db)
    if is_ == "hazirla":
        db.execute("INSERT OR IGNORE INTO kanal (id, ad) VALUES (?, ?)", KANAL)
        db.commit()
    elif is_ == "sifirla":
        db.execute("UPDATE kanal SET son_bakis = 0")
        db.commit()
        yoklama.ayar_yaz(db, "program", "")
    elif is_ == "denetle":
        son = db.execute("SELECT son_bakis FROM kanal WHERE id = ?", (KANAL[0],)).fetchone()[0]
        n = db.execute("SELECT COUNT(*) FROM abone_video").fetchone()[0]
        print(f"son bakış: {time.time() - son:.0f} sn önce" if son else "son bakış: hiç", f"| video: {n}",
              "| arkada:", yoklama.ayar(db, "arkada"), "| program:", yoklama.ayar(db, "program"))
        gunluk_yolu = yoklama.veri_klasoru() / "arkada.log"
        if gunluk_yolu.exists():
            print(gunluk_yolu.read_text(encoding="utf-8"))
        return 0 if son else 1
    return 0


def _oku():
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, arkada.RUN_ANAHTARI) as k:
                return winreg.QueryValueEx(k, arkada.RUN_ADI)[0]
        except FileNotFoundError:
            return None
    yol = arkada._autostart_yolu()
    return open(yol, encoding="utf-8").read() if os.path.exists(yol) else None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
