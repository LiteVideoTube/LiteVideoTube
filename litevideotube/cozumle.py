"""Bir videonun oynatılabilir adreslerini yt-dlp'den alıp kalite ve ses seçeneklerine çevirir.

Neden mpv'nin kendi ytdl eklentisi değil: (1) YouTube bazı videoların adresini birkaç saniye sonra
açıyor (yt-dlp'nin available_at alanı); eklenti bunu bilmiyor, 403 alıyordu. (2) Kalite listesi
ve ses dili seçimi için bütün biçimler elimizde olmalı; kalite değişince yt-dlp yeniden çalışmaz.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

from . import ag, diller, donanim, parca_araci
from .ceviri import QT_TR_NOOP, kurulan_dil, tr

# Biçim sırası: eski ekran kartları AV1 çözemiyor (bu makinede Intel HD 620), H.264 her yerde çözülür. Ekran kartı VP9'u
# çözebiliyorsa 8 bitlik VP9 H.264'ün önüne geçer (_sira; donanim.py).
BICIM_SIRASI = {"avc1": 0, "vp09": 1, "vp9": 1, "av01": 2}
BICIM_ADI = {"avc1": "H.264", "vp09": "VP9", "vp9": "VP9", "av01": "AV1"}
VARSAYILAN_UST = 1080


def ytdlp_yolu():
    return os.environ.get("LVT_YTDL") or shutil.which("yt-dlp") or "yt-dlp"


def ytdlp_js():
    """yt-dlp'nin YouTube için istediği JavaScript çalıştırıcısı. Pakette (Windows, Linux) exe'nin yanında
    QuickJS (qjs.exe ya da qjs, 2 MB; deno 93 MB tutuyordu, çözme Node'dan ~0,3 sn yavaş, 23 Ekim). Paket dışında
    yt-dlp'nin kendi seçimi (deno, ya da kullanıcının yt-dlp ayarı). LVT_JS ile elle verilebilir.
    Her yt-dlp çağrısı bunu kullandığı için sistemin proxy'si de burada verilir (ag.py)."""
    if os.environ.get("LVT_JS"):
        return ["--js-runtimes", os.environ["LVT_JS"], *ag.ytdlp()]
    if getattr(sys, "frozen", False):
        qjs = os.path.join(os.path.dirname(sys.executable), "qjs.exe" if sys.platform == "win32" else "qjs")
        if os.path.isfile(qjs):
            return ["--js-runtimes", "quickjs:" + qjs, *ag.ytdlp()]
    return ag.ytdlp()


class CozumHatasi(Exception):
    pass


_BIRIM_SN = {"minute": 60, "hour": 3600, "day": 86400}
# YouTube'un İngilizce sebeplerinin düz Türkçesi (yt-dlp sebebi YouTube'dan İngilizce alıyor). Sıra önemli:
# ilk eşleşen kullanılır.
_SEBEPLER = [
    ("not made this video available in your country", QT_TR_NOOP("Bu video bu ülkede izlenemiyor; yükleyen engellemiş.")),
    ("confirm your age", QT_TR_NOOP("YouTube bu video için yaş doğrulaması istiyor. Tarayıcıda, hesabın açıkken izlenebilir.")),
    # Kilit internet adresine konuyor; modem yeniden bağlanınca çoğu ev hattı yeni adres alıyor (24 Ekim gecesi
    # böyle kalktı; kullanıcı uzun yazı okumaz, yalnız ne yapacağı yazar).
    ("not a bot", QT_TR_NOOP("YouTube IP adresini geçici olarak engelledi. Modemi kapatıp aç. Düzelmezse 3 dakika kapalı tutup tekrar aç.")),
    ("try again later", QT_TR_NOOP("YouTube bu bilgisayardan gelen istekleri bir süreliğine (en çok bir saat) kısıtladı. Biraz sonra yeniden dene.")),
    ("members", QT_TR_NOOP("Bu video yalnız kanalın üyelerine açık.")),
    ("private video", QT_TR_NOOP("Bu video gizli; yalnız sahibinin izin verdiği hesaplar izleyebilir.")),
    ("has been removed", QT_TR_NOOP("Bu video YouTube'dan kaldırılmış.")),
    ("unavailable", QT_TR_NOOP("Bu video artık yok ya da izlenemiyor.")),
    ("requested format is not available", QT_TR_NOOP("Bu videonun oynatılabilir bir biçimi bulunamadı.")),
]


def hata_turkce(metin):
    """yt-dlp'nin hata metnini kullanıcıya gösterilecek hâle çevirir: (başlık, açıklama, bekle_sn). Başlık yalnız
    başlamamış yayında; "Video açılamadı" yazılmaz, ekran zaten boş.
    bekle_sn: başlamamış canlı yayın ya da prömiyerde başlamasına kalan saniye (bilinmiyorsa ama yakındaysa
    60), değilse 0. Tanınmayan metin olduğu gibi açıklamaya girer."""
    k = metin.lower()
    m = re.search(r"(?:live event will begin|premieres) in (\d+) (minute|hour|day)", k)
    yakinda = "begin in a few moments" in k or "will begin shortly" in k
    if m or yakinda:
        baslik = tr("Prömiyer henüz başlamadı.") if "premiere" in k else tr("Canlı yayın henüz başlamadı.")
        if yakinda:
            return baslik, tr("Birazdan başlayacak. Başlayınca video kendiliğinden açılır."), 60
        n, birim = int(m.group(1)), m.group(2)
        sn = n * _BIRIM_SN[birim]
        saat = time.strftime("%H:%M", time.localtime(time.time() + sn))
        if sn >= 86400:
            ne_zaman = (tr("Yaklaşık %n dakika sonra başlayacak.", None, n) if birim == "minute"
                        else tr("Yaklaşık %n saat sonra başlayacak.", None, n) if birim == "hour"
                        else tr("Yaklaşık %n gün sonra başlayacak.", None, n))
        else:
            ne_zaman = (tr("Yaklaşık %n dakika sonra, saat %1 civarında başlayacak.", None, n) if birim == "minute"
                        else tr("Yaklaşık %n saat sonra, saat %1 civarında başlayacak.", None, n) if birim == "hour"
                        else tr("Yaklaşık %n gün sonra, saat %1 civarında başlayacak.", None, n)).replace("%1", saat)
        return baslik, ne_zaman + " " + tr("Program açık kalırsa başlayınca video kendiliğinden açılır."), sn
    for parca, turkce in _SEBEPLER:
        if parca in k:
            return "", tr(turkce), 0
    # Tanınmayan YouTube hatası ("[youtube] ..." İngilizce) ekrana çıkmaz, günlüğe yazılır (oynatici._hata_ver).
    if metin.startswith("["):
        return "", tr("Bu video şu an açılmıyor. Yeniden dene ya da tarayıcıda aç."), 0
    return "", metin, 0


def _sira(kod, vcodec):
    """Biçimin seçilme sırası (küçük önce)."""
    if kod in ("vp9", "vp09") and donanim.vp9 and (vcodec == "vp9" or vcodec.startswith("vp09.00")):
        return -1
    return BICIM_SIRASI.get(kod, 3)


def _bicim_kodu(vcodec):
    for k in BICIM_SIRASI:
        if (vcodec or "").startswith(k):
            return k
    return None


MWEB = ["--extractor-args", "youtube:player_client=mweb"]


def coz(video_id, dil=None, canli_ipucu=False):
    """yt-dlp -J çalıştırır, sonucu sadeleştirir. Adreslerin açılması gereken ana kadar bekler.
    Canlı yayında bir kez daha, YouTube'un telefon tarayıcısı kimliğiyle (mweb) sorar: o kimlikte
    görüntü ve ses tek akışta, liste birkaç parçalık (22 Ekim düzeninin canli.lua yolu; varsayılan
    kimlik 23 Ekim'de yalnız sessiz görüntü akışları verdi).
    canli_ipucu: listede canlı görünen video; önce doğrudan mweb'e sorulur (~2 sn kazanç). Yayın bitmişse
    (sonuç canlı değil) olağan yol."""
    adres = video_id if "://" in video_id else "https://www.youtube.com/watch?v=" + video_id
    youtube = "youtube.com" in adres
    if canli_ipucu and youtube:
        try:
            d = _ytdlp_json(adres, MWEB)
            if d.get("is_live"):
                return sadelestir(d, dil)
        except CozumHatasi:
            pass
    d = _bot_korumali(adres)
    if d.get("is_live") and youtube:
        try:
            d = _ytdlp_json(adres, MWEB)
        except CozumHatasi:
            if not d["formats"]:
                # Hızlı yol HLS listesini istemiyor; mweb de açamazsa yedek adres varsayılan kimlikten.
                try:
                    d = _ytdlp_json(adres)
                except CozumHatasi:
                    pass
    return sadelestir(d, dil)


# YouTube bu bilgisayarın adresini bir süreliğine bot sayınca ("Sign in to confirm you're not a bot") her
# video bu hatayı verir (24 Ekim akşamı: her video, yt-dlp 2026.08.19). Sitelere gömülü oynatıcının kimliği
# (web_embedded) o sırada girişsiz çalışıyordu (Sintel, 0_8J_0s6Je4: bütün kaliteler, adresler indi);
# gömülmeyi kapatmış videolarda "Video unavailable" der (Yeraltı). Bot hatası görülünce 10 dk önce o kimlik
# denenir (her videoda boşuna bir istek ve ~3 sn gitmesin), o da açamazsa varsayılan kimlik.
GOMULU = ["--extractor-args", "youtube:player_client=web_embedded"]
_bot_saati = 0.0


def kilidi_unut():
    """Kullanıcı "Yeniden dene"ye bastı: çoğu zaman modemi kapatıp açmıştır (hata mesajı bunu söylüyor), kilit
    kalkmış olabilir. Önce yine varsayılan kimlik denenir (IP değişimini dışarıya sormadan anlamanın
    yolu bu; kilit kalktıysa gömülmesi kapalı video da gecikmesiz açılır)."""
    global _bot_saati
    _bot_saati = 0.0


# Önce yalnız visionos kimliğiyle sorulur (28 Ekim). yt-dlp'nin varsayılanında adresler TV kimliğinden geliyor ve
# YouTube orada reklamın geçilebildiği ana kadar (çoğu videoda 5 sn) adresi açmıyor (available_at); visionos'ta bu
# bekleme yok, JavaScript çözmek de gerekmiyor (Node açılmıyor). 15 türlü videoda kalite, ses ve altyazı listesi
# aynıydı; tıklamadan oynatmaya ~8 sn yerine ~3 sn. HLS listesi istenmez (canlı olmayan videoda kullanılmıyor,
# ~0,4 sn; canlıda zaten mweb'e ayrıca sorulur). Oynatılır biçim gelmezse ya da hata verirse eski yol.
HIZLI = ["--extractor-args", "youtube:player_client=visionos;skip=hls"]


def _oynatilir_var(d):
    sure = d.get("duration") or 0
    return bool(d.get("is_live")) or any(f.get("vcodec") not in (None, "none") and _oynatilir(f, sure)
                                         for f in d["formats"])


def _vp9_eksik(d):
    """Yayını bitip YouTube'da henüz işlenmekte olan videoda (post_live) visionos kimliği yalnız H.264 veriyor; VP9 varsayılan
    kimlikte. Bu videolarda YouTube'un H.264 kopyası canlıyken hazırlanmış ve daha çok veriye rağmen lekeli (29 Ekim,
    SW-rQJOHDbk 1080p: H.264 5019 kbps yüzlerde lekeli, VP9 2896 kbps temiz). Ekran kartı VP9'u çözebiliyorsa
    varsayılan kimliğe de sorulur; açılış yalnız bu videolarda birkaç saniye uzar."""
    if not donanim.vp9 or d.get("live_status") != "post_live":
        return False
    sure = d.get("duration") or 0
    return not any(_bicim_kodu(f.get("vcodec")) in ("vp9", "vp09") and _oynatilir(f, sure) for f in d["formats"])


def _bot_korumali(adres):
    global _bot_saati
    if "youtube.com" not in adres:
        return _ytdlp_json(adres)
    if HIZLI:
        try:
            d = _ytdlp_json(adres, HIZLI)
            if _oynatilir_var(d):
                if _vp9_eksik(d):
                    try:
                        d2 = _ytdlp_json(adres)
                        if _oynatilir_var(d2) and not _vp9_eksik(d2):
                            return d2
                    except CozumHatasi:
                        pass
                return d
        except CozumHatasi:
            pass
    if time.time() - _bot_saati < 600:
        try:
            return _ytdlp_json(adres, GOMULU)
        except CozumHatasi:
            pass
    try:
        return _ytdlp_json(adres)
    except CozumHatasi as e:
        if "not a bot" not in str(e):
            raise
        _bot_saati = time.time()
        try:
            return _ytdlp_json(adres, GOMULU)
        except CozumHatasi:
            raise e


# yt-dlp'den yalnız kullanılan alanlar istenir (-J yerine). Yayını bitip YouTube'da henüz işlenmekte olan
# videolarda (post_live) -J her biçimin her bir saniyelik parçasının adresini yazıyor: 1,5 saatlik yayında
# 103 MB ve 23 sn; bu alanlarla aynı video 23 KB ve 3,6 sn.
_KOK_ALANLAR = "title,duration,is_live,live_status,url,http_headers,subtitles,automatic_captions"
_BICIM_ALANLARI = ("format_id,url,protocol,vcodec,acodec,height,width,fps,tbr,format_note,http_headers,"
                   "language,language_preference,abr,available_at,target_duration,container")


def _ytdlp_json(adres, ek=()):
    komut = [ytdlp_yolu(), *ytdlp_js(), "--no-warnings", "--no-playlist",
             "--print", "%(.{" + _KOK_ALANLAR + "})j", "--print", "%(formats.:.{" + _BICIM_ALANLARI + "})j",
             *ek, adres]
    bayrak = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=90, creationflags=bayrak)
    except FileNotFoundError:
        raise CozumHatasi(tr("yt-dlp bulunamadı"))
    except subprocess.TimeoutExpired:
        raise CozumHatasi(tr("yt-dlp 90 saniyede cevap vermedi"))
    if r.returncode != 0 or not r.stdout.strip():
        satir = [s for s in r.stderr.splitlines() if "ERROR" in s] or r.stderr.splitlines()[-1:] or [tr("bilinmeyen hata")]
        raise CozumHatasi(satir[0].replace("ERROR: ", "")[:300])
    satirlar = r.stdout.splitlines()
    d = json.loads(satirlar[0])
    try:
        d["formats"] = json.loads(satirlar[1])  # biçim yoksa yt-dlp "NA" yazar
    except (IndexError, ValueError):
        d["formats"] = []
    if not isinstance(d["formats"], list):
        d["formats"] = []
    return d


