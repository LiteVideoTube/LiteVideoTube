"""Ekran kartının VP9'u çözüp çözemediği (28 Ekim).

YouTube bazı videolarda H.264 kopyasına çok az veri ayırıyor (ycnxudvQSWI 720p: H.264 332 kbps, VP9 718 kbps); sitede
oynayan VP9 olduğu için aynı 720p programda bulanık görünüyordu. Program H.264'ü eski ekran
kartları da çözebilsin diye seçiyordu; ekran kartı VP9'u da çözebiliyorsa VP9 seçilir (cozumle.sadelestir), çözemeyende
H.264 kalır (işlemci yorulmasın).

Nasıl anlaşılır: program açılınca arka planda yarım saniyelik, 320x180, ~900 baytlık bir VP9 dosyası (aşağıda gömülü) ayrı
bir mpv'yle, görüntüsüz açılır; mpv'nin kullandığı çözücüye (hwdec-current) bakılır. Ekran kartı çözebiliyorsa "vaapi-copy"
(Linux), "d3d11va-copy" (Windows) gibi bir ad, çözemiyorsa önce denenen adın ardından "no" gelir; son değere bakılır.
Bu makinede (Intel HD 620) VP9 çözülüyor, AV1 çözülmüyor. Sınama bitmeden açılan video H.264'le açılır. 10 bitlik VP9
(HDR, vp09.02) sınanmaz, seçilmez.
"""
import base64
import os
import tempfile
import threading

from . import iz

vp9 = False   # sınama sonucu; bitene kadar False (H.264)

_ORNEK = (
    "GkXfo59ChoEBQveBAULygQRC84EIQoKEd2VibUKHgQJChYECGFOAZwEAAAAAAAM5EU2bdLpNu4tTq4QVSalmU6yBoU27i1OrhBZU"
    "rmtTrIHYTbuMU6uEElTDZ1OsggEfTbuMU6uEHFO7a1OsggMj7AEAAAAAAABZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAVSalmsirXsYMPQkBNgI1M"
    "YXZmNjAuMTYuMTAwV0GNTGF2ZjYwLjE2LjEwMESJiEB/QAAAAAAAFlSua8KuAQAAAAAAADnXgQFzxYj8PCGKearUEpyBACK1nIN1"
    "bmSIgQCGhVZfVlA5g4EBI+ODhAH8oFXgirCCAUC6gbSagQISVMNnQIBzc6BjwIBnyJpFo4dFTkNPREVSRIeNTGF2ZjYwLjE2LjEw"
    "MHNz2mPAi2PFiPw8IYp5qtQSZ8ilRaOHRU5DT0RFUkSHmExhdmM2MC4zMS4xMDIgbGlidnB4LXZwOWfIoUWjiERVUkFUSU9ORIeT"
    "MDA6MDA6MDAuNTAwMDAwMDAwAB9DtnVBeOeBAKOjgQAAgIJJg0IAE/ALNgA4JBwZQgAAMGAAAGZCyn7NeWpvzECjloEAIQCGAECS"
    "HABf4AADIAAAWjUXrhCjloEAQwCGAECSHABdwAADIAAAWjUXrhCjloEAZACGAECSHABegAADIAAAWjUXrhCjloEAhQCGAECSHABc"
    "YAADIAAAWjUXrhCjloEApwCGAECSHABaIAADIAAAWjUXrhCjloEAyACGAECSnABYAAADIAAAWjUXrhCjloEA6QCGAECSnABVwAAD"
    "IAAAWjUXrhCjloEBCwCGAECSnABU4AADIAAAWjUXrhCjloEBLACGAECSnABUIAADIAAAWjUXrhCjloEBTQCGAMCSnABQIAADIAAA"
    "WjUXrhCjloEBbwCGAECSnABTQAADIAAAWjUXrhCjloEBkACGAECSnABSYAADIAAAWjUXrhCjloEBsQCGAECSnABRoAADIAAAWjUX"
    "rhCjloEB0wCGAECSnABQ4AADIAAAWjUXrhAcU7trkbuPs4EAt4r3gQHxggGl8IED"
)


def _sina():
    global vp9
    try:
        import mpv
        yol = os.path.join(tempfile.gettempdir(), "litevideotube-vp9-sinama.webm")
        with open(yol, "wb") as f:
            f.write(base64.b64decode(_ORNEK))
        gorulen = []
        bitti = threading.Event()
        p = mpv.MPV(vo="null", ao="null", hwdec="auto-safe", config=False, ytdl=False)
        p.observe_property("hwdec-current", lambda _ad, deger: deger and gorulen.append(deger))

        @p.event_callback("end-file")
        def _bitti(_olay):
            bitti.set()
        p.command("loadfile", yol)
        bitti.wait(10)
        p.terminate()
        vp9 = bool(gorulen) and gorulen[-1] != "no"
        iz.yaz(f"VP9 donanımla çözülüyor mu: {'evet' if vp9 else 'hayır'} ({', '.join(gorulen) or 'çözücü yok'})")
    except Exception as e:
        iz.yaz(f"VP9 sınaması yapılamadı: {e!r}")


def sina():
    """Program açılınca bir kez, arka planda."""
    threading.Thread(target=_sina, daemon=True).start()
