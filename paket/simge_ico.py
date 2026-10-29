"""Programın simgesinden (litevideotube/program_simgesi.py) Windows paketi
için paket/litevideotube.ico yapar: 16-256 piksellik yedi boy, her biri PNG olarak (Windows Vista'dan beri ICO içinde
PNG geçerli). Simge değişince yeniden çalıştırılır: QT_QPA_PLATFORM=offscreen .venv/bin/python paket/simge_ico.py"""
import struct, sys
from pathlib import Path
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "litevideotube"))
import program_simgesi  # noqa: E402  (paketin __init__'i ağır modülleri yüklemesin diye doğrudan)

BOYLAR = program_simgesi.BOYLAR
app = QGuiApplication(sys.argv)
simge = program_simgesi.simge()
parcalar = []
for n in BOYLAR:
    b = QByteArray(); tampon = QBuffer(b); tampon.open(QIODevice.WriteOnly)
    simge.pixmap(n, n).toImage().save(tampon, "PNG")
    parcalar.append(bytes(b))
bas = struct.pack("<HHH", 0, 1, len(BOYLAR))
yer = 6 + 16 * len(BOYLAR)
dizin = b""
for n, veri in zip(BOYLAR, parcalar):
    dizin += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(veri), yer)
    yer += len(veri)
(KOK / "paket" / "litevideotube.ico").write_bytes(bas + dizin + b"".join(parcalar))
print("tamam")