def _oynatilir(f, sure):
    """Tek adresten oynatılabilen biçim (http/https), ya da yayını bitip YouTube'da henüz işlenmekte olan
    videonun (post_live) parçalı biçimi. İkincisinde YouTube yalnız saniyelik parçalar veriyor (adres + "&sq=N",
    N = 0, 1, 2...; her parça kendi başına oynatılabilir mp4/webm); program bunlardan bir DASH listesi kurar
    (dash_dosyasi). Bu durum yayın bittikten sonra saatlerce sürebiliyor (27 Ekim 03:00: Ulusal Kanal'ın iki yayını
    bitişlerinden 2,5 ve 6,5 saat sonra hâlâ işleniyordu; başka kanalların akşam biten yayınları işlenmişti)."""
    if f.get("protocol") in ("https", "http"):
        return True
    return f.get("protocol") == "http_dash_segments" and bool(f.get("target_duration")) and sure > 0


def _parca_bilgisi(f):
    """Parçalı biçimde parça süresi (sn) ve kap türü; tek adresli biçimde boş."""
    if f.get("protocol") != "http_dash_segments":
        return {}
    return {"parca_sn": float(f["target_duration"]), "codecs": f.get("vcodec") if f.get("vcodec") not in (None, "none")
            else f.get("acodec"), "webm": "webm" in (f.get("container") or ""),
            "en": f.get("width") or 0, "boy": f.get("height") or 0}


