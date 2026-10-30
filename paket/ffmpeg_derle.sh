#!/bin/bash
# Windows paketi için küçük ffmpeg (27 Ekim: paketi küçült). Linux'ta mingw-w64 ile Windows'a derlenir
# (.github/workflows/ffmpeg.yml). Aynı parçalarla Linux paketi (AppImage) için de: hedef "linux", tek parça (static)
# ffmpeg, kullanıcının sistemindeki kitaplıklara bağlı değil. Program ffmpeg'i yalnız indirmede, yt-dlp'nin üç işi için kullanıyor
# (litevideotube/indirme.py): ayrı inen görüntüyle sesi MP4'te birleştirmek (yeniden kodlamadan), m4a sesi
# düzeltmek (yeniden kodlamadan) ve "yalnız ses (MP3)" için sesi çözüp LAME ile MP3'e çevirmek. Bu yüzden yalnız
# bunlara yeten parçalar açılır; hazır büyük yapı (yt-dlp/FFmpeg-Builds gpl) 162 MB idi.
# Lisans: --enable-gpl yok, ffmpeg LGPL-2.1-or-later; LAME LGPL-2.0-or-later (paket/lisanslar/OKUBENI.txt).
#
# Kullanım: ffmpeg_derle.sh <çıktı klasörü> [ffmpeg sürümü, ör. 9.0.2; boşsa son kararlı sürüm] [hedef: windows (varsayılan) | linux]
# Çıktı: ffmpeg.exe (linux'ta ffmpeg), SURUM.txt, ffmpeg-LICENSE.md, LAME-COPYING.txt, kaynak/ (kullanılan kaynak arşivleri ve bu betik: GPL/LGPL kaynak yükümlülüğü için).
set -euo pipefail
CIKTI=$(realpath -m "$1"); SURUM=${2:-}; HEDEF=${3:-windows}; BETIK=$(realpath "${BASH_SOURCE[0]}")
LAME=3.100
mkdir -p "$CIKTI/kaynak"
IS=$(mktemp -d); cd "$IS"
if [ -z "$SURUM" ]; then   # son kararlı sürüm: nX.Y(.Z) biçimindeki en büyük etiket ("-dev" olmayan)
  SURUM=$(git ls-remote --tags https://github.com/FFmpeg/FFmpeg 'n*' | awk -F/ '{print $3}' | grep -E '^n[0-9]+\.[0-9]+(\.[0-9]+)?$' | sort -V | tail -1 | cut -c2-)
fi
echo "ffmpeg $SURUM, LAME $LAME"
# HAZIR_KAYNAK: arşivlerin önceden indirildiği klasör (ffmpeg.org'a ulaşılamayan makinede deneme için).
for a in "ffmpeg-$SURUM.tar.xz|https://ffmpeg.org/releases/ffmpeg-$SURUM.tar.xz" \
         "lame-$LAME.tar.gz|https://downloads.sourceforge.net/project/lame/lame/$LAME/lame-$LAME.tar.gz"; do
  ad=${a%%|*}; adres=${a#*|}
  if [ -n "${HAZIR_KAYNAK:-}" ] && [ -f "$HAZIR_KAYNAK/$ad" ]; then cp "$HAZIR_KAYNAK/$ad" .; else curl -fsSL --retry 4 --retry-delay 5 --connect-timeout 30 --max-time 600 -o "$ad" "$adres"; fi
done
cp "ffmpeg-$SURUM.tar.xz" "lame-$LAME.tar.gz" "$CIKTI/kaynak/"
cp "$BETIK" "$CIKTI/kaynak/ffmpeg_derle.sh"
tar xf "ffmpeg-$SURUM.tar.xz"; tar xf "lame-$LAME.tar.gz"
ON=$IS/on
case "$HEDEF" in
  windows) HOST=x86_64-w64-mingw32; LAME_HOST=(--host=$HOST); STRIP=$HOST-strip; EXE=ffmpeg.exe
           FF_HEDEF=(--target-os=mingw32 --cross-prefix=$HOST- --enable-w32threads); DERLEYICI="mingw-w64 $($HOST-gcc -dumpversion)" ;;
  linux)   LAME_HOST=(); STRIP=strip; EXE=ffmpeg
           FF_HEDEF=(--target-os=linux --enable-pthreads); DERLEYICI="gcc $(gcc -dumpversion), static" ;;
  *) echo "Bilinmeyen hedef: $HEDEF (windows | linux)" >&2; exit 1 ;;
