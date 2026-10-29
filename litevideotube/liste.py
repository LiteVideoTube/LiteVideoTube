"""Oynatma listeleri ve "Sonra izle" (izleme geçmişindeki "Ana sayfaya geri koy" yerine,
YouTube'daki gibi). Listeler programın kendi kaydında durur, YouTube hesabına yazılmaz.

"Sonra izle" (numarası 1) ve "Favoriler" (numarası 0) hep vardır, silinemez. Favoriler'in numarası 0:
kişinin açtığı listeler 2'den başlar, sonradan eklenen sabit liste onlarla çakışmasın. Yeni eklenen video listenin sonuna girer; liste
baştan sona oynatılır.
"""
import json
import sqlite3
import subprocess
import sys
import threading
import time

from PySide6.QtCore import Property, QObject, Signal, Slot

from .ceviri import tr
from .cozumle import ytdlp_js, ytdlp_yolu
from .kayit import veri_klasoru

SONRA_IZLE = 1
FAVORILER = 0
SABITLER = (SONRA_IZLE, FAVORILER)


def _ad(liste_id, ad):
    """Sabit listelerin adı kayıtta Türkçe ("Sonra izle", "Favoriler"); ekranda ekran dilinde."""
    return tr("Sonra izle") if liste_id == SONRA_IZLE else tr("Favoriler") if liste_id == FAVORILER else ad


def _sure_yazi(sn):
    if not sn:
        return ""
    sn = int(sn)
    sa, dk, s = sn // 3600, sn // 60 % 60, sn % 60
    return f"{sa}:{dk:02d}:{s:02d}" if sa else f"{dk}:{s:02d}"