def sadelestir(d, dil=None):
    dil = dil or kurulan_dil()   # ses ve altyazı sırasında kullanıcının dili başta (ekran dili)
    bicimler = d.get("formats") or []
    canli = bool(d.get("is_live"))
    sonuc = {"baslik": d.get("title") or "", "sure": d.get("duration") or 0, "canli": canli,
             "kaliteler": [], "sesler": [], "tek_adres": None, "basliklar": {}, "acilis": 0,
             "altyazilar": altyazilar(d, dil), "gecerlilik": 0}
    acilis = max([f.get("available_at") or 0 for f in bicimler] + [0])
    sonuc["acilis"] = acilis
    # Adreslerin geçerlilik sonu (adreste expire=, ~6 saat): uzun duraklatmadan sonra yeniden çözülür.
    sonlar = [int(m.group(1)) for f in bicimler for m in [re.search(r"[/&?]expire[/=](\d+)", f.get("url") or "")] if m]
    sonuc["gecerlilik"] = min(sonlar) if sonlar else 0
    if canli:
        # Canlı yayın: görüntü ve ses tek akışta olan HLS listeleri, boyuta göre (önce H.264).
        siniflar = {}
        for f in bicimler:
            if f.get("vcodec") in (None, "none") or f.get("acodec") in (None, "none") or not f.get("height"):
                continue
            if not str(f.get("protocol") or "").startswith("m3u8"):
                continue
            kod = _bicim_kodu(f.get("vcodec"))
            aday = {"yukseklik": f["height"], "fps": f.get("fps") or 0, "bicim": BICIM_ADI.get(kod, "?"),
                    "_sira": BICIM_SIRASI.get(kod, 3), "buyutulmus": False, "url": f["url"],
                    "basliklar": f.get("http_headers") or {}, "id": f.get("format_id"), "tbr": f.get("tbr") or 0}
            eski = siniflar.get(f["height"])
            if eski is None or aday["_sira"] < eski["_sira"]:
                siniflar[f["height"]] = aday
        kaliteler = sorted(siniflar.values(), key=lambda k: -k["yukseklik"])
        for k in kaliteler:
            k["ad"] = f"{k['yukseklik']}p" + (str(int(k["fps"])) if k["fps"] > 30 else "")
            k.pop("_sira")
        if kaliteler:
            sonuc["kaliteler"] = kaliteler
            sonuc["basliklar"] = kaliteler[0]["basliklar"]
            return sonuc
    if canli or not bicimler:
        # Canlı yayın ve tek dosyalı videolar: yt-dlp'nin seçtiği tek adres (ayrıntı sonraki turlarda).
        en_iyi = d.get("url") or (bicimler[-1]["url"] if bicimler else None)
        sonuc["tek_adres"] = en_iyi
        sonuc["basliklar"] = d.get("http_headers") or {}
        return sonuc

    # Görüntü: kısa kenara göre sınıf (dikey videolarda da doğru; 22 Ekim), her sınıfta en iyi biçim.
    siniflar = {}
    for f in bicimler:
        if f.get("vcodec") in (None, "none") or f.get("acodec") not in (None, "none"):
            continue
        if not _oynatilir(f, sonuc["sure"]):
            continue
        kod = _bicim_kodu(f.get("vcodec"))
        if kod is None or not f.get("width") or not f.get("height"):
            continue
        # Boyut adı YouTube'unki ("1080p"): geniş ekran filmde 1920x800 de 1080p sayılır. Not yoksa
        # kısa kenar (dikey videoda 720x1280 = 720p; 22 Ekim).
        m = re.match(r"(\d+)p", f.get("format_note") or "")
        kisa = int(m.group(1)) if m else min(f["width"], f["height"])
        buyutulmus = "upscaled" in (f.get("format_note") or "").lower() or str(f.get("format_id", "")).endswith("-sr")
        anahtar = (kisa, buyutulmus)
        aday = {"yukseklik": kisa, "fps": f.get("fps") or 0, "bicim": BICIM_ADI[kod], "_sira": _sira(kod, f.get("vcodec") or ""),
                "buyutulmus": buyutulmus, "url": f["url"], "basliklar": f.get("http_headers") or {},
                "id": f.get("format_id"), "tbr": f.get("tbr") or 0, **_parca_bilgisi(f)}
        eski = siniflar.get(anahtar)
        # Önce biçim (H.264 > VP9 > AV1), sonra kare hızı, sonra bit hızı.
        if eski is None or (aday["_sira"], -aday["fps"], -aday["tbr"]) < (eski["_sira"], -eski["fps"], -eski["tbr"]):
            siniflar[anahtar] = aday
    kaliteler = sorted(siniflar.values(), key=lambda k: (-k["yukseklik"], k["buyutulmus"]))
    for k in kaliteler:
        k["ad"] = f"{k['yukseklik']}p" + (str(int(k["fps"])) if k["fps"] > 30 else "")
        k.pop("_sira")
    sonuc["kaliteler"] = kaliteler

    # Ses: dillere göre, her dilde en yüksek bit hızlı. Özgün ses ve kullanıcının dili öne.
    diller = {}
    for f in bicimler:
        if f.get("acodec") in (None, "none") or f.get("vcodec") not in (None, "none"):
            continue
        if not _oynatilir(f, sonuc["sure"]):
            continue
        not_ = (f.get("format_note") or "").lower()
        if "drc" in not_ or "-drc" in str(f.get("format_id")):
            continue  # ses sıkıştırmalı kopyalar ayrıca listelenmez
        d_ = f.get("language") or "?"
        aday = {"dil": d_, "ozgun": "original" in not_ or (f.get("language_preference") or 0) >= 10,
                "dublaj": "dubbed" in not_, "abr": f.get("abr") or 0, "url": f["url"],
                "basliklar": f.get("http_headers") or {}, "not": f.get("format_note") or "", **_parca_bilgisi(f)}
        eski = diller.get(d_)
        if eski is None or aday["abr"] > eski["abr"]:
            diller[d_] = aday
    sesler = sorted(diller.values(), key=lambda s: (s["dil"] != dil, not s["ozgun"], s["dil"]))
    sonuc["sesler"] = sesler
    sonuc["altyazilar"] = altyazilar(d, dil)
    sonuc["basliklar"] = (kaliteler[0]["basliklar"] if kaliteler else {}) or d.get("http_headers") or {}
    if not kaliteler:
        # YouTube dışı dosya ya da yalnız birleşik biçim: yt-dlp'nin seçtiği tek adres.
        sonuc["tek_adres"] = d.get("url") or bicimler[-1].get("url")
        sonuc["sesler"] = []
    return sonuc


