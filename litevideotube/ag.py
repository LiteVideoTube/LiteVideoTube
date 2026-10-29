"""Sistemin proxy ayarı (29 Ekim). YouTube'un kapalı ya da yavaşlatıldığı yerlerde (İran, Rusya) insanlar VPN
programlarını çoğu zaman "sistem proxy'si" kipinde kullanıyor (v2rayN, Hiddify): program yalnız sistemin proxy ayarını
değiştiriyor, tarayıcılar ona uyuyor. Programın bütün bağlantıları bu ayara uyar: YouTube istekleri (urllib3), video
(mpv), yt-dlp ve küçük resimler (Qt). Tam VPN (TUN) kipinde ayar yoktur, trafik zaten tünelden geçer.

Ayar program açılırken bir kez okunur: Linux'ta http_proxy / https_proxy ortam değişkenleri, Windows'ta İnternet
Seçenekleri (kayıt defteri; urllib.request.getproxies ikisini de okur). Yalnız HTTP proxy desteklenir (mpv ve ffmpeg
SOCKS bilmiyor); v2rayN ve Hiddify sistem proxy'si olarak HTTP verir. LVT_PROXY ile elle verilebilir ("yok": kapalı)."""
import os
import urllib.request

import urllib3


def _sistem():
    """Ortam değişkenleri; onlarda proxy yoksa Windows'ta İnternet Seçenekleri. urllib.request.getproxies ortamda
    yalnız no_proxy olsa da kayıt defterine bakmıyor; program kendini yeniden başlatınca (yakınlık, kişi değişimi,
    güncellemeden sonra) aşağıda koyduğumuz no_proxy yeni kopyaya geçiyor ve Windows'taki proxy kayboluyordu
    (29 Ekim, windows-guncelleme-github.yml)."""
    p = {k: v for k, v in urllib.request.getproxies_environment().items() if k != "no"}
    if not p and os.name == "nt":
        p = urllib.request.getproxies_registry()
    return p


def _bul():
    elle = os.environ.get("LVT_PROXY")
    if elle is not None:
        return "" if elle in ("", "yok") else elle
    p = _sistem()
    adres = p.get("https") or p.get("http") or ""
    if adres and "://" not in adres:
        adres = "http://" + adres
    # Windows'ta tek adresli ayar bazı Python sürümlerinde "https://adres" diye okunuyor; proxy yine düz HTTP konuşur.
    if adres.startswith("https://"):
        adres = "http://" + adres[len("https://"):]
    return adres if adres.startswith("http://") else ""


PROXY = _bul()
SEBEP = "" if PROXY else next((v for k, v in _sistem().items() if k in ("https", "http")), "")

if PROXY:
    # Programın kendi yerel sunucusu (parca_araci, 127.0.0.1) proxy'ye gitmesin; mpv'nin ffmpeg'i no_proxy'ye bakıyor.
    _haric = [h for h in (os.environ.get("no_proxy") or "").split(",") if h.strip()]
    os.environ["no_proxy"] = ",".join(_haric + [h for h in ("127.0.0.1", "localhost") if h not in _haric])


def havuz(**ayar):
    """urllib3 havuzu; sistemde proxy varsa onun üstünden (https adresleri CONNECT tüneliyle)."""
    return urllib3.ProxyManager(PROXY, **ayar) if PROXY else urllib3.PoolManager(**ayar)


_acici = urllib.request.build_opener(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY} if PROXY else {}))


def ac(istek, timeout):
    """urllib.request.urlopen yerine: proxy kararı havuz() ile aynı olsun."""
    return _acici.open(istek, timeout=timeout)


def ytdlp():
    return ["--proxy", PROXY] if PROXY else []
