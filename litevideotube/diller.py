"""Dil adları ve sıralaması: altyazı ve ses dili menüleri için. Ekran dili Türkçeyken bu dosyadaki Türkçe adlar ve
Türk alfabesi; başka dilde Qt'nin İngilizce dil adları (Qt yalnız İngilizce ve dilin kendi adını veriyor; öbür
ekran dilleri için de şimdilik İngilizce) ve harf farkı gözetmeyen sıra.
"""
import unicodedata

from .ceviri import kurulan_dil

# Dil adları Türkçe (YouTube'un altyazı ve ses dilleri). Kaynak: Debian iso-codes Türkçe çevirisi
# (/usr/share/locale/tr/LC_MESSAGES/iso_639-*.mo, iso_3166-1.mo; 23 Ekim'de üretildi), alışılmış adlar elle düzeltildi.
DIL_ADLARI = {
    "aa": "Afar dili",
    "ab": "Abhazca",
    "af": "Afrikanca",
    "ak": "Akan dili",
    "am": "Amharca",
    "ar": "Arapça",
    "as": "Assamca",
    "ay": "Aymara dili",
    "az": "Azerice",
    "ba": "Başkurtça",
    "be": "Belarusça",
    "bg": "Bulgarca",
    "bho": "Bhojpuri",
    "bn": "Bengalce",
    "bo": "Tibetçe",
    "br": "Bretonca",
    "bs": "Boşnakça",
    "ca": "Katalanca",
    "ceb": "Sebuano dili",
    "co": "Korsikaca",
    "crs": "Seyşel Kreolü",
    "cs": "Çekçe",
    "cy": "Galce",
    "da": "Danca",
    "de": "Almanca",
    "dv": "Maldivce",
    "dz": "Butanca",
    "ee": "Eve dili",
    "el": "Yunanca",
    "en": "İngilizce",
    "eo": "Esperanto",
    "es": "İspanyolca",
    "es-ES": "İspanyolca (İspanya)",
    "et": "Estonca",
    "eu": "Baskça",
    "fa": "Farsça",
    "fi": "Fince",
    "fil": "Filipince",
    "fj": "Fiji dili",
    "fo": "Faroece",
    "fr": "Fransızca",
    "fy": "Frizce",
    "ga": "İrlandaca",
    "gaa": "Ga dili",
    "gd": "İskoç Galcesi",
    "gl": "Galiçyaca",
    "gn": "Guarani dili",
    "gu": "Güceratça",
    "gv": "Manx dili",
    "ha": "Hausa dili",
    "haw": "Havaice",
    "hi": "Hintçe",
    "hmn": "Hmong dili",
    "hr": "Hırvatça",
    "ht": "Haiti Kreolü",
    "hu": "Macarca",
    "hy": "Ermenice",
    "id": "Endonezce",
    "ig": "İbo dili",
    "is": "İzlandaca",
    "it": "İtalyanca",
    "iu": "İnuitçe",
    "iw": "İbranice",
    "ja": "Japonca",
    "jv": "Cava dili",
    "ka": "Gürcüce",
    "kha": "Khasi dili",
    "kk": "Kazakça",
    "kl": "Grönlandca",
    "km": "Kmerce",
    "kn": "Kannada dili",
    "ko": "Korece",
    "kri": "Krio dili",
    "ku": "Kürtçe",
    "ky": "Kırgızca",
    "la": "Latince",
    "lb": "Lüksemburgca",
    "lg": "Ganda dili",
    "ln": "Lingala",
    "lo": "Laoca",
    "lt": "Litvanyaca",
    "lua": "Luba-Lulua dili",
    "luo": "Luo dili",
    "lv": "Letonca",
    "mfe": "Mauritius Kreolü",
    "mg": "Malgaşça",
    "mi": "Maori dili",
    "mk": "Makedonca",
    "ml": "Malayalam dili",
    "mn": "Moğolca",
    "mr": "Marathi dili",
    "ms": "Malayca",
    "mt": "Maltaca",
    "my": "Birmanca",
    "ne": "Nepalce",
    "new": "Nevarice",
    "nl": "Felemenkçe",
    "no": "Norveççe",
    "nso": "Kuzey Sotho dili",
    "ny": "Çiçevaca",
    "oc": "Oksitanca",
    "om": "Oromo dili",
    "or": "Oriya dili",
    "os": "Osetçe",
    "pa": "Pencapça",
    "pam": "Pampanga dili",
    "pl": "Lehçe",
    "ps": "Peştuca",
    "pt": "Portekizce",
    "pt-BR": "Portekizce (Brezilya)",
    "pt-PT": "Portekizce (Portekiz)",
    "qu": "Keçuva dili",
    "rn": "Kirundi",
    "ro": "Rumence",
    "ru": "Rusça",
    "rw": "Kinyarwanda",
    "sa": "Sanskritçe",
    "sd": "Sintçe",
    "sg": "Sango dili",
    "si": "Seylanca",
    "sk": "Slovakça",
    "sl": "Slovence",
    "sm": "Samoaca",
    "sn": "Şona dili",
    "so": "Somalice",
    "sq": "Arnavutça",
    "sr": "Sırpça",
    "ss": "Svati dili",
    "st": "Güney Sotho dili",
    "su": "Sunda dili",
    "sv": "İsveçce",
    "sw": "Svahili",
    "ta": "Tamilce",
    "te": "Telugu dili",
    "tg": "Tacikçe",
    "th": "Tayca",
    "ti": "Tigrinyaca",
    "tk": "Türkmence",
    "tn": "Setsvana",
    "to": "Tonga dili",
    "tr": "Türkçe",
    "ts": "Tsonga dili",
    "tt": "Tatarca",
    "tum": "Tumbuka dili",
    "ug": "Uygurca",
    "uk": "Ukraynaca",
    "ur": "Urduca",
    "uz": "Özbekçe",
    "ve": "Venda dili",
    "vi": "Vietnamca",
    "war": "Varay dili",
    "wo": "Volofça",
    "xh": "Xhosa dili",
    "yi": "Yidiş",
    "yo": "Yoruba dili",
    "zh-CN": "Çince (Basitleştirilmiş)",
    "zh-Hans": "Çince (Basitleştirilmiş)",
    "zh-Hant": "Çince (Geleneksel)",
    "zu": "Zuluca",
}

