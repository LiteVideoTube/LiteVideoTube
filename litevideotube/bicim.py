"""Tarih, saat ve sayı yazıları ekran diline göre (ceviri.kur Qt'nin varsayılan yerel ayarını o dile alır).
Ay ve gün adları Qt'den (Türkçede elle tutulan eski tablolarla aynı: "3 Kasım", "Cuma"); gün ve ayın sırası çevrilen
biçimde ("d MMMM", İngilizcede "MMMM d"). Yalnız Qt'yi zaten yükleyen modüller kullanır (arka plan yoklaması değil)."""
from PySide6.QtCore import QDate, QLocale, QTime

from .ceviri import kurulan_dil, tr


def ondalik():
    return QLocale().decimalPoint()


def gun_ay(g, yil_da=False):
    """g: date ya da datetime. "3 Kasım", yıl_da ise "3 Kasım 2025"."""
    return QLocale().toString(QDate(g.year, g.month, g.day), tr("d MMMM yyyy") if yil_da else tr("d MMMM"))


def gun_adi(g):
    """Haftanın günü: "Cuma"."""
    return QLocale().standaloneDayName(g.isoweekday())


def saat(t):
    """datetime ya da (saat, dakika): "22:25" (İngilizcede "10:25 PM")."""
    sa, dk = t if isinstance(t, tuple) else (t.hour, t.minute)
    return QLocale().toString(QTime(sa, dk), QLocale.FormatType.ShortFormat)


def turkce_mi(sorgu=""):
    """Küçük harf çevirisi Türkçe mi yapılsın (I -> ı, İ -> i): ekran dili Türkçeyken ya da aranan söz Türkçeye özgü
    harf içerirken (İngilizce ekranda Türkçe başlık arayan "ışık" bulsun)."""
    return kurulan_dil() == "tr" or any(h in sorgu for h in "ıİğĞşŞ")


def kucuk(s, turkce):
    if turkce:
        return s.replace("I", "ı").replace("İ", "i").lower()
    return s.replace("İ", "i").lower()   # Python'un lower()'ı İ'yi "i̇" yapıyor