def _vtt_adresi(liste):
    """YouTube'un altyazı kapısından WebVTT adresi (HLS listesi olan vtt değil)."""
    for f in liste or []:
        if f.get("ext") == "vtt" and "api/timedtext" in (f.get("url") or ""):
            return f["url"]
    for f in liste or []:
        u = f.get("url") or ""
        if "api/timedtext" in u and "fmt=" in u:
            return re.sub(r"fmt=[^&]+", "fmt=vtt", u)
    return None


def altyazilar(d, dil=None):
    """Üç tür: elle yazılmışlar, otomatik (konuşmanın kendi dili,
    YouTube'da "-orig") ve makine çevirileri (adreste tlang=; YouTube girişsiz isteklere 429 veriyor).
    Her türde kullanıcının dili (ekran dili) başta, öbürleri adlarının abece sırasıyla (diller.sira_anahtari)."""
    dil = dil or kurulan_dil()

    def sirala(liste):
        return sorted(liste, key=lambda a: (a["kod"].split("-")[0] != dil, diller.sira_anahtari(a["ad"])))
    elle, otomatik, ceviri = [], [], []
    for kod, liste in (d.get("subtitles") or {}).items():
        u = _vtt_adresi(liste)
        if u and kod != "live_chat":
            elle.append({"kod": kod, "ad": diller.dil_adi(kod), "url": u, "tur": "elle"})
    for kod, liste in (d.get("automatic_captions") or {}).items():
        u = _vtt_adresi(liste)
        if not u:
            continue
        if kod.endswith("-orig"):
            k = kod[:-len("-orig")]
            otomatik.append({"kod": k, "ad": diller.dil_adi(k), "url": u, "tur": "otomatik"})
        elif "tlang=" in u:
            ceviri.append({"kod": kod, "ad": diller.dil_adi(kod), "url": u, "tur": "ceviri"})
    return {"elle": sirala(elle), "otomatik": sirala(otomatik), "ceviri": sirala(ceviri)}


