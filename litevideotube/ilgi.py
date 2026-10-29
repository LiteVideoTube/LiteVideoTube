"""Programın kendi sıralaması: YouTube'un algoritması yerine izleme geçmişinden.

İzlenen her video, kanalına puan verir: izlenen dakika (en çok 20, uzun yayınlar her şeyi ezmesin) ve video
gerçekten izlendiyse (en az bir dakikası ya da yarısı) 1 puan; birkaç saniye bakıp geçilen video puan vermez.
Puanın yarısı 14 günde silinir; yeni bir şeye merak salınınca o kanal kendiliğinden öne çıkar, bırakılan kanal
kendiliğinden geriler. Abonelik sayfasının "İzlediklerine göre" bölümü (abonelik.py, akis) ilgi duyulan
kanalların son üç günkü videolarını, puana göre en çok 3 gün daha yeniymiş gibi sayarak dizer; bir kanaldan en çok
iki video (24 Ekim denemesinde bir haber kanalının 48 saniyelik izlenmesi ilk sekiz videonun yedisini o kanala
veriyordu). Bölümün altındaki akış zamana göre kalır.

İlgili kanallar: izlenen videoların yanında YouTube'un verdiği öneriler (videoya göre, kişiye özel değil)
kaydedilir (kayit.py, oneri_kanal). Abone olunmamış bir kanal, ilgi duyulan videoların yanında ne kadar çok
çıkıyorsa ve kendisi ne kadar izlendiyse o kadar önde önerilir. Hepsi bu bilgisayarda; hesap yok, ek istek yok.
Qt'siz: arka plan yoklaması da kullanabilsin.
"""
import math
import time

YARI_OMUR = 14 * 86400
ONE_ALMA_EN_COK = 3 * 86400
BAS_PAYI = 10.0   # kayit.py'deki gibi: 10 saniyeden az izlenen video izlenmemiş sayılır
KANAL_BASINA = 2  # bir kanalın öne alınan en yeni video sayısı


def video_puani(konum, sure):
    konum = min(konum or 0.0, sure or 0.0) if sure else (konum or 0.0)
    if konum < BAS_PAYI:
        return 0.0
    izlendi = konum >= 60.0 or (sure and konum >= sure / 2)
    return (1.0 if izlendi else 0.0) + min(konum / 60.0, 20.0)


def _soluk(son, simdi):
    return 0.5 ** (max(0.0, simdi - (son or 0.0)) / YARI_OMUR)


def kanal_ilgileri(db, simdi=None):
    """{kanal_id: puan} izleme geçmişinden."""
    simdi = simdi or time.time()
    puan = {}
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'gecmis'").fetchone():
        return puan   # geçmiş tablosunu program (kayit.py) kurar; yoklama ondan önce de çalışabilir
    for kanal_id, konum, sure, son in db.execute(
            "SELECT kanal_id, konum, sure, son FROM gecmis WHERE kanal_id IS NOT NULL AND kanal_id != ''"):
        p = video_puani(konum, sure) * _soluk(son, simdi)
        if p > 0:
            puan[kanal_id] = puan.get(kanal_id, 0.0) + p
    return puan


def one_alma(puan):
    """Akışta videonun kaç saniye daha yeniymiş gibi sayılacağı: 5 puan bir gün, 15 puan iki gün, en çok üç gün."""
    return min(ONE_ALMA_EN_COK, 86400 * math.log2(1.0 + puan / 5.0)) if puan > 0 else 0.0


def sirala(videolar, puan, kanal=lambda v: v["kanal_id"], yayin=lambda v: v["yayin"]):
    """Akışı ilgiye göre dizer; videolar en yeniden eskiye gelmeli. Kanal başına en yeni KANAL_BASINA video öne alınır."""
    sayac = {}

    def anahtar(v):
        k = kanal(v)
        sayac[k] = sayac.get(k, 0) + 1
        return (yayin(v) or 0) + (one_alma(puan.get(k, 0.0)) if sayac[k] <= KANAL_BASINA else 0.0)
    anahtarlar = [anahtar(v) for v in videolar]
    return [v for _, v in sorted(zip(anahtarlar, videolar), key=lambda x: x[0], reverse=True)]


def ilgili_kanallar(db, sinir=10, simdi=None):
    """Abone olunmamış, ilgi çekebilecek kanallar: [{'id', 'ad', 'puan'}], en öndeki başta."""
    simdi = simdi or time.time()
    abone = {r[0] for r in db.execute("SELECT id FROM kanal")}
    puan, ad = {}, {}
    # Kendisi izlenen ama abone olunmayan kanal.
    for kanal_id, kanal, konum, sure, son in db.execute(
            "SELECT kanal_id, kanal, konum, sure, son FROM gecmis WHERE kanal_id IS NOT NULL AND kanal_id != ''"):
        if kanal_id in abone:
            continue
        p = 2.0 * video_puani(konum, sure) * _soluk(son, simdi)
        if p > 0:
            puan[kanal_id] = puan.get(kanal_id, 0.0) + p
            ad[kanal_id] = ad.get(kanal_id) or kanal
    # İzlenen videoların yanında önerilen kanal: o videonun puanı kadar.
    for kanal_id, kanal, konum, sure, son in db.execute(
            """SELECT o.kanal_id, o.ad, g.konum, g.sure, g.son FROM oneri_kanal o JOIN gecmis g ON g.id = o.video_id"""):
        if kanal_id in abone:
            continue
        p = video_puani(konum, sure) * _soluk(son, simdi) / 4.0
        if p > 0:
            puan[kanal_id] = puan.get(kanal_id, 0.0) + p
            ad[kanal_id] = ad.get(kanal_id) or kanal
    sirali = sorted(puan, key=puan.get, reverse=True)[:sinir]
    return [{"id": k, "ad": ad.get(k) or "", "puan": round(puan[k], 1)} for k in sirali]
