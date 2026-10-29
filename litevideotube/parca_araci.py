"""Yayını bitip YouTube'da henüz işlenmekte olan videoların (post_live) parçalarını oynatıcıya aradan veren küçük yerel
sunucu (yalnız 127.0.0.1).

Neden: oynatıcının içindeki ffmpeg her parçayı "Range: bytes=0-" ile istiyor. YouTube'un sunucusu
önbelleğinde olmayan bir parçayı (yani o güne kadar kimsenin istemediği parçayı) boyutunu bilmeden gönderiyor:
"Content-Range: bytes 0-/*". ffmpeg 6.1 (Ubuntu 24.04'ün sürümü) buradaki "*"'ı 0 bayt sanıyor, parçayı boş okuyor,
DASH okuyucusu "Error when loading first fragment of playlist" deyip o akışı bitiriyor; oynatıcı önden inen birkaç
saniyeyi oynatıp videoyu bitmiş sayıyor. Hata her videoda çıkmıyor: önbellekteki parça boyutuyla geliyor, bazı
sunucular da Range'e hiç bakmadan düz 200 dönüyor (27 Ekim'de 1O_LubdJ2kE ve SOBp6__JVEc'de öyleydi, eski yol oynadı).
Görülen: V6URk7Lx50g (12 saat) ve 83bLAoV1elo (2 saat) birkaç saniye oynayıp durdu, bu yolla oynadı.
ffmpeg'de düzeltildi (faab9c8e56, 30 Eylül 2026), Ubuntu'nun sürümünde yok. Range'siz istekte YouTube boyutsuz da olsa
düz 200 dönüyor, ffmpeg bunu sonuna kadar okuyor; ama ffmpeg'in DASH okuyucusuna Range'i kapattırmanın yolu yok. Bu
yüzden parçaları program kendisi Range'siz ister ve oynatıcıya aktarır.

İkinci iş (28 Ekim): sıradan videoların dosyaları (tam_kayit). YouTube tek parça (Range'siz, "bytes=X-" ya da 10 MB'tan
büyük aralıklı) isteği videonun kendi hızının ~2 katına kısıyor (ycnxudvQSWI 480p: 0,41 Mbit/s; aynı adresten 10 MB'lık
parça 34 Mbit/s; visionos ve TV kimliğinde aynı). Oynatıcı dosyayı tek parça istediği için önden pay birikmiyor, en küçük
dalgalanmada takılıyor, zayıf internet kuralı da boşuna kalite düşürüyordu (kısılan hız kaliteyle birlikte düşüyor).
Aracı oynatıcının isteğini (Range'iyle, ileri sarma bozulmasın) PARCA'lık aralıklı isteklere bölüp tam hızla aktarır.

Yalnız kayıtlı adresler verilir (kayit), başka bir program bunu açık bir aracı gibi kullanamaz.
"""
import http.client
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import urllib3

from . import ag

_sunucu = None
_kilit = threading.Lock()
_kayitlar = {}   # anahtar -> (kök adres, başlıklar); yalnız açık videonun parçaları
_tamlar = {}     # anahtar -> (adres, başlıklar, boyut); açık videonun görüntü ve ses dosyası
PARCA = 8 * 1024 * 1024   # YouTube'un kısmadığı en büyük aralık 10 MB'ın biraz altı
_havuz = ag.havuz(timeout=urllib3.Timeout(connect=10, read=20), retries=urllib3.Retry(total=2, redirect=5))