esac

(cd "lame-$LAME"
 ./configure "${LAME_HOST[@]}" --prefix="$ON" --disable-shared --enable-static --disable-frontend --disable-gtktest \
   --disable-decoder --enable-nasm=no CFLAGS="-O2" > /dev/null
 make -j"$(nproc)" > /dev/null && make install > /dev/null)

cd "ffmpeg-$SURUM"
# Ses: AAC ve Opus (YouTube'un verdikleri), Vorbis ve MP3 (eski biçimler) çözülür; MP3'e LAME ile kodlanır.
# Görüntü yalnız kopyalanır; ayrıştırıcılar zaman bilgisi için. VP9 çözücüsü yalnız MP4'e yazarken gereken bilgiyi
# (renk biçimi) okumak için: o olmadan VP9'lu MP4'ün başlığı eksik yazılıyordu (27 Ekim, Windows denemesi).
./configure --prefix="$ON" --arch=x86_64 "${FF_HEDEF[@]}" --pkg-config=pkg-config \
  --pkg-config-flags=--static --extra-cflags="-I$ON/include" --extra-ldflags="-L$ON/lib -static" \
  --disable-everything --disable-autodetect --disable-debug --disable-doc --disable-ffplay --disable-ffprobe \
  --disable-avdevice --disable-swscale --disable-x86asm --enable-small \
  --enable-libmp3lame --enable-encoder=libmp3lame \
  --enable-decoder=aac,aac_latm,opus,vorbis,mp3float,mp3,flac,vp9 \
  --enable-demuxer=mov,matroska,webm_dash_manifest,mp3,aac,ogg,wav,flac,mpegts,concat \
  --enable-muxer=mp4,mov,ipod,mp3,matroska,webm,adts,ogg,opus \
  --enable-parser=aac,aac_latm,h264,hevc,vp8,vp9,av1,opus,vorbis,mpegaudio,flac \
  --enable-bsf=aac_adtstoasc,setts,vp9_superframe,vp9_superframe_split,h264_mp4toannexb,hevc_mp4toannexb,extract_extradata,av1_frame_split,av1_metadata \
  --enable-filter=abuffer,abuffersink,buffer,buffersink,aresample,aformat,anull,null,format,atrim,trim,asetpts,setpts \
  --enable-protocol=file,pipe,concat --enable-swresample
make -j"$(nproc)" > /dev/null
$STRIP -o "$CIKTI/$EXE" $EXE
cp LICENSE.md "$CIKTI/ffmpeg-LICENSE.md"; cp "../lame-$LAME/COPYING" "$CIKTI/LAME-COPYING.txt"
{
  echo "ffmpeg $SURUM (LGPL-2.1-or-later, --enable-gpl yok) + LAME $LAME (LGPL), $DERLEYICI"
  echo "kaynak: https://ffmpeg.org/releases/ffmpeg-$SURUM.tar.xz , https://downloads.sourceforge.net/project/lame/lame/$LAME/lame-$LAME.tar.gz"
  echo "derleme: paket/ffmpeg_derle.sh (LiteVideoTube deposu)"
  grep -o 'FFMPEG_CONFIGURATION "[^"]*"' config.h | sed 's/FFMPEG_CONFIGURATION /yapılandırma: /'
} > "$CIKTI/SURUM.txt"
ls -la "$CIKTI/$EXE"
rm -rf "$IS"
