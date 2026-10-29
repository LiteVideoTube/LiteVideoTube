"""Yenilikler notları (litevideotube/yenilikler/<dil>.json; yenilikler.py) tutarlı mı: her dil Türkçeyle aynı sürümleri,
aynı tarihleri ve her sürümde aynı sayıda maddeyi taşıyor mu, boş başlık ya da açıklama var mı; programın her dilinin
(ceviri/*.ts) notu var mı. Sürüm verilirse (yayın akışı) o sürümün notu ve tarihi de aranır.
  python araclar/yenilikler_sinama.py [sürüm]"""
import json
import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parent.parent / "litevideotube"
K = KOK / "yenilikler"
hata = []
tr = json.loads((K / "tr.json").read_text(encoding="utf-8"))
diller = sorted(p.stem.split("_")[-1] for p in (KOK / "ceviri").glob("litevideotube_*.ts"))
for dil in diller:
    yol = K / f"{dil}.json"
    if not yol.exists():
        hata.append(f"{dil}: not dosyası yok")
        continue
    d = json.loads(yol.read_text(encoding="utf-8"))
    if [(s["surum"], s["tarih"], len(s["maddeler"])) for s in d] != [(s["surum"], s["tarih"], len(s["maddeler"])) for s in tr]:
        hata.append(f"{dil}: sürümler, tarihler ya da madde sayıları Türkçeyle aynı değil")
    for s in d:
        for m in s["maddeler"]:
            if not m.get("baslik", "").strip() or not m.get("ayrinti", "").strip():
                hata.append(f"{dil} {s['surum']}: boş başlık ya da açıklama")
if len(sys.argv) > 1:
    s = next((s for s in tr if s["surum"] == sys.argv[1]), None)
    if s is None:
        hata.append(f"{sys.argv[1]} sürümünün notu yok (yenilikler/tr.json)")
    elif not s["tarih"]:
        hata.append(f"{sys.argv[1]} sürümünün tarihi yok")
for h in hata:
    print("HATA", h)
print("tamam" if not hata else f"{len(hata)} hata", f"({len(diller) + 1} dil)")
sys.exit(1 if hata else 0)
