"""YouTube'dan sayfa verisi almak (arama, video sayfası). Tarayıcı kullanılmaz.

YouTube'un kendi veri kapıları (youtubei/v1) okunur; alanlar eksik gelebilir, hepsi güvenle okunur.
Video adresleri burada değil,
her zaman yt-dlp'den (mpv'nin ytdl kancası) alınır.
"""
import base64
import json
import re
import time
import urllib.parse

import urllib3

from . import ag, ceviri
from .ceviri import QT_TR_NOOP, tr


# Sayfa isteklerine güncel bir tarayıcı adıyla gidilir (karar notu, 3. ilke).
TARAYICI = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
WEB_SURUM = "2.20261020.01.00"
# Kanal listelerine (RSS) programın kendi adıyla gidilir (3. ilke); kod yayımlanınca proje adresi eklenecek.
PROGRAM_ADI = "LiteVideoTube/0.1"

# YouTube boşta kalan bağlantıyı kapatabiliyor; POST'lar da yeniden denenir (22 Ekim dersi).
_havuz = ag.havuz(
    retries=urllib3.Retry(total=3, backoff_factor=0.3, allowed_methods=None,
                          status_forcelist=(500, 502, 503, 504)),
    timeout=urllib3.Timeout(connect=10, read=20),
    # Sıkıştırma istenir: kanal sayfası gzip'le 41 KB, istenmezse ~10 katı (23 Ekim).
    headers={"User-Agent": TARAYICI, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5", "Accept-Encoding": "gzip"},
)


class YouTubeHatasi(Exception):
    pass


def _getir(adres, govde=None):
    if govde is None:
        r = _havuz.request("GET", adres)
    else:
        istemci = _al(govde, "context", "client", vars={})
        dil, ulke = istemci.get("hl", "tr"), istemci.get("gl", "TR")
        r = _havuz.request("POST", adres, body=json.dumps(govde).encode(),
                           headers={"Content-Type": "application/json", "User-Agent": TARAYICI,
                                    "Accept-Encoding": "gzip", "Accept-Language": f"{dil}-{ulke},{dil};q=0.9,en;q=0.5"})
    if r.status != 200:
        raise YouTubeHatasi(tr("YouTube %1 döndü").replace("%1", str(r.status)))
    return r.data


# Abonelik yoklamasının yolu (kanal sekmeleri, yüklemeler listesi) hep Türkçe ve Türkiye: yoklama.py ve abonelik.py
# YouTube'un Türkçe yazısını çözümlüyor ("18 saat önce yayınlandı", "… tarihi için planlandı"), arka plan yoklaması
# (Qt'siz) da aynı yoldan geçiyor. Ekrana giden istekler (arama, video sayfası, öneriler, yorumlar, kanal sayfası,
# gündem) programın diliyle ve ülkesiyle (ceviri.kurulan_dil, ceviri.ulke; 29 Ekim).
YOKLAMA_DILI = ("tr", "TR")


def _baglam(dil=None, ulke=None):
    dil, ulke = dil or ceviri.kurulan_dil(), ulke or ceviri.ulke()
    # Saat farkı verilmezse YouTube "… tarihi için planlandı" saatlerini ABD Pasifik saatiyle yazıyor (26 Ekim:
    # 18:00'deki yayın "08:00" görünüyordu). Bilgisayarın saat farkı yetiyor, dilim adı gerekmiyor.
    return {"client": {"clientName": "WEB", "clientVersion": WEB_SURUM, "hl": dil, "gl": ulke,
                       "utcOffsetMinutes": time.localtime().tm_gmtoff // 60}}


def _al(d, *yol, vars=None):
    """İç içe sözlük/listede yol boyunca güvenle iner; bir adım yoksa vars döner.
    YouTube alanları sık değişiyor ve bazen eksik geliyor; hiçbir eksik alan programı düşürmemeli."""
    for adim in yol:
        try:
            d = d[adim]
        except (KeyError, IndexError, TypeError):
            return vars
    return d


def _yazi(d):
    """YouTube'un yazı alanları: {'simpleText': ...}, {'runs': [...]} ya da {'content': ...}."""
    if not isinstance(d, dict):
        return d if isinstance(d, str) else ""
    if "simpleText" in d:
        return d["simpleText"]
    if "runs" in d:
        return "".join(r.get("text", "") for r in d["runs"])
    return d.get("content", "")


def _video(r):
    """Bir arama sonucu ya da öneri; video değilse None. Eski (videoRenderer) ve yeni
    (lockupViewModel) biçimin ikisi de okunur."""
    if "videoRenderer" in r or "compactVideoRenderer" in r:
        v = r.get("videoRenderer") or r.get("compactVideoRenderer")
        vid = v.get("videoId")
        sahip = v.get("ownerText") or v.get("longBylineText") or v.get("shortBylineText") or {}
        rozet = [_al(b, "metadataBadgeRenderer", "style") for b in v.get("badges", [])]
        sure = _yazi(v.get("lengthText"))
        canli = "BADGE_STYLE_TYPE_LIVE_NOW" in rozet or (not sure and bool(v.get("viewCountText", {}).get("runs")))
        kresim = _al(v, "channelThumbnailSupportedRenderers", "channelThumbnailWithLinkRenderer", "thumbnail",
                     "thumbnails", vars=[]) or _al(v, "channelThumbnail", "thumbnails", vars=[])
        return {"id": vid, "baslik": _yazi(v.get("title")), "kanal": _yazi(sahip),
                "kanal_id": _al(sahip, "runs", 0, "navigationEndpoint", "browseEndpoint", "browseId"),
                "kanal_resim": (kresim[-1].get("url") if kresim else "") or "",
                "sure": sure, "izlenme": _yazi(v.get("shortViewCountText")) or _yazi(v.get("viewCountText")),
                "tarih": _yazi(v.get("publishedTimeText")), "canli": canli,
                "resim": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"} if vid else None
    if "lockupViewModel" in r:
        v = r["lockupViewModel"]
        if v.get("contentType") not in (None, "LOCKUP_CONTENT_TYPE_VIDEO"):
            return None
        vid = v.get("contentId")
        meta = _al(v, "metadata", "lockupMetadataViewModel", vars={})
        satirlar = _al(meta, "metadata", "contentMetadataViewModel", "metadataRows", vars=[])
        parcalar = [[_al(p, "text", "content", vars="") for p in s.get("metadataParts", [])] for s in satirlar]
        parcalar = [s for s in ([x for x in satir if x] for satir in parcalar) if s]   # boş ayraç satırları atılır
        sure, rozet = "", ""
        for o in _al(v, "contentImage", "thumbnailViewModel", "overlays", vars=[]):
            for b in _al(o, "thumbnailBottomOverlayViewModel", "badges", vars=[]):
                sure = _al(b, "thumbnailBadgeViewModel", "text", vars=sure)
                rozet = _al(b, "thumbnailBadgeViewModel", "badgeStyle", vars=rozet)
        canli = rozet == "THUMBNAIL_OVERLAY_BADGE_STYLE_LIVE" or sure.upper() in ("CANLI", "LIVE")
        # Satırlar yerine göre ayrılır (29 Ekim; önceden yazının içindeki sözcüğe bakılıyordu, yalnız Türkçe ve
        # İngilizcede tutuyordu, YouTube artık programın diliyle yazıyor): öneride ilk satır kanal adı, ikincisi
        # izlenme ve tarih; kanal sayfasında yalnız izlenme ve tarih. Canlıda tek parça izleyici sayısı. Tek parçalı
        # başka satırda sözcüğe bakılır, tutmazsa tarih sayılır (kartta ikisi yan yana yazıldığı için fark görünmez).
        kanal = parcalar[0][0] if len(parcalar) > 1 else ""
        son = parcalar[1] if len(parcalar) > 1 else parcalar[0] if parcalar else []
        if len(son) > 1:
            ikinci = son[:2]
        elif son and (canli or _izlenme_mi(son[0])):
            ikinci = [son[0], ""]
        else:
            ikinci = ["", son[0] if son else ""]
        kanal_id = _al(meta, "image", "decoratedAvatarViewModel", "rendererContext", "commandContext",
                       "onTap", "innertubeCommand", "browseEndpoint", "browseId")
        kresim = _al(meta, "image", "decoratedAvatarViewModel", "avatar", "avatarViewModel", "image", "sources", vars=[])
        return {"id": vid, "baslik": _al(meta, "title", "content", vars=""), "kanal": kanal,
                "kanal_id": kanal_id, "kanal_resim": (kresim[-1].get("url") if kresim else "") or "",
                "sure": "" if canli else sure,
                "izlenme": ikinci[0] if ikinci else "", "tarih": ikinci[1] if len(ikinci) > 1 else "",
                "canli": canli, "resim": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"} if vid else None
    if "shortsLockupViewModel" in r:
        # Kanalın Shorts sekmesindeki dikey kart: başlık ve izlenme kartın üstünde yazar; kanal ve tarih yok.
        v = r["shortsLockupViewModel"]
        vid = _al(v, "onTap", "innertubeCommand", "reelWatchEndpoint", "videoId")
        return {"id": vid, "baslik": _al(v, "overlayMetadata", "primaryText", "content", vars=""), "kanal": "",
                "kanal_id": None, "sure": "", "izlenme": _al(v, "overlayMetadata", "secondaryText", "content", vars=""),
                "tarih": "", "canli": False, "shorts": True, "resim": shorts_resmi(vid)} if vid else None
    return None


def shorts_resmi(vid):
    """Shorts'un dikey küçük resmi (oar2: ~135 KB; oardefault üç katı büyük)."""
    return f"https://i.ytimg.com/vi/{vid}/oar2.jpg"


def _izlenme_mi(x):
    # Yalnız tek parçalı satırda (_video): Türkçe ve İngilizce sözcükler; başka dilde tutmazsa tarih sayılır.
    # Önerilerde izlenme kelimesiz gelebiliyor ("1,3 Mn", "62K"; 20 Ekim).
    if re.match(r"^\d[\d.,]*\s*(B|Mn|Mr|K|M|bin)?$", x.replace("\xa0", " ").strip()):
        return True
    x = x.lower()
    return any(k in x for k in ("görüntüleme", "izlenme", "views", "izleyen", "watching", "bekliyor"))


def _videolar_ve_devam(ogeler):
    videolar, devam = [], None
    for r in ogeler:
        if "richItemRenderer" in r:
            r = _al(r, "richItemRenderer", "content", vars={})
        if "itemSectionRenderer" in r:
            alt, d = _videolar_ve_devam(_al(r, "itemSectionRenderer", "contents", vars=[]))
            videolar += alt
            devam = devam or d
        elif "continuationItemRenderer" in r:
            devam = _al(r, "continuationItemRenderer", "continuationEndpoint", "continuationCommand", "token")
        else:
            v = _video(r)
            if v:
                videolar.append(v)
    return videolar, devam


def ara(sorgu, devam=None):
    """Arama sonuçları: {'videolar': [...], 'devam': sonraki sayfanın anahtarı ya da None}."""
    govde = {"context": _baglam()}
    if devam:
        govde["continuation"] = devam
    else:
        govde["query"] = sorgu
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/search?prettyPrint=false", govde))
    if devam:
        ham = []
        for k in veri.get("onResponseReceivedCommands", []):
            ham += _al(k, "appendContinuationItemsAction", "continuationItems", vars=[])
    else:
        ham = _al(veri, "contents", "twoColumnSearchResultsRenderer", "primaryContents",
                  "sectionListRenderer", "contents", vars=[])
    videolar, sonraki = _videolar_ve_devam(ham)
    return {"videolar": videolar, "devam": sonraki}


def video_sayfasi(video_id):
    """Başlık, kanal, açıklama ve ilk öneriler (tek istek, youtubei/v1/next)."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/next?prettyPrint=false",
                             {"context": _baglam(), "videoId": video_id}))
    ana = _al(veri, "contents", "twoColumnWatchNextResults", vars={})
    birincil, ikincil = {}, {}
    for c in _al(ana, "results", "results", "contents", vars=[]):
        birincil = c.get("videoPrimaryInfoRenderer", birincil)
        ikincil = c.get("videoSecondaryInfoRenderer", ikincil)
    sahip = _al(ikincil, "owner", "videoOwnerRenderer", vars={})
    oneriler, devam = _videolar_ve_devam(_al(ana, "secondaryResults", "secondaryResults", "results", vars=[]))
    # Yorumlar sayfayla gelmez; yorum bölümünde yalnız ilk partinin anahtarı var (yorumlar() ile istenir).
    # Bölümde anahtar yerine bir mesaj varsa ("Yorumlar kapalı") o gösterilir.
    yorum_devam, yorum_mesaji = None, ""
    for c in _al(ana, "results", "results", "contents", vars=[]):
        bolum = c.get("itemSectionRenderer") or {}
        if bolum.get("sectionIdentifier") != "comment-item-section":
            continue
        for x in bolum.get("contents", []):
            yorum_devam = yorum_devam or _al(x, "continuationItemRenderer", "continuationEndpoint",
                                             "continuationCommand", "token")
            if "messageRenderer" in x:
                # Mesajın ilk parçası ("Yorumlar kapalı."); ardından gelen "Daha fazla bilgi" bir bağlantı.
                yorum_mesaji = _al(x, "messageRenderer", "text", "runs", 0, "text", vars="") \
                    or _yazi(_al(x, "messageRenderer", "text")) or tr("Yorumlar kapalı.")
    if not yorum_devam and not yorum_mesaji:
        yorum_mesaji = tr("Bu videonun yorumları gelmedi.")
    return {
        "id": video_id,
        "baslik": _yazi(birincil.get("title")),
        "kanal": _yazi(sahip.get("title")),
        "kanal_id": _al(sahip, "navigationEndpoint", "browseEndpoint", "browseId"),
        "abone": _yazi(sahip.get("subscriberCountText")),
        "kanal_resim": (_al(sahip, "thumbnail", "thumbnails", vars=[]) or [{}])[-1].get("url") or "",
        "izlenme": _yazi(_al(birincil, "viewCount", "videoViewCountRenderer", "viewCount")),
        "tarih": _yazi(birincil.get("dateText")),
        "aciklama": _al(ikincil, "attributedDescription", "content", vars="") or _yazi(ikincil.get("description")),
        "oneriler": oneriler,
        "oneri_devam": devam,
        "yorum_devam": yorum_devam,
        "yorum_mesaji": yorum_mesaji,
    }


def _html(x):
    return x.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _yorum_metni(icerik, video_id):
    """Yorumun metni Qt'nin StyledText'i olarak (HTML'nin küçük bir parçası) ve düz hâli. Bağlantılar: bu videonun
    bir anı 't:<sn>', başka video 'v:<id>' ya da 'v:<id>:<sn>', kanal 'c:<id>', dış adres olduğu gibi.
    YouTube yerleri UTF-16 birimiyle sayıyor (emoji iki birim), dilimler ona göre alınır."""
    metin = icerik.get("content", "") or ""
    u = metin.encode("utf-16-le")
    uzunluk = len(u) // 2

    def parca(a, b):
        return u[2 * a:2 * b].decode("utf-16-le", "replace")
    kosular = sorted((k for k in icerik.get("commandRuns", []) if "startIndex" in k), key=lambda k: k["startIndex"])
    cikti, yer = [], 0
    for k in kosular:
        a, n = k["startIndex"], k.get("length", 0)
        if a < yer:
            continue
        cikti.append(_html(parca(yer, a)))
        komut = _al(k, "onTap", "innertubeCommand", vars={})
        hedef = ""
        if "watchEndpoint" in komut:
            w = komut["watchEndpoint"]
            sn = w.get("startTimeSeconds")
            if w.get("videoId") == video_id and sn is not None:
                hedef = f"t:{sn}"
            elif w.get("videoId"):
                hedef = f"v:{w['videoId']}" + (f":{sn}" if sn else "")
        elif str(_al(komut, "browseEndpoint", "browseId", vars="")).startswith("UC"):
            hedef = "c:" + komut["browseEndpoint"]["browseId"]
        elif "urlEndpoint" in komut:
            hedef = komut["urlEndpoint"].get("url", "")
            q = urllib.parse.urlparse(hedef)
            if q.path == "/redirect":   # youtube.com/redirect?q=<asıl adres>
                hedef = urllib.parse.parse_qs(q.query).get("q", [hedef])[0]
        yazi = _html(parca(a, a + n))
        cikti.append(f'<a href="{_html(hedef)}">{yazi}</a>' if hedef else yazi)
        yer = a + n
    cikti.append(_html(parca(yer, uzunluk)))
    return "".join(cikti).replace("\n", "<br>"), metin


def _yorum(cvm, varliklar, video_id):
    """YouTube'un yeni yorum biçimi: commentViewModel yalnız anahtar taşır, içerik 'frameworkUpdates'teki
    varlıklarda (commentEntityPayload, engagementToolbarStateEntityPayload)."""
    v = _al(varliklar.get(cvm.get("commentKey"), {}), "commentEntityPayload", vars={})
    if not v:
        return None
    oz, yazar, arac = v.get("properties", {}), v.get("author", {}), v.get("toolbar", {})
    durum = _al(varliklar.get(cvm.get("toolbarStateKey"), {}), "engagementToolbarStateEntityPayload", vars={})
    html, duz = _yorum_metni(oz.get("content", {}), video_id)
    # 40 piksellik daire: Google'ın resim sunucusu yuvarlak kesip saydam köşeli PNG veriyor ("=s48-cc", ~5 KB);
    # arayüzde maske efekti (her resme ayrı çizim yüzeyi) gerekmiyor.
    resim = re.sub(r"=s\d+-.*$", "=s48-cc", yazar.get("avatarThumbnailUrl", "") or "")
    return {"id": oz.get("commentId") or cvm.get("commentId", ""), "metin": html,
            "yazar": yazar.get("displayName", ""), "yazar_id": yazar.get("channelId", ""), "resim": resim,
            "dogrulanmis": bool(yazar.get("isVerified")), "sahip": bool(yazar.get("isCreator")),
            "tarih": oz.get("publishedTime", ""), "begeni": arac.get("likeCountNotliked", "") or "",
            "yanit_sayisi": arac.get("replyCount", "") or "",
            "kalp": durum.get("heartState") == "TOOLBAR_HEART_STATE_HEARTED",
            "kalp_ipucu": arac.get("heartActiveTooltip", "") or "",
            "sabit": cvm.get("pinnedText", "") or "", "yanit_devam": ""}


def yorumlar(devam, video_id):
    """Bir parti yorum (ilk parti: video_sayfasi'nın yorum_devam anahtarıyla; ~20 yorum, 0,3-0,9 sn, gzip'siz
    ~260 KB) ya da bir yorumun yanıtları. Döner: {'sayi': '2.155 Yorum' (yalnız ilk partide),
    'siralar': [{'ad', 'devam', 'secili'}], 'yorumlar': [...], 'devam': sonraki partinin anahtarı ya da None}."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/next?prettyPrint=false",
                             {"context": _baglam(), "continuation": devam}))
    varliklar = {m.get("entityKey"): m.get("payload", {})
                 for m in _al(veri, "frameworkUpdates", "entityBatchUpdate", "mutations", vars=[])}
    sonuc = {"sayi": "", "siralar": [], "yorumlar": [], "devam": None}
    for k in veri.get("onResponseReceivedEndpoints", []):
        ogeler = _al(k, "reloadContinuationItemsCommand", "continuationItems", vars=None) \
            or _al(k, "appendContinuationItemsAction", "continuationItems", vars=[])
        for x in ogeler:
            if "commentsHeaderRenderer" in x:
                h = x["commentsHeaderRenderer"]
                sonuc["sayi"] = _yazi(h.get("countText"))
                for s in _al(h, "sortMenu", "sortFilterSubMenuRenderer", "subMenuItems", vars=[]):
                    sonuc["siralar"].append({"ad": s.get("title", ""), "secili": bool(s.get("selected")),
                                             "devam": _al(s, "serviceEndpoint", "continuationCommand", "token",
                                                          vars="")})
            elif "commentThreadRenderer" in x:
                t = x["commentThreadRenderer"]
                y = _yorum(_al(t, "commentViewModel", "commentViewModel", vars={}), varliklar, video_id)
                if y:
                    y["yanit_devam"] = next((_al(r, "continuationItemRenderer", "continuationEndpoint",
                                                 "continuationCommand", "token")
                                             for r in _al(t, "replies", "commentRepliesRenderer", "contents", vars=[])
                                             if "continuationItemRenderer" in r), None) or ""
                    sonuc["yorumlar"].append(y)
            elif "commentViewModel" in x:   # yanıtlar
                y = _yorum(x["commentViewModel"], varliklar, video_id)
                if y:
                    sonuc["yorumlar"].append(y)
            elif "continuationItemRenderer" in x:
                c = x["continuationItemRenderer"]
                # Yorumlarda devam anahtarı doğrudan, yanıtlarda "Daha fazla yanıt göster" düğmesinin içinde.
                sonuc["devam"] = _al(c, "continuationEndpoint", "continuationCommand", "token") \
                    or _al(c, "button", "buttonRenderer", "command", "continuationCommand", "token")
    return sonuc


def _kanal_sekmesi(kanal_id, params):
    """Kanalın bir sekmesindeki ilk ~30 video: (kanal adı, videolar, kanal resmi). Resim sol kenardaki abonelik
    listesi için: yoklamanın zaten yaptığı istekten, ek istek yok. Yalnız yoklama kullanıyor: Türkçe (YOKLAMA_DILI)."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                             {"context": _baglam(*YOKLAMA_DILI), "browseId": kanal_id, "params": params}))
    md = _al(veri, "metadata", "channelMetadataRenderer", vars={})
    ad = md.get("title") or ""
    resimler = _al(veri, "header", "pageHeaderRenderer", "content", "pageHeaderViewModel", "image",
                   "decoratedAvatarViewModel", "avatar", "avatarViewModel", "image", "sources", vars=[]) \
        or _al(md, "avatar", "thumbnails", vars=[])
    resim = (resimler[-1].get("url") if resimler else "") or ""
    for t in _al(veri, "contents", "twoColumnBrowseResultsRenderer", "tabs", vars=[]):
        tr = t.get("tabRenderer", {})
        # Kanalda istenen sekme yoksa YouTube başka bir sekmeyi seçili döndürüyor (26 Ekim: Canlı sekmesi olmayan
        # Wodahz'da Shorts geldi; Shorts ve süresiz videolar 'başlamamış yayın' sanılıyor, her yoklamada Canlı
        # sekmesi yeniden isteniyordu). Seçili sekme istenen değilse boş.
        if tr.get("selected"):
            if _sekme_turu(_al(tr, "endpoint", "browseEndpoint", "params", vars="")) != _sekme_turu(params):
                return ad, [], resim
            videolar, _ = _videolar_ve_devam(_al(tr, "content", "richGridRenderer", "contents", vars=[]))
            for v in videolar:
                v["kanal"] = v["kanal"] or ad
                v["kanal_id"] = kanal_id
            return ad, videolar, resim
    return ad, [], resim


def _sekme_turu(params):
    """Kanal sekmesinin params'ından sekmenin adı (videos, streams, shorts): base64 içinde düz yazıyla duruyor."""
    try:
        ham = base64.urlsafe_b64decode(urllib.parse.unquote(params) + "==")
    except ValueError:
        return ""
    return next((t for t in ("videos", "streams", "shorts") if t.encode() in ham), "")


def kanal_videolari(kanal_id):
    """Kanalın 'Videolar' sekmesindeki son ~30 video (süreleriyle): (ad, videolar, resim). RSS bozukken ve RSS
    yeni video gösterince süreleri almak için (22 Ekim düzeninin yedek yolu)."""
    return _kanal_sekmesi(kanal_id, "EgZ2aWRlb3PyBgQKAjoA")


def kanal_canli(kanal_id):
    """Kanalın 'Canlı' sekmesi (en yeniler önde): şu an süren yayınlar "canli", bitenler süreli, başlamamışlar
    süresiz. Canlı yayınlar 'Videolar' sekmesinde yok (25 Ekim, Lofi Girl ile denendi). (videolar, resim)."""
    return _kanal_sekmesi(kanal_id, "EgdzdHJlYW1z8gYECgJ6AA==")[1:]


def kanal_sayfasi(kanal_id):
    """Kanal sayfası: ad, @adı, abone ve video sayısı, resim, açıklama ve 'Videolar' sekmesinin ilk
    ~30 videosu (gzip'le ~41 KB). Devamı kanal_devami ile."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                             {"context": _baglam(), "browseId": kanal_id, "params": "EgZ2aWRlb3PyBgQKAjoA"}))
    md = _al(veri, "metadata", "channelMetadataRenderer", vars={})
    vm = _al(veri, "header", "pageHeaderRenderer", "content", "pageHeaderViewModel", vars={})
    parcalar = [p for r in _al(vm, "metadata", "contentMetadataViewModel", "metadataRows", vars=[])
                for p in r.get("metadataParts", [])]
    tutamac = next((_al(p, "text", "content", vars="") for p in parcalar
                    if _al(p, "text", "content", vars="").startswith("@")), "")
    # Abone ve video sayısı @adın ardından bu sırayla (29 Ekim; önceden "abone"/"subscriber" sözcüğüne bakılıyordu,
    # YouTube artık programın diliyle yazıyor). Abone sayısı gizli kanalda tek parça kalır: abone sayısının
    # okunuşu (accessibilityLabel) var, video sayısının yok.
    sayilar = [p for p in parcalar if not _al(p, "text", "content", vars="").startswith("@")]
    abone = next((_al(p, "text", "content", vars="") for p in sayilar[:1]
                  if len(sayilar) > 1 or "accessibilityLabel" in p), "")
    video_sayisi = next((_al(p, "text", "content", vars="") for p in sayilar
                         if _al(p, "text", "content", vars="") != abone), "")
    resimler = _al(vm, "image", "decoratedAvatarViewModel", "avatar", "avatarViewModel", "image", "sources", vars=[]) \
        or _al(md, "avatar", "thumbnails", vars=[])
    resim = (resimler[-1].get("url") if resimler else "") or ""
    videolar, devam = [], None
    for t in _al(veri, "contents", "twoColumnBrowseResultsRenderer", "tabs", vars=[]):
        tr = t.get("tabRenderer", {})
        if tr.get("selected"):
            videolar, devam = _videolar_ve_devam(_al(tr, "content", "richGridRenderer", "contents", vars=[]))
    ad = md.get("title") or _al(vm, "title", "dynamicTextViewModel", "text", "content", vars="")
    for v in videolar:
        v["kanal"], v["kanal_id"] = v["kanal"] or ad, kanal_id
    return {"id": kanal_id, "ad": ad, "tutamac": tutamac, "abone": abone.replace("\xa0", " "),
            "video_sayisi": video_sayisi.replace("\xa0", " "), "resim": resim,
            "aciklama": md.get("description") or "", "videolar": videolar, "devam": devam}


def kanal_shorts(kanal_id, yoklama=False):
    """Kanalın 'Shorts' sekmesi (en yeniler önde): (videolar, devam). Devamı kanal_devami ile. Kanal sayfasında
    programın dilinde, yoklamada Türkçe (YOKLAMA_DILI)."""
    baglam = _baglam(*YOKLAMA_DILI) if yoklama else _baglam()
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                             {"context": baglam, "browseId": kanal_id, "params": "EgZzaG9ydHPyBgUKA5oBAA=="}))
    for t in _al(veri, "contents", "twoColumnBrowseResultsRenderer", "tabs", vars=[]):
        tr = t.get("tabRenderer", {})
        if tr.get("selected"):
            return _videolar_ve_devam(_al(tr, "content", "richGridRenderer", "contents", vars=[]))
    return [], None


def kanal_yuklemeleri(kanal_id):
    """Kanalın bütün yüklemelerinin listesi (UU + kimliğin UC'den sonrası), ilk ~100, süreleriyle. Kanal sayfası
    "Bu kanal kullanılamıyor" deyip boş dönerken de çalışıyor (25 Ekim, Ahmet Nesin: sekmeler boş, videolar
    oynuyor, RSS'te var). Yalnız yoklama kullanıyor: Türkçe (YOKLAMA_DILI)."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                             {"context": _baglam(*YOKLAMA_DILI), "browseId": "VLUU" + kanal_id[2:]}))
    for t in _al(veri, "contents", "twoColumnBrowseResultsRenderer", "tabs", vars=[]):
        return _videolar_ve_devam(_al(t, "tabRenderer", "content", "sectionListRenderer", "contents", vars=[]))[0]
    return []


def video_var_mi(video_id):
    """Video herkese açık mı (oEmbed, küçük JSON): gizli ya da silinmişse False (401/403/404), açıksa True, YouTube
    başka bir şey derse None. RSS kanal bir videoyu gizledikten ya da sildikten sonra da bir süre gösteriyor (25 Ekim,
    KRT TV)."""
    r = _havuz.request("GET", "https://www.youtube.com/oembed?format=json&url=https://www.youtube.com/watch?v="
                       + video_id, headers={"User-Agent": PROGRAM_ADI})
    if r.status == 429:
        raise CokIstek()
    return True if r.status == 200 else (False if r.status in (401, 403, 404) else None)


def kanal_devami(kanal_id, ad, devam):
    """Kanalın 'Videolar' sekmesinin sonraki partisi."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                             {"context": _baglam(), "continuation": devam}))
    ham = []
    for k in veri.get("onResponseReceivedActions", []) + veri.get("onResponseReceivedEndpoints", []):
        ham += _al(k, "appendContinuationItemsAction", "continuationItems", vars=[])
    videolar, sonraki = _videolar_ve_devam(ham)
    for v in videolar:
        v["kanal"], v["kanal_id"] = v["kanal"] or ad, kanal_id
    return videolar, sonraki


def kanal_rss(kanal_id, yalniz_shorts=False, yalniz_uzun=False):
    """Kanalın RSS listesi: son 15 video, kesin yayın zamanıyla. Programın kendi adıyla gidilir
    (3. ilke). Bozuksa (404, ara ara oluyor) None. Shorts'un bağlantısı /shorts/ID (uzun videonunki
    watch?v=): her videoda "shorts" işareti. yalniz_shorts: kanalın yalnız Shorts listesi (UUSH + kimliğin UC'den
    sonrası; 25 Ekim'de denendi), son 15 Shorts. yalniz_uzun: kanalın yalnız uzun videoları (UULF; Shorts ve canlı yayın
    yok; 28 Ekim'de denendi), son 15 video."""
    import xml.etree.ElementTree as ET
    from datetime import datetime
    liste = "UUSH" if yalniz_shorts else "UULF" if yalniz_uzun else ""
    adres = ("https://www.youtube.com/feeds/videos.xml?playlist_id=" + liste + kanal_id[2:] if liste
             else "https://www.youtube.com/feeds/videos.xml?channel_id=" + kanal_id)
    r = _havuz.request("GET", adres, headers={"User-Agent": PROGRAM_ADI, "Accept-Encoding": "gzip"})
    if r.status in (404, 500, 502, 503):
        return None  # YouTube'un RSS'i aynı kanala rastgele 200/404/500 veriyor (23 Ekim)
    if r.status == 429:
        raise CokIstek()
    if r.status != 200:
        raise YouTubeHatasi(f"RSS {r.status}")
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
          "media": "http://search.yahoo.com/mrss/"}
    kok = ET.fromstring(r.data)
    ad = kok.findtext("a:title", "", ns)
    videolar = []
    for e in kok.findall("a:entry", ns):
        vid = e.findtext("yt:videoId", "", ns)
        yayin = e.findtext("a:published", "", ns)
        try:
            ts = datetime.fromisoformat(yayin.replace("Z", "+00:00")).timestamp()
        except ValueError:
            ts = 0
        bag = (e.find("a:link", ns).get("href") or "") if e.find("a:link", ns) is not None else ""
        # İzlenme sayısı RSS'in o anki sayısı (her bakışta yenilenir; ek istek yok).
        ist = e.find("media:group/media:community/media:statistics", ns)
        try:
            izlenme = int(ist.get("views")) if ist is not None else None
        except (TypeError, ValueError):
            izlenme = None
        videolar.append({"id": vid, "baslik": e.findtext("a:title", "", ns), "kanal": ad, "kanal_id": kanal_id,
                         "yayin": ts, "shorts": yalniz_shorts or "/shorts/" in bag, "izlenme": izlenme})
    if liste:   # listenin adı "Short videos" ya da "Videos"; kanalın adı ilk girdinin yazarında
        ad = kok.findtext("a:entry/a:author/a:name", "", ns)
        for v in videolar:
            v["kanal"] = ad
    return {"ad": ad, "videolar": videolar}


class CokIstek(YouTubeHatasi):
    """YouTube 429: bir süre durulmalı."""


def oneri_devami(devam):
    """Önerilerin sonraki partisi."""
    veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/next?prettyPrint=false",
                             {"context": _baglam(), "continuation": devam}))
    ham = []
    for k in veri.get("onResponseReceivedEndpoints", []):
        ham += _al(k, "appendContinuationItemsAction", "continuationItems", vars=[])
    return _videolar_ve_devam(ham)


# Aboneliği olmayan kişinin abonelik sayfası boş durmasın (28 Ekim: "boş göstermek iyi değil, eli boş gözükmek gibi").
# Girişsiz YouTube ana sayfası "Başlamak için arama yapın" diyor, Trendler kaldırılmış (400); YouTube'un kendi konu
# sayfaları ise girişsiz de ülkeye göre (gl, ceviri.ulke) video veriyor (sayfa başına ~0,4 sn). Bölüm: (ad, başlık,
# sayfa, raf başına).
# Canlı yayınlar alınmaz: konu sayfalarının canlı rafında kumarhane ve yabancı dilde yayınlar çıkıyordu; Oyun sayfası
# eski biçimde ve yalnız 5 video veriyordu.
GUNDEM = [("muzik", QT_TR_NOOP("Yeni müzik videoları"), "UC-9-kyTW8ZkZNDHQJ6FgpwQ", 12),   # öbür rafları oynatma listesi
          ("spor", QT_TR_NOOP("Spor"), "UCEgdi0XIXXZ-qJOFPf4JSKw", 6),
          ("haber", QT_TR_NOOP("Haberler"), "UCYfdidRxbB8Qhf0Nx7ioOYw", 2)]          # her raf bir haber: ilk iki video
GUNDEM_EN_COK = 24


def gundem():
    """[{"ad", "baslik", "videolar"}]: videosu gelen bölümler. Bir sayfa gelmezse o bölüm yok."""
    bolumler = []
    for ad, baslik, kimlik, raf_basina in GUNDEM:
        try:
            veri = json.loads(_getir("https://www.youtube.com/youtubei/v1/browse?prettyPrint=false",
                                     {"context": _baglam(), "browseId": kimlik}))
        except (YouTubeHatasi, urllib3.exceptions.HTTPError, ValueError):
            continue
        videolar, gorulen = [], set()
        for t in _al(veri, "contents", "twoColumnBrowseResultsRenderer", "tabs", vars=[]):
            if not _al(t, "tabRenderer", "selected"):
                continue
            for b in _al(t, "tabRenderer", "content", "richGridRenderer", "contents", vars=[]):
                raf = _al(b, "richSectionRenderer", "content", "richShelfRenderer", "contents", vars=[])
                alinan = [v for v in _videolar_ve_devam(raf)[0] if not v["canli"] and v["sure"] and v["id"] not in gorulen]
                for v in alinan[:raf_basina]:
                    gorulen.add(v["id"])
                    videolar.append(v)
        if videolar:
            bolumler.append({"ad": ad, "baslik": tr(baslik), "videolar": videolar[:GUNDEM_EN_COK]})
    return bolumler


if __name__ == "__main__":
    import sys
    t = time.time()
    s = ara(sys.argv[1] if len(sys.argv) > 1 else "tears of steel")
    print(f"arama {time.time()-t:.2f} sn, {len(s['videolar'])} video, devam: {bool(s['devam'])}")
    for o in s["videolar"][:3]:
        print(" ", o)
    t = time.time()
    s2 = ara(None, s["devam"])
    print(f"arama devamı {time.time()-t:.2f} sn, {len(s2['videolar'])} video")
    t = time.time()
    v = video_sayfasi(s["videolar"][0]["id"])
    print(f"video sayfası {time.time()-t:.2f} sn: {v['baslik']!r} / {v['kanal']!r}, {len(v['oneriler'])} öneri")
    print({k: (x[:80] if isinstance(x, str) else x) for k, x in v.items() if k not in ("oneriler",)})
    for o in v["oneriler"][:3]:
        print(" ", o)
    t = time.time()
    d, _ = oneri_devami(v["oneri_devam"])
    print(f"öneri devamı {time.time()-t:.2f} sn, {len(d)} öneri")
    t = time.time()
    y = yorumlar(v["yorum_devam"], v["id"])
    print(f"yorumlar {time.time()-t:.2f} sn: {y['sayi']}, {len(y['yorumlar'])} yorum, sıralar "
          f"{[s['ad'] for s in y['siralar']]}, devam: {bool(y['devam'])}")
    ilk = next((x for x in y["yorumlar"] if x["yanit_devam"]), None)
    if ilk:
        t = time.time()
        yn = yorumlar(ilk["yanit_devam"], v["id"])
        print(f"yanıtlar {time.time()-t:.2f} sn: {len(yn['yorumlar'])} yanıt ({ilk['yanit_sayisi']} bekleniyor), "
              f"devam: {bool(yn['devam'])}")
        print(" ", {k: x for k, x in yn["yorumlar"][0].items() if k != "metin"})