class Listeler(QObject):
    degisti = Signal()
    iceAlindi = Signal(int, str)     # yeni listenin numarası (-1: olmadı), açıklama
    _ice_alindi = Signal(str, str, list)   # liste adı, hata, videolar

    def __init__(self):
        super().__init__()
        self.db = sqlite3.connect(str(veri_klasoru() / "kayit.db"), timeout=10)
        self.db.execute("PRAGMA synchronous=NORMAL")   # yoklama.baglan'daki gibi
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS liste (id INTEGER PRIMARY KEY, ad TEXT, olusma REAL);
            CREATE TABLE IF NOT EXISTS liste_video (liste_id INTEGER, video_id TEXT, baslik TEXT, kanal TEXT,
                kanal_id TEXT, sure_yazi TEXT, sira REAL, PRIMARY KEY (liste_id, video_id));""")
        self.db.execute("INSERT OR IGNORE INTO liste (id, ad, olusma) VALUES (?, 'Sonra izle', ?)",
                        (SONRA_IZLE, time.time()))
        self.db.execute("INSERT OR IGNORE INTO liste (id, ad, olusma) VALUES (?, 'Favoriler', ?)",
                        (FAVORILER, time.time()))
        self.db.commit()
        self._sonra = {r[0] for r in self.db.execute("SELECT video_id FROM liste_video WHERE liste_id = ?",
                                                     (SONRA_IZLE,))}
        self._favori = {r[0] for r in self.db.execute("SELECT video_id FROM liste_video WHERE liste_id = ?",
                                                      (FAVORILER,))}
        self._s = 0
        self._ice_alindi.connect(self._ice_alindi_geldi)

    def _degisti(self):
        self._s += 1
        self._sonra = {r[0] for r in self.db.execute("SELECT video_id FROM liste_video WHERE liste_id = ?",
                                                     (SONRA_IZLE,))}
        self._favori = {r[0] for r in self.db.execute("SELECT video_id FROM liste_video WHERE liste_id = ?",
                                                      (FAVORILER,))}
        self.degisti.emit()

    # QML bağları "Sonra izle" işaretlerini yenilesin diye her değişiklikte artar.
    surum = Property(int, lambda s: s._s, notify=degisti)

    @Slot(result=list)
    def listeler(self):
        sonuc = []
        for r in self.db.execute("""SELECT l.id, l.ad, COUNT(v.video_id),
                (SELECT video_id FROM liste_video WHERE liste_id = l.id ORDER BY sira LIMIT 1)
                FROM liste l LEFT JOIN liste_video v ON v.liste_id = l.id
                GROUP BY l.id ORDER BY l.id = 1 DESC, l.id = 0 DESC, l.olusma"""):
            sonuc.append({"id": r[0], "ad": _ad(r[0], r[1]), "sayi": r[2], "sabit": r[0] in SABITLER, "favori": r[0] == FAVORILER,
                          "resim": f"https://i.ytimg.com/vi/{r[3]}/mqdefault.jpg" if r[3] else ""})
        return sonuc

    @Slot(int, result=list)
    def videolar(self, liste_id):
        return [{"id": r[0], "baslik": r[1], "kanal": r[2], "kanal_id": r[3], "sure": r[4] or "",
                 "izlenme": "", "tarih": "", "resim": f"https://i.ytimg.com/vi/{r[0]}/mqdefault.jpg"}
                for r in self.db.execute("SELECT video_id, baslik, kanal, kanal_id, sure_yazi FROM liste_video "
                                         "WHERE liste_id = ? ORDER BY sira", (liste_id,))]

    @Slot(int, result=str)
    def ad(self, liste_id):
        r = self.db.execute("SELECT ad FROM liste WHERE id = ?", (liste_id,)).fetchone()
        return _ad(liste_id, r[0]) if r else ""

    @Slot(int, "QVariantMap")
    def ekle(self, liste_id, v):
        if not v.get("id") or "://" in v["id"]:
            return
        son = self.db.execute("SELECT COALESCE(MAX(sira), 0) FROM liste_video WHERE liste_id = ?",
                              (liste_id,)).fetchone()[0]
        self.db.execute("INSERT OR IGNORE INTO liste_video VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (liste_id, v["id"], v.get("baslik") or "", v.get("kanal") or "", v.get("kanal_id"),
                         v.get("sure") or "", son + 1))
        self.db.commit()
        self._degisti()

    @Slot(int, str)
    def cikar(self, liste_id, video_id):
        self.db.execute("DELETE FROM liste_video WHERE liste_id = ? AND video_id = ?", (liste_id, video_id))
        self.db.commit()
        self._degisti()

    @Slot(int, str, result=bool)
    def icinde(self, liste_id, video_id):
        return self.db.execute("SELECT 1 FROM liste_video WHERE liste_id = ? AND video_id = ?",
                               (liste_id, video_id)).fetchone() is not None

    @Slot(str, result=bool)
    def sonradaMi(self, video_id):
        return video_id in self._sonra

    @Slot("QVariantMap")
    def sonraIzleDegistir(self, v):
        if v.get("id") in self._sonra:
            self.cikar(SONRA_IZLE, v["id"])
        else:
            self.ekle(SONRA_IZLE, v)

    # Favoriler: video sayfasındaki ve Shorts görünümündeki kalp düğmesi.
    @Slot(str, result=bool)
    def favoriMi(self, video_id):
        return video_id in self._favori

    @Slot("QVariantMap")
    def favoriDegistir(self, v):
        if v.get("id") in self._favori:
            self.cikar(FAVORILER, v["id"])
        else:
            self.ekle(FAVORILER, v)

    @Slot(str, result=int)
    def yeniListe(self, ad):
        ad = ad.strip() or tr("Yeni liste")
        k = self.db.execute("INSERT INTO liste (ad, olusma) VALUES (?, ?)", (ad, time.time()))
        self.db.commit()
        self._degisti()
        return k.lastrowid

    @Slot(int, str)
    def adDegistir(self, liste_id, ad):
        if liste_id not in SABITLER and ad.strip():
            self.db.execute("UPDATE liste SET ad = ? WHERE id = ?", (ad.strip(), liste_id))
            self.db.commit()
            self._degisti()

    @Slot(int)
    def listeSil(self, liste_id):
        if liste_id in SABITLER:
            return
        self.db.execute("DELETE FROM liste_video WHERE liste_id = ?", (liste_id,))
        self.db.execute("DELETE FROM liste WHERE id = ?", (liste_id,))
        self.db.commit()
        self._degisti()

    @Slot(int, str, int)
    def tasi(self, liste_id, video_id, yon):
        """Videoyu listede bir yukarı (-1) ya da aşağı (+1) taşır."""
        satirlar = [r[0] for r in self.db.execute("SELECT video_id FROM liste_video WHERE liste_id = ? ORDER BY sira",
                                                  (liste_id,))]
        if video_id not in satirlar:
            return
        i = satirlar.index(video_id)
        j = i + yon
        if not 0 <= j < len(satirlar):
            return
        satirlar[i], satirlar[j] = satirlar[j], satirlar[i]
        self.db.executemany("UPDATE liste_video SET sira = ? WHERE liste_id = ? AND video_id = ?",
                            [(n + 1, liste_id, vid) for n, vid in enumerate(satirlar)])
        self.db.commit()
        self._degisti()

    @Slot(str)
    def bagliListeAl(self, adres):
        """YouTube'daki bir oynatma listesinin bağlantısı (list=...): programda aynı adla yeni bir liste
        açılır, videolar sırasıyla girer. Tek yönlü bir kopya: YouTube'daki liste sonradan değişirse
        programdaki değişmez, hesaba bir şey yazılmaz. Herkese açık ve liste bağlantısıyla paylaşılmış
        listeler hesapsız okunur (yt-dlp --flat-playlist, 43 videoluk liste ~1,5 sn)."""
        def is_():
            bayrak = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            try:
                r = subprocess.run([ytdlp_yolu(), *ytdlp_js(), "--flat-playlist", "-J", "--no-warnings", adres],
                                   capture_output=True, text=True, timeout=120, creationflags=bayrak)
                d = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None
            except (OSError, subprocess.TimeoutExpired, ValueError):
                d = None
            if not d or not d.get("entries"):
                self._ice_alindi.emit("", tr("Liste okunamadı (gizli liste olabilir ya da bağlantı bozuk)."), [])
                return
            videolar = [{"id": e.get("id"), "baslik": e.get("title") or "", "kanal": e.get("channel") or e.get("uploader") or "",
                         "kanal_id": e.get("channel_id"), "sure": _sure_yazi(e.get("duration"))}
                        for e in d["entries"] if e and e.get("id") and len(e["id"]) == 11]
            self._ice_alindi.emit(d.get("title") or tr("YouTube listesi"), "", videolar)
        threading.Thread(target=is_, daemon=True).start()

    def _ice_alindi_geldi(self, ad, hata, videolar):
        if not videolar:
            self.iceAlindi.emit(-1, hata or tr("Listede video yok."))
            return
        k = self.db.execute("INSERT INTO liste (ad, olusma) VALUES (?, ?)", (ad, time.time()))
        no = k.lastrowid
        self.db.executemany("INSERT OR IGNORE INTO liste_video VALUES (?, ?, ?, ?, ?, ?, ?)",
                            [(no, v["id"], v["baslik"], v["kanal"], v["kanal_id"], v["sure"], i + 1)
                             for i, v in enumerate(videolar)])
        self.db.commit()
        self._degisti()
        self.iceAlindi.emit(no, tr("\"%1\" listesi alındı: %n video.", None, len(videolar)).replace("%1", ad))
