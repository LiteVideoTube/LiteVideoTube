"""Yenilikler: sürüm notları (29 Ekim). Program güncellendikten sonra ilk açılışta kısa bir pencere o sürümün
ana başlıklarını gösterir ("Güncellendi"); ayrıntılar programın içindeki Yenilikler sayfasında (lvt://yenilikler,
kişi menüsünün en altındaki satır). İsteyen ayrıntıyı okur, istemeyen pencereyi kapatır.

Notlar yenilikler/<dil>.json'da, en yeni sürüm başta: [{"surum": "0.1.0", "tarih": "2026-11-02",
"maddeler": [{"baslik": "...", "ayrinti": "..."}]}]. Kaynak Türkçe (tr.json); öbür diller aynı sürümleri ve aynı sayıda
maddeyi taşır (araclar/yenilikler_sinama.py bakar, yayın akışı da). Dilin dosyası yoksa İngilizce, o da yoksa Türkçe.

Programın sürümü youtube.PROGRAM_ADI'de (yayın akışı yazar). Son açılan sürüm kişilerin ortak ayarında
("son_surum", kisiler.json): ilk kurulumda pencere çıkmaz, yalnız sürüm yazılır; sürüm büyüdüyse çıkar.
"""
import json
from pathlib import Path

from PySide6.QtCore import Property, QObject, Slot

from . import ceviri, yoklama
from .youtube import PROGRAM_ADI

KLASOR = Path(__file__).resolve().parent / "yenilikler"
EN_COK_BASLIK = 5   # kısa pencerede; birkaç sürüm birden atlandıysa en yenilerinden


def surum():
    return PROGRAM_ADI.split("/")[-1]


def anahtar(s):
    """"0.10.2" > "0.9.9" diye karşılaştırmak için."""
    try:
        t = tuple(int(x) for x in s.split("."))
    except ValueError:
        return ()
    return t + (0,) * (3 - len(t))   # "0.1" ile "0.1.0" aynı


def notlar(dil=None):
    for aday in (dil or ceviri.kurulan_dil(), ceviri.YEDEK_DIL, ceviri.KAYNAK_DIL):
        try:
            with open(KLASOR / f"{aday}.json", encoding="utf-8") as f:
                return sorted(json.load(f), key=lambda s: anahtar(s["surum"]), reverse=True)
        except (OSError, ValueError):
            continue
    return []


class Yenilikler(QObject):
    def __init__(self):
        super().__init__()
        self._surum = surum()
        k = yoklama.kisiler()
        son = k.get("son_surum", "")
        # İlk kurulumda (son sürüm yok) ya da aynı sürümde çıkmaz; geri dönüldüyse de çıkmaz.
        self._eski = son if son and anahtar(son) < anahtar(self._surum) else ""
        if son != self._surum:
            k["son_surum"] = self._surum
            yoklama.kisileri_yaz(k)

    surumAdi = Property(str, lambda s: s._surum, constant=True)
    # Güncellendikten sonraki ilk açılış: önceki sürüm (yoksa "")
    oncekiSurum = Property(str, lambda s: s._eski, constant=True)

    @Slot(result=list)
    def hepsi(self):
        return notlar()

    @Slot(result=list)
    def yeniBasliklar(self):
        """Önceki sürümden sonra gelen sürümlerin başlıkları, en yenisi başta."""
        b = []
        for s in notlar():
            if anahtar(s["surum"]) <= anahtar(self._eski) or anahtar(s["surum"]) > anahtar(self._surum):
                continue
            b += [m["baslik"] for m in s["maddeler"]]
        return b[:EN_COK_BASLIK]
