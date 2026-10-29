"""libmpv-2.dll'in kaynak arşivleri (GPL; .github/workflows/kaynak-kodu.yml kullanır).

Pakete giren libmpv-2.dll, shinchiro/mpv-winbuild-cmake'in bir sürümü. O derleme tarif deposundaki (packages/*.cmake)
her parçayı, derlendiği anda kaynak deposunun en son hâliyle (çoğunda belirli bir sürüm değil, ana dalın o anki
hâli) alıp içine koyuyor; sürüm notunda commit listesi yok. Bu betik aynısını geri kurar: tarifte mpv'nin bağlı olduğu
bütün parçaları (DEPENDS, iç içe) bulur ve her birinin deposunu derlemenin başladığı andaki commit'iyle arşivler.
mpv'nin commit'i dll'in içinde yazdığı için tamdır; öbürlerinde "derleme başladığında ana daldaki son commit" alınır.
Derleme sırasında (birkaç dakika) yeni commit gelmişse fark olabilir; bu durum arşivlerin listesinde yazmaz.

  python libmpv_kaynak.py <tarif klasörü> <derleme başlangıcı, ISO> <mpv commit'i> <çıktı klasörü> [--yalniz-liste]
"""
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


def tarifler(klasor):
    """{paket: {"bagli": [...], "git": url, "etiket": GIT_TAG, "url": URL}}"""
    t = {}
    for f in sorted((Path(klasor) / "packages").glob("*.cmake")):
        metin = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"ExternalProject_Add\((\S+)(.*?)\n\)", metin, re.S):
            ad, govde = m.group(1), m.group(2)
            bagli = []
            d = re.search(r"\bDEPENDS\b(.*?)(?=\n\s+[A-Z_]{3,}\b)", govde, re.S)
            if d:
                bagli = [x for x in d.group(1).split() if not x.startswith("$")]
            git = re.search(r"GIT_REPOSITORY\s+(\S+)", govde)
            etiket = re.search(r"GIT_TAG\s+(\S+)", govde)
            url = re.search(r"\n\s+URL\s+(\S+)", govde)
            t[ad] = {"bagli": bagli, "git": git and git.group(1), "etiket": etiket and etiket.group(1),
                     "url": url and url.group(1)}
    return t


def gerekenler(t, kok="mpv"):
    gorulen, sira = set(), [kok]
    while sira:
        p = sira.pop()
        if p in gorulen or p not in t:
            continue
        gorulen.add(p)
        sira.extend(t[p]["bagli"])
    return sorted(gorulen)


def calis(*k, **kw):
    return subprocess.run(k, check=True, text=True, capture_output=True, **kw).stdout.strip()


def arsivle(ad, bilgi, zaman, mpv_commit, cikti, is_klasoru):
    if bilgi["url"] and not bilgi["git"]:
        dosya = cikti / f"{ad}-{bilgi['url'].rsplit('/', 1)[-1]}"
        urllib.request.urlretrieve(bilgi["url"], dosya)
        return f"{ad} {bilgi['url']}"
    depo = is_klasoru / ad
    if not depo.exists():
        calis("git", "clone", "-q", "--filter=blob:none", "--no-checkout", bilgi["git"], str(depo))
    if ad == "mpv":
        commit = calis("git", "-C", str(depo), "rev-parse", mpv_commit)
    else:
        ref = f"origin/{bilgi['etiket']}" if bilgi["etiket"] else "origin/HEAD"
        try:
            calis("git", "-C", str(depo), "rev-parse", "--verify", ref)
        except subprocess.CalledProcessError:
            ref = bilgi["etiket"]   # dal değil, etiket
        commit = calis("git", "-C", str(depo), "rev-list", "-1", f"--before={zaman}", ref)
    hedef = cikti / f"{ad}-{commit[:10]}.tar.xz"
    with open(hedef, "wb") as f:
        arsiv = subprocess.Popen(["git", "-C", str(depo), "archive", f"--prefix={ad}/", commit], stdout=subprocess.PIPE)
        subprocess.run(["xz", "-T0", "-6"], stdin=arsiv.stdout, stdout=f, check=True)
        arsiv.wait()
    return f"{ad} {bilgi['git']} {commit}"


def main(klasor, zaman, mpv_commit, cikti, yalniz_liste=False):
    t = tarifler(klasor)
    paketler = gerekenler(t)
    print(f"mpv'nin bağlı olduğu {len(paketler)} parça:", " ".join(paketler))
    if yalniz_liste:
        for p in paketler:
            print(f"  {p}: {t[p]['git'] or t[p]['url']} {t[p]['etiket'] or ''}")
        return 0
    cikti = Path(cikti)
    cikti.mkdir(parents=True, exist_ok=True)
    is_klasoru = Path("libmpv-depolar")
    is_klasoru.mkdir(exist_ok=True)
    satirlar, hatalar = [], []
    for p in paketler:
        if not (t[p]["git"] or t[p]["url"]):
            satirlar.append(f"{p} (kaynağı yok: yalnız başka parçaları toplayan bir adım)")
            continue
        try:
            satirlar.append(arsivle(p, t[p], zaman, mpv_commit, cikti, is_klasoru))
            print("tamam:", satirlar[-1], flush=True)
        except Exception as e:
            hatalar.append(f"{p}: {e}")
            print("ALINAMADI:", p, e, flush=True)
    (cikti / "LISTE.txt").write_text(
        f"Derleme başlangıcı: {zaman}\nmpv commit: {mpv_commit}\n\n" + "\n".join(satirlar)
        + ("\n\nAlınamayanlar:\n" + "\n".join(hatalar) if hatalar else "") + "\n", encoding="utf-8")
    return 1 if hatalar else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5], yalniz_liste="--yalniz-liste" in sys.argv))