ESKI_KODLAR = {"he": "iw", "jv": "jw"}  # YouTube bazı dillerde eski kodu kullanıyor

_ALFABE = "aâbcçdefgğhıiîjklmnoöpqrsştuûüvwxyz"
_SIRA = {h: i for i, h in enumerate(_ALFABE)}


def dil_adi(kod):
    kod = kod or ""
    if kurulan_dil() != "tr":
        return _ingilizce_ad(kod)
    if kod in DIL_ADLARI:
        return DIL_ADLARI[kod]
    kok = kod.split("-")[0]
    return DIL_ADLARI.get(kok) or DIL_ADLARI.get(ESKI_KODLAR.get(kok, "")) or kod


def _ingilizce_ad(kod):
    """Qt'den İngilizce ad; yazı ya da ülke farkı varsa parantezde ("Chinese (Simplified Han)", "Portuguese (Brazil)")."""
    from PySide6.QtCore import QLocale
    kok, _, ek = kod.partition("-")
    yerel = QLocale("_".join([{"iw": "he", "jw": "jv"}.get(kok, kok)] + ([ek] if ek else [])))
    if yerel.language() == QLocale.Language.C:
        return kod
    ad = QLocale.languageToString(yerel.language())
    if ek:
        ayrinti = QLocale.scriptToString(yerel.script()) if len(ek) == 4 else QLocale.territoryToString(yerel.territory())
        ad += f" ({ayrinti})"
    return ad


def sira_anahtari(s):
    """Dil adlarının sırası: Türkçede Türk alfabesi, başka dilde duz_sira."""
    return tr_anahtar(s) if kurulan_dil() == "tr" else duz_sira(s)


def duz_sira(s):
    """Türkçe dışındaki sıra: büyük-küçük harf ve şapka, çengel gibi işaretler gözetilmez (Ç c'nin, Ö o'nun yanında);
    eşitlikte işaretli olan sonra. Liste (öbür sıra anahtarları gibi), harf yerine kod noktaları."""
    k = (s or "").casefold()
    yalin = "".join(h for h in unicodedata.normalize("NFKD", k) if not unicodedata.combining(h)).replace("ı", "i")
    return [ord(h) for h in yalin] + [0] + [ord(h) for h in k]


def kucult(s):
    """Türkçe küçük harf: I → ı, İ → i (Python'un lower()'ı İ'yi 'i̇' yapar)."""
    return s.replace("I", "ı").replace("İ", "i").lower()


def tr_anahtar(s):
    """Türk alfabesine göre sıralama anahtarı (Ç, Ğ, I, İ, Ö, Ş, Ü yerinde)."""
    return [_SIRA.get(h, 100 + ord(h)) for h in kucult(s)]