def varsayilan_kalite(kaliteler, ust=VARSAYILAN_UST):
    """Üst sınırın altındaki en yüksek gerçek (büyütülmemiş) boyut; AV1 yalnız başka biçim yoksa.
    Büyütülmüş kopya yalnız gerçek boyut hiç yoksa seçilir."""
    uygun = [i for i, k in enumerate(kaliteler) if k["yukseklik"] <= ust]
    for kosul in (lambda k: not k["buyutulmus"] and k["bicim"] != "AV1",
                  lambda k: not k["buyutulmus"],
                  lambda k: True):
        for i in uygun:
            if kosul(kaliteler[i]):
                return i
    return 0 if kaliteler else -1


_dash_son = None


def dash_dosyasi(sure, video, ses=None):
    """Parçalı biçim (post_live, _oynatilir) için mpv'nin okuyacağı DASH listesini geçici bir dosyaya yazar, yolunu
    döndürür. Liste her parçanın adresini tek tek yazmaz, "$Number$" kalıbıyla kısa kalır (~3 KB). Parçalar YouTube'dan
    doğrudan değil, programın yerel aracısından (parca_araci) istenir: ffmpeg 6.1, YouTube'un önbelleğinde olmayan
    parçayı boş okuyup videoyu birkaç saniyede bitmiş sayıyordu.
    Neden dosya: mpv'nin memory:// yolundan verilen DASH listesini ffmpeg açamadı (27 Ekim). Bir önceki liste
    silinir; program kapanınca son liste de (dash_temizle). Görüntü ve ses aynı listede (ayrı ses dosyası yok)."""
    global _dash_son
    from xml.sax.saxutils import quoteattr

    def temsil(k, tur):
        ms = int(round(k["parca_sn"] * 1000))
        kalip = parca_araci.kayit(k["url"], k.get("basliklar"))
        boyut = f' width="{k["en"]}" height="{k["boy"]}"' if tur == "video" and k.get("en") else ""
        return (f'<AdaptationSet mimeType="{tur}/{"webm" if k.get("webm") else "mp4"}">'
                f'<Representation id="{tur}" bandwidth="{int((k.get("tbr") or k.get("abr") or 100) * 1000)}"'
                f' codecs={quoteattr(k.get("codecs") or "")}{boyut}>'
                f'<SegmentTemplate media={quoteattr(kalip)} startNumber="0" timescale="1000"'
                f' duration="{ms}"/></Representation></AdaptationSet>')
    parca_araci.unut()   # önceki videonun (ya da kalitenin) parçaları artık verilmez
    metin = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" type="static" profiles="urn:mpeg:dash:profile:isoff-live:2011"'
             f' mediaPresentationDuration="PT{int(sure)}S" minBufferTime="PT2S"><Period start="PT0S">'
             + temsil(video, "video") + (temsil(ses, "audio") if ses else "") + "</Period></MPD>\n")
    import tempfile
    fd, yol = tempfile.mkstemp(prefix="litevideotube-", suffix=".mpd")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(metin)
    dash_temizle()
    _dash_son = yol
    return yol


def dash_temizle():
    global _dash_son
    if _dash_son:
        try:
            os.remove(_dash_son)
        except OSError:
            pass
        _dash_son = None


def bekle(acilis):
    """YouTube'un adresi açtığı ana kadar bekler (en çok 15 sn)."""
    kalan = min(15.0, acilis - time.time() + 0.3)
    if kalan > 0:
        time.sleep(kalan)


if __name__ == "__main__":
    t = time.time()
    s = coz(sys.argv[1] if len(sys.argv) > 1 else "h7qTI6Njp9g")
    print(f"{time.time()-t:.1f} sn; açılışa {s['acilis']-time.time():.1f} sn")
    for i, k in enumerate(s["kaliteler"]):
        print(i, k["ad"], k["bicim"], "büyütülmüş" if k["buyutulmus"] else "", k["id"])
    print("varsayılan:", s["kaliteler"][varsayilan_kalite(s["kaliteler"])]["ad"] if s["kaliteler"] else None)
    for x in s["sesler"]:
        print("ses", x["dil"], x["not"], round(x["abr"]))
