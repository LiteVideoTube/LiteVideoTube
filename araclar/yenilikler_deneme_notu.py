"""Ön sürüm denemesinde (yayin.yml, on_surum) o sürüme bir Yenilikler notu ekler, yalnız o pakete (depoya yazılmaz):
deneme sürümünde de "Güncellendi" penceresi başlık göstersin.
  python araclar/yenilikler_deneme_notu.py <sürüm>"""
import datetime
import json
import pathlib
import sys

s = sys.argv[1]
for yol in sorted((pathlib.Path(__file__).resolve().parent.parent / "litevideotube" / "yenilikler").glob("*.json")):
    d = json.loads(yol.read_text(encoding="utf-8"))
    if not any(x["surum"] == s for x in d):
        d.insert(0, {"surum": s, "tarih": datetime.date.today().isoformat(),
                     "maddeler": [{"baslik": f"Deneme {s}", "ayrinti": "Ön sürüm denemesi."}]})
        yol.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(f"{s} için deneme notu eklendi")