class _Isleyici(BaseHTTPRequestHandler):
    # Boyut bilinmiyorsa parça "chunked" gönderilir: ffmpeg 6.1 boyutsuz ve chunked olmayan cevabın sonunu
    # "Stream ends prematurely" diye hata sayıyor.
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        parcalar = self.path.strip("/").split("/")
        if len(parcalar) == 2 and parcalar[1] == "tam":
            tam = _tamlar.get(parcalar[0])
            if tam is None:
                self.send_error(404)
            else:
                self._tam(*tam)
            self.close_connection = True
            return
        kayit = _kayitlar.get(parcalar[0]) if len(parcalar) == 2 else None
        if kayit is None or not parcalar[1].isdigit():
            self.send_error(404)
            return
        adres, basliklar = kayit
        istek = urllib.request.Request(adres + "&sq=" + parcalar[1], headers=basliklar)
        try:
            cevap = ag.ac(istek, timeout=20)
        except urllib.error.HTTPError as e:
            self.send_error(e.code)
            return
        except OSError:
            self.send_error(502)
            return
        boyut = cevap.headers.get("Content-Length")
        with cevap:
            self.send_response(200)
            self.send_header("Content-Type", cevap.headers.get("Content-Type") or "application/octet-stream")
            self.send_header("Content-Length" if boyut else "Transfer-Encoding", boyut or "chunked")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                while True:
                    blok = cevap.read1(65536)
                    if boyut:
                        self.wfile.write(blok)
                    elif blok:
                        self.wfile.write(b"%x\r\n%s\r\n" % (len(blok), blok))
                    else:
                        self.wfile.write(b"0\r\n\r\n")
                    if not blok:
                        break
            except (OSError, http.client.HTTPException):
                pass   # oynatıcı parçayı yarıda bıraktı (atlama, video değişti) ya da YouTube kesti
        self.close_connection = True

    def _parca_iste(self, adres, basliklar, bas, son):
        return _havuz.request("GET", adres, headers={**basliklar, "Range": f"bytes={bas}-{son}"},
                              preload_content=False)

    def _tam(self, adres, basliklar, boyut):
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range") or "")
        bas = int(m.group(1)) if m and m.group(1) else 0
        son = int(m.group(2)) if m and m.group(2) else boyut - 1
        son = min(son, boyut - 1)
        if bas > son:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{boyut}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        # İlk parça başlıklardan önce istenir: YouTube hata verirse (süresi dolmuş adres, 403) oynatıcıya aynı hata gider.
        try:
            cevap = self._parca_iste(adres, basliklar, bas, min(bas + PARCA - 1, son))
        except (urllib3.exceptions.HTTPError, OSError):
            self.send_error(502)
            return
        if cevap.status not in (200, 206):
            self.send_error(cevap.status)
            cevap.release_conn()
            return
        self.send_response(206 if m else 200)
        self.send_header("Content-Type", cevap.headers.get("Content-Type") or "application/octet-stream")
        self.send_header("Content-Length", str(son - bas + 1))
        self.send_header("Accept-Ranges", "bytes")
        if m:
            self.send_header("Content-Range", f"bytes {bas}-{son}/{boyut}")
        self.send_header("Connection", "close")
        self.end_headers()
        konum = bas
        while True:
            try:
                for blok in cevap.stream(65536):
                    self.wfile.write(blok)
                    konum += len(blok)
            except (ConnectionError, BrokenPipeError):
                cevap.release_conn()
                return   # oynatıcı bıraktı (atlama, video değişti)
            except (urllib3.exceptions.HTTPError, OSError):
                pass     # YouTube parçayı yarıda kesti: kalan yer yeniden istenir
            cevap.release_conn()
            if konum > son:
                return
            for deneme in range(3):
                try:
                    cevap = self._parca_iste(adres, basliklar, konum, min(konum + PARCA - 1, son))
                    if cevap.status in (200, 206):
                        break
                    cevap.release_conn()
                except (urllib3.exceptions.HTTPError, OSError):
                    pass
                time.sleep(1 + deneme)
            else:
                return   # bağlantı kesilir; oynatıcı yeniden bağlanır (reconnect), olmazsa dosya hatası

    def log_message(self, *_):
        pass


def kayit(adres, basliklar):
    """Parçalı bir biçimin kök adresini kaydeder, oynatıcıya verilecek kalıbı döndürür ("$Number$" parça numarası)."""
    global _sunucu
    with _kilit:
        _baslat()
        anahtar = secrets.token_urlsafe(12)
        _kayitlar[anahtar] = (adres, {a: b for a, b in (basliklar or {}).items() if a.lower() != "range"})
        return f"http://127.0.0.1:{_sunucu.server_address[1]}/{anahtar}/$Number$"


def _baslat():
    global _sunucu
    if _sunucu is None:
        _sunucu = ThreadingHTTPServer(("127.0.0.1", 0), _Isleyici)
        _sunucu.daemon_threads = True
        threading.Thread(target=_sunucu.serve_forever, daemon=True).start()


def tam_kayit(adres, basliklar):
    """YouTube'un video ya da ses dosyasının adresini aracıdan verilecek adrese çevirir. Boyutu adreste yazmayanlar
    (canlı yayın listesi, YouTube dışı adres) olduğu gibi döner."""
    if not adres or "googlevideo.com" not in adres:
        return adres
    m = re.search(r"[?&]clen=(\d+)", adres)
    if not m:
        return adres
    with _kilit:
        _baslat()
        anahtar = secrets.token_urlsafe(12)
        _tamlar[anahtar] = (adres, {a: b for a, b in (basliklar or {}).items() if a.lower() != "range"}, int(m.group(1)))
        return f"http://127.0.0.1:{_sunucu.server_address[1]}/{anahtar}/tam"


def tam_unut():
    """Önceki videonun (ya da kalitenin) dosyaları artık verilmez."""
    with _kilit:
        _tamlar.clear()


def unut():
    """Önceki videonun (ya da kalitenin) kayıtları silinir; yalnız açık olanınkiler kalır."""
    with _kilit:
        _kayitlar.clear()


def durdur():
    global _sunucu
    with _kilit:
        _kayitlar.clear()
        _tamlar.clear()
        if _sunucu is not None:
            _sunucu.shutdown()
            _sunucu.server_close()
            _sunucu = None
