#!/bin/bash
# Linux paketi: AppImage'ın içine girecek tek klasör (PyInstaller), yanında libmpv ve kitaplıkları, yt-dlp, QuickJS,
# küçük ffmpeg ve lisanslar. Velopack bu klasörden AppImage yapar (.github/workflows/yayin-linux.yml).
# Ubuntu 24.04'te çalıştırılır (GitHub'ın ubuntu-24.04 makinesi): libmpv2 ve kitaplıkları oradan alınır, bu yüzden
# paket glibc 2.39 ve sonrasını ister (Ubuntu 24.04, Linux Mint 22, Debian 13, Fedora 40 ve sonrası).
# Her masaüstünde zaten olan ve kullanıcının sistemine uygun olması gereken kitaplıklar (glibc, OpenGL/EGL, X11, ALSA,
# fontconfig...) pakete girmez: AppImage topluluğunun listesi (pkg2appimage/excludelist) ve ekran kartı kitaplıkları.
#
# Kullanım: paket/linux_paket.sh <sürüm, ör. 0.1.1> <küçük ffmpeg'in klasörü (paket/ffmpeg_derle.sh <klasör> "" linux)>
# Gerekenler: python3'te requirements.txt, pyinstaller ve velopack; sistemde libmpv2, curl, gh (GitHub'a girişli), dpkg.
# PYTHON değişkeni başka bir python verir (ör. .venv/bin/python).
# Çıktı: dist/LiteVideoTube/ (lisanslar/SURUMLER.txt ve lisanslar/linux-kitapliklar.txt dahil), dist/litevideotube.png.
set -euo pipefail
SURUM=$1; FFMPEG=$(realpath "$2"); PY=${PYTHON:-python3}
cd "$(dirname "$0")/.."
KOK=$PWD; IS=$(mktemp -d); trap 'rm -rf "$IS"' EXIT
LIB=/usr/lib/x86_64-linux-gnu
[[ $SURUM =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Sürüm X.Y.Z biçiminde olmalı: $SURUM" >&2; exit 1; }
[ -f "$LIB/libmpv.so.2" ] || { echo "libmpv2 kurulu değil (sudo apt install libmpv2)" >&2; exit 1; }
[ -f "$FFMPEG/ffmpeg" ] || { echo "$FFMPEG/ffmpeg yok" >&2; exit 1; }
chmod +x "$FFMPEG/ffmpeg"   # GitHub iş akışı yüklemelerinden gelince çalıştırma izni düşüyor

# ---- yardımcı programlar
mkdir -p "$IS/yardim" "$IS/lisanslar"
curl -fsSL --retry 4 -o "$IS/yardim/yt-dlp" https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux
gh release download -R quickjs-ng/quickjs -p qjs-linux-x86_64 -O "$IS/yardim/qjs"
cp "$FFMPEG/ffmpeg" "$IS/yardim/"
chmod +x "$IS/yardim/"*
YTDLP=$("$IS/yardim/yt-dlp" --version)
QJS=$(gh release view -R quickjs-ng/quickjs --json tagName -q .tagName)

# ---- program (PyInstaller); programın sürümü yazılır, dosya sonra eski haline döner
cp litevideotube/youtube.py "$IS/youtube.py.yedek"
trap 'cp "$IS/youtube.py.yedek" "$KOK/litevideotube/youtube.py"; rm -rf "$IS"' EXIT
sed -i "s|PROGRAM_ADI = \"LiteVideoTube/[^\"]*\"|PROGRAM_ADI = \"LiteVideoTube/$SURUM\"|" litevideotube/youtube.py
grep 'PROGRAM_ADI = ' litevideotube/youtube.py
rm -rf build/LiteVideoTube dist/LiteVideoTube
"$PY" -m PyInstaller --noconfirm --onedir --windowed --name LiteVideoTube \
  --add-data "litevideotube/qml:litevideotube/qml" \
  --add-data "litevideotube/simgeler:litevideotube/simgeler" \
  --add-data "litevideotube/ceviri:litevideotube/ceviri" \
  --add-data "litevideotube/yenilikler:litevideotube/yenilikler" \
  --add-binary "$LIB/libmpv.so.2:." \
  --exclude-module tkinter --paths . paket/giris.py 2>&1 | tail -2
cp "$IS/youtube.py.yedek" litevideotube/youtube.py
P=dist/LiteVideoTube; I=$P/_internal
# Qt 6.5'ten beri xcb (X11) için gerekli, çoğu sistemde kurulu değil; PyInstaller ancak sistemde bulursa koyar.
# YEREL_LIB: apt'siz makinede (sudo yoksa) kitaplığın elle konduğu klasör.
[ -n "${YEREL_LIB:-}" ] && [ ! -e "$I/libxcb-cursor.so.0" ] && cp -L "$YEREL_LIB/libxcb-cursor.so.0" "$I/"
[ -e "$I/libxcb-cursor.so.0" ] || { echo "libxcb-cursor.so.0 pakete girmedi (sudo apt install libxcb-cursor0)" >&2; exit 1; }

# Kullanılmayan Qt Quick biçemleri (program Basic kullanıyor; Windows paketinde de silinir).
for t in FluentWinUI3 Imagine Material Universal Fusion iOS macOS; do
  rm -rf "$I/PySide6/Qt/qml/QtQuick/Controls/$t"
  rm -f "$I/PySide6/Qt/lib/libQt6QuickControls2$t"*.so* "$I/libQt6QuickControls2$t"*.so*
done

# Kullanıcının sisteminden gelmesi gereken kitaplıklar pakette durmasın.
curl -fsSL --retry 4 -o "$IS/excludelist" https://raw.githubusercontent.com/AppImageCommunity/pkg2appimage/master/excludelist
{ grep -vE '^\s*(#|$)' "$IS/excludelist" | awk '{print $1}'
  # Ekran kartı ve sürücüsüne bağlı olanlar: sistemdeki Mesa ya da NVIDIA sürücüsüyle aynı olmalı.
  printf '%s\n' libGL.so.1 libEGL.so.1 libGLX.so.0 libGLdispatch.so.0 libOpenGL.so.0 libgbm.so.1 libdrm.so.2 \
    libdrm_amdgpu.so.1 libdrm_intel.so.1 libdrm_nouveau.so.2 libdrm_radeon.so.1 libvdpau.so.1 libOpenCL.so.1 \
    libwayland-cursor.so.0 libwayland-egl.so.1 libwayland-server.so.0   # PyInstaller da koymuyor (Mesa ile eş olmalı)
} | sort -u > "$IS/disarida"
silinen=0
while read -r ad; do
  for f in "$I/$ad" "$I/PySide6/Qt/lib/$ad"; do [ -e "$f" ] && { rm -f "$f"; silinen=$((silinen + 1)); }; done
done < "$IS/disarida"
echo "Sistemden gelecek kitaplık (pakette silinen): $silinen"
# Ekran eklentileri ve libmpv'nin istediği her kitaplık ya pakette ya da yukarıdaki listede (her sistemde var) olmalı.
# PyInstaller bu makinede bulamadığını koymuyor (ör. Qt'nin X11 eklentisinin libxcb-* parçaları sunucu makinesinde
# kurulu değildi); eksik kalan kullanıcının makinesinde değil burada yakalansın.
eksik=$(for f in "$I"/libmpv.so.2 "$I"/PySide6/Qt/plugins/platforms/libq{xcb,wayland}.so; do
  [ -e "$f" ] || continue
  LD_LIBRARY_PATH="$I:$I/PySide6/Qt/lib" ldd "$f" | awk '$2 == "=>" {print $1, $3}' | while read -r ad yol; do
    case "$yol" in "$P"/*|"$KOK/$P"/*) continue ;; esac
    grep -qxF "$ad" "$IS/disarida" || echo "$(basename "$f"): $ad ($yol)"
  done
done | sort -u)
[ -z "$eksik" ] || { echo "Pakette olmayan ve her sistemde bulunmayan kitaplıklar (apt ile kurulup yeniden yapılmalı):" >&2
                     echo "$eksik" >&2; exit 1; }

# ---- lisanslar ve sürümler
cp paket/lisanslar/* "$IS/lisanslar/"
cp LICENSE "$IS/lisanslar/GPL-3.0.txt"
cp "$FFMPEG/ffmpeg-LICENSE.md" "$IS/lisanslar/ffmpeg-LICENSE.txt"
cp "$FFMPEG/LAME-COPYING.txt" "$IS/lisanslar/"
curl -fsSL --retry 4 -o "$IS/lisanslar/yt-dlp-THIRD_PARTY_LICENSES.txt" \
  "https://raw.githubusercontent.com/yt-dlp/yt-dlp/$YTDLP/THIRD_PARTY_LICENSES.txt"
# Ubuntu'dan alınan kitaplıklar (libmpv ve bağlı oldukları): hangi paketten, hangi sürüm, kaynağı nerede; paketlerin
# telif dosyaları lisanslar/linux/ altında.
mkdir -p "$IS/lisanslar/linux"
: > "$IS/kitaplik-paket"
for f in "$I"/*.so*; do
  ad=$(basename "$f")
  for d in "$LIB" /lib/x86_64-linux-gnu; do
    if [ -e "$d/$ad" ]; then
      # dpkg kaydında yol /usr/lib ya da /lib ile durabiliyor (usrmerge); ikisine de bakılır.
      gercek=$(realpath "$d/$ad")
      paket=$(dpkg -S "$gercek" "${gercek#/usr}" 2>/dev/null | head -1 | cut -d: -f1) || true
      [ -n "$paket" ] && echo "$ad $paket" >> "$IS/kitaplik-paket"
      break
    fi
  done
done
{
  echo "LiteVideoTube $SURUM (Linux) içindeki Ubuntu 24.04 kitaplıkları / Ubuntu 24.04 libraries in this package"
  echo "dosya / file: paket / package (sürüm / version) -> kaynak / source"
  sort -k2 "$IS/kitaplik-paket" | while read -r ad paket; do
    read -r kaynak kaynak_surum < <(dpkg-query -W -f='${source:Package} ${source:Version}\n' "$paket")
    echo "$ad: $paket ($kaynak_surum) -> https://launchpad.net/ubuntu/+source/$kaynak/$kaynak_surum"
  done
} > "$IS/lisanslar/linux-kitapliklar.txt"
cut -d' ' -f2 "$IS/kitaplik-paket" | sort -u | while read -r paket; do
  [ -f "/usr/share/doc/$paket/copyright" ] && cp "/usr/share/doc/$paket/copyright" "$IS/lisanslar/linux/$paket.txt"
done
MPV_PAKET=$(dpkg-query -W -f='${Version}' libmpv2)
{
  echo "LiteVideoTube $SURUM (Linux) / $(date +%F) / commit $(git rev-parse HEAD)"
  echo "libmpv.so.2: Ubuntu 24.04 libmpv2 $MPV_PAKET  https://launchpad.net/ubuntu/+source/mpv/$MPV_PAKET"
  echo "  öteki kitaplıklar / other libraries: linux-kitapliklar.txt"
  echo "ffmpeg: $("$IS/yardim/ffmpeg" -hide_banner -version | head -1)"
  echo "  $(head -2 "$FFMPEG/SURUM.txt" | paste -sd'/' | sed 's|/| / |')"
  echo "yt-dlp: $YTDLP  https://github.com/yt-dlp/yt-dlp/releases/tag/$YTDLP"
  echo "qjs: quickjs-ng $QJS  https://github.com/quickjs-ng/quickjs/releases/tag/$QJS"
  echo "Kaynak kodu / source code (ffmpeg): https://github.com/LiteVideoTube/LiteVideoTube/releases/tag/kaynak-kodu"
} > "$IS/lisanslar/SURUMLER.txt"
cat "$IS/lisanslar/SURUMLER.txt"

cp "$IS/yardim/"* "$P/"
cp -r "$IS/lisanslar" "$P/"

# Menü ve dosya simgesi (Velopack AppImage'a koyar): programın kendi simgesinden 256 piksel.
QT_QPA_PLATFORM=offscreen "$PY" - <<'EOF'
import sys
sys.path.insert(0, "litevideotube")
from PySide6.QtGui import QGuiApplication
app = QGuiApplication(sys.argv)
import program_simgesi
program_simgesi.simge().pixmap(256, 256).toImage().save("dist/litevideotube.png")
EOF
echo "Paket: $(du -sm "$P" | cut -f1) MB, $(find "$P" -type f | wc -l) dosya"
