"""Programın simgesi (litevideotube.svg): bebe mavisi karo, karoyu dolduran lacivert çerçeveli monitör, beyaz ekranda
sapı ve damarlarıyla yaprak. Her boyda aynı çizim; her boy ayrı çizilir ki küçükte de keskin dursun. Pencere simgesi ve
Windows paketinin .ico'su buradan."""
from pathlib import Path
from PySide6.QtGui import QIcon

KLASOR = Path(__file__).resolve().parent / "simgeler"
BOYLAR = (16, 24, 32, 48, 64, 128, 256)


def simge():
    """Her boyu ayrı çizilmiş QIcon; QGuiApplication açıldıktan sonra çağrılır."""
    cizim = QIcon(str(KLASOR / "litevideotube.svg"))
    sonuc = QIcon()
    for n in BOYLAR:
        sonuc.addPixmap(cizim.pixmap(n, n))
    return sonuc
