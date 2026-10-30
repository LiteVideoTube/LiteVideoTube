<p align="center"><img src="paket/litevideotube.png" width="112" alt="LiteVideoTube"></p>
<h1 align="center">LiteVideoTube</h1>
<p align="center"><b>YouTube, bilgisayarı zorlamadan.</b><br>
YouTube on far less hardware.</p>
<p align="center"><a href="https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube-win-Setup.exe"><b>Windows</b></a> · <a href="https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube.AppImage"><b>Linux</b></a></p>

[Türkçe](#türkçe) · [English](#english)

## Türkçe

**Windows için indir: [LiteVideoTube-win-Setup.exe](https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube-win-Setup.exe)**. İndirip çift tıklayın. Windows "bilinmeyen yayımcı" derse "Ek bilgi" → "Yine de çalıştır".

**Linux için indir: [LiteVideoTube.AppImage](https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube.AppImage)**. İndirdikten sonra dosyaya sağ tıklayıp Özellikler → İzinler'den "Çalıştırılabilir" işaretleyin (ya da `chmod +x LiteVideoTube.AppImage`), sonra çift tıklayın. Ubuntu 24.04, Linux Mint 22, Debian 13, Fedora 40 ve sonrasında çalışır.

Program 14 dilde; ilk açılışta dilinizi sorar. Yeni sürümleri kendisi indirir.

### Linux'ta açılmazsa

- **Çift tıklayınca hiçbir şey olmuyor:** dosya çalıştırılabilir işaretli değil. Sağ tık → Özellikler → İzinler → "Çalıştırılabilir", ya da terminalde `chmod +x LiteVideoTube.AppImage`.
- **Terminalde `GLIBC_2.3x not found` hatası:** sisteminiz paketin istediğinden eski (ör. Ubuntu 22.04, Linux Mint 21, Debian 12). Sistemi yeni sürüme yükseltmek gerekir; eski sistemler için paket henüz yok.
- **FUSE ya da `fusermount` hatası:** `sudo apt install fuse3` (Ubuntu, Mint, Debian) ya da `sudo dnf install fuse3` (Fedora). Olmazsa programı `./LiteVideoTube.AppImage --appimage-extract-and-run` ile açın. Ubuntu 22.04 ve sonrasında `fuse` paketini kurmayın, sistemi bozabilir.
- **Başka bir sorun:** programın üst şeridindeki (!) düğmesi ("Hata bildir ya da öneri yaz"), ya da GitHub'da Issues.

## English

**Download for Windows: [LiteVideoTube-win-Setup.exe](https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube-win-Setup.exe)**. Download and double-click. If Windows says "unknown publisher", click "More info" → "Run anyway".

**Download for Linux: [LiteVideoTube.AppImage](https://github.com/LiteVideoTube/LiteVideoTube/releases/latest/download/LiteVideoTube.AppImage)**. After downloading, right-click the file → Properties → Permissions → "Allow executing as program" (or `chmod +x LiteVideoTube.AppImage`), then double-click. Runs on Ubuntu 24.04, Linux Mint 22, Debian 13, Fedora 40 or newer.

The program speaks 14 languages and asks for yours on first start. It updates itself.

### If it does not start on Linux

- **Nothing happens on double-click:** the file is not marked executable; see above.
- **`GLIBC_2.3x not found` in a terminal:** your system is older than the package needs (e.g. Ubuntu 22.04, Linux Mint 21, Debian 12). There is no package for older systems yet.
- **FUSE or `fusermount` error:** `sudo apt install fuse3` (Ubuntu, Mint, Debian) or `sudo dnf install fuse3` (Fedora). Otherwise start it with `./LiteVideoTube.AppImage --appimage-extract-and-run`. On Ubuntu 22.04 and newer, do not install the `fuse` package; it can break the system.
- **Anything else:** the (!) button in the program's top bar ("Report a problem or send a suggestion"), or GitHub Issues.

## Kurmak

- Windows: sürümler (Releases) sayfasındaki `LiteVideoTube-win-Setup.exe`. Program yeni sürümleri kendisi indirir ve "Yeni sürüm var" penceresiyle sorar.
- Linux: sürümler sayfasındaki `LiteVideoTube.AppImage`. Kurulum yok, dosyanın kendisi program; yeni sürümleri Windows'taki gibi kendisi indirir.
- Geliştirme (Linux): `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m litevideotube`. Sistemde libmpv (`libmpv2`) ve güncel yt-dlp gerekir.

## Yapı

Python + PySide6 (Qt Quick) arayüz; video libmpv ile programın kendi penceresinin içine çizilir; video adresleri yt-dlp'den, sayfa verisi (arama, öneriler) YouTube'un kendi veri kapılarından.

- `litevideotube/`: program (`uygulama.py` açılış, `oynatici.py` video öğesi ve altyazı, `cozumle.py` video adresleri (yt-dlp), `youtube.py` sayfa verisi ve yorumlar, `veri.py` arka plan köprüsü, `kayit.py` geçmiş, kaldığı yer ve ayarlar, `abonelik.py` (abonelik sayfasının bölümleri: `akis`), `ilgi.py` programın kendi sıralaması (izleme geçmişinden), `kisi.py` kişiler (her kişinin kayıtları ayrı klasörde: `yoklama.py`, `veri_klasoru`), `liste.py` oynatma listeleri ve Sonra izle, `indirme.py`, `diller.py` dil adları, `guncelleme.py` otomatik güncelleme, `geribildirim.py` hata bildirme, `qml/` arayüz, `simgeler/` Material Symbols).
- `paket/` ve `.github/workflows/windows-paket.yml`: Windows paketi (PyInstaller tek klasör; exe'nin yanında libmpv-2.dll, yt-dlp.exe, ffmpeg.exe, qjs.exe). ffmpeg yalnız indirmeye yeten küçük bir derleme (`paket/ffmpeg_derle.sh`, `ffmpeg.yml`).
- `paket/linux_paket.sh` ve `.github/workflows/yayin-linux.yml`: Linux paketi (PyInstaller tek klasör; Ubuntu 24.04'ün libmpv'si ve kitaplıkları, yt-dlp, qjs, ffmpeg'in Linux derlemesi; Velopack ile AppImage). Kitaplıkların paketleri, sürümleri ve kaynak adresleri paketin `lisanslar/linux-kitapliklar.txt` dosyasında.
- Yayın: `yayin.yml` (Velopack paketi → GitHub Releases; kurulu programlar oradan güncellenir; ardından `yayin-linux.yml` Linux paketini aynı sürüme ekler ve sürüm notunun başına indirme bağlantılarını yazar), `ytdlp-izle.yml` (yt-dlp'nin yeni sürümünde programın yeni sürümünü çıkarır), `kaynak-kodu.yml` (libmpv ve ffmpeg'in kaynak arşivleri, sürümler sayfasında "kaynak-kodu").
- Sınama için ortam değişkenleri: `LVT_VERI` (kayıt klasörü), `LVT_INDIR` (indirme klasörü), `LVT_ARA`, `LVT_AC`, `LVT_SINAMA=<sn>,<png>`, `LVT_BUYUK`, `LVT_LOG` (mpv günlüğü), `LVT_MPV` (ek mpv ayarları), `LVT_YTDL` (yt-dlp yolu), `LVT_JS` (yt-dlp'nin JavaScript çalıştırıcısı), `LVT_GECERLILIK_SN` (video adresinin ömrünü kısaltır), `LVT_GUNCELLEME` (güncellemenin geleceği yer), `LVT_GUNCELLEME_GUNLUK`, `LVT_GUNCELLEME_SEC` (`simdi`/`sonra`: güncelleme penceresinin düğmesine kendisi basar), `LVT_GUNCELLEME_JETON` ve `LVT_GUNCELLEME_ON_SURUM` (gizli depodan ve ön sürümlerle güncelleme denemesi, `windows-guncelleme-github.yml`), `LVT_SENTRY_DSN` (geri bildirimin gideceği yer; boşsa gönderilmez), `LVT_DIL` (programın dili, örnek `en`; `litevideotube/ceviri.py`), `LVT_PROXY` (proxy adresi, `yok`: kapalı; verilmezse sistemin ayarı, `litevideotube/ag.py`).
- `araclar/arkada_sinama.py`: Windows paketinde arka plan yoklamasının denemesi (`windows-paket.yml` kullanır).

## Bağımsızlık

LiteVideoTube bağımsız, ticari olmayan bir projedir. YouTube veya Google ile bağlantılı değildir, onlar tarafından onaylanmamış ya da desteklenmemiştir. YouTube ve Google, Google LLC'nin ticari markalarıdır.

LiteVideoTube is an independent, non-commercial project. It is not affiliated with, endorsed by or sponsored by YouTube or Google. YouTube and Google are trademarks of Google LLC.

## Lisans

LiteVideoTube, GNU Genel Kamu Lisansı sürüm 3 ya da (dilediğiniz gibi) sonraki bir sürümü (GPL-3.0-or-later) koşullarında dağıtılır; tam metin `LICENSE`. Windows paketindeki başka programların (libmpv, ffmpeg, yt-dlp, Qt, QuickJS ve ötekiler) lisansları ve kaynak adresleri `paket/lisanslar/OKUBENI.txt`'te; paket yapılırken bu klasör, parçaların tam sürümleriyle (`SURUMLER.txt`) birlikte paketin `lisanslar/` klasörüne girer.

Copyright (C) 2026 Adeptus Vesperius Noctivagus
